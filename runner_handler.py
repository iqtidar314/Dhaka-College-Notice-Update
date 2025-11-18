import os
import json
import urllib.request
import urllib.parse
import html  # Added for safe HTML escaping

# Configuration
ERROR_FILE = 'error_state.json'
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def load_error_state():
    if os.path.exists(ERROR_FILE):
        try:
            with open(ERROR_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"last_error": {}, "previous_error": {}}

def save_error_state(data):
    try:
        with open(ERROR_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to save error state: {e}")

def send_telegram_message(message):
    if not TOKEN or not CHAT_ID:
        print("Missing Telegram credentials")
        return False
        
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    # We use data= to force a POST request which is more robust for longer messages
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
        print("Telegram notification sent.")
        return True
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")
        return False

def handle_failure():
    error_data = load_error_state()
    last_error = error_data.get("last_error", {})
    previous_error = error_data.get("previous_error", {})
    
    error_type = "runner_failure"
    
    # Get GitHub context
    workflow = html.escape(os.environ.get('GITHUB_WORKFLOW', 'Unknown'))
    run_id = os.environ.get('GITHUB_RUN_ID', 'Unknown')
    repo = html.escape(os.environ.get('GITHUB_REPOSITORY', 'Unknown'))
    
    # Create a clean detail string
    detail_error = f"Workflow '{workflow}' failed. Run ID: {run_id}"

    current_error_type = last_error.get("type")
    current_count = last_error.get("count", 0)
    current_sent = last_error.get("sent", False)
    current_active = last_error.get("active", False)

    # --- LOGIC: Matches your monitor.py 3-strike rule ---
    
    # Case 1: Same error type (Runner failed again)
    if current_error_type == error_type and current_active:
        error_count = current_count + 1
        error_data["last_error"] = {
            "type": error_type,
            "active": True,
            "count": error_count,
            "detail_error": detail_error,
            "sent": current_sent
        }

    # Case 2: Different error type (e.g., was Network error, now Runner crashed)
    elif current_error_type != error_type:
        # Restore previous error if eligible
        if (previous_error.get("active", False) and 
            previous_error.get("type") == error_type and 
            current_count < 3 and not current_sent):
            
            error_count = previous_error.get("count", 0) + 1
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": detail_error,
                "sent": previous_error.get("sent", False)
            }
            error_data["previous_error"] = {"type": None, "count": 0, "sent": False, "active": False}
        else:
            # Archive current as previous if it was significant
            if current_active and current_sent and current_count >= 3:
                error_data["previous_error"] = {
                    "type": current_error_type,
                    "count": current_count,
                    "sent": True,
                    "active": True
                }
            
            # Start new count
            error_count = 1
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": detail_error,
                "sent": False
            }
            
    # Case 3: First run or fresh start
    else:
        error_count = 1
        error_data["last_error"] = {
            "type": error_type,
            "active": True,
            "count": error_count,
            "detail_error": detail_error,
            "sent": False
        }

    # --- SEND LOGIC ---
    if error_count >= 3 and not error_data["last_error"]["sent"]:
        msg = (
            f"🚨 <b>GitHub Action Failed!</b>\n"
            f"Repo: {repo}\n"
            f"Workflow: {workflow}\n"
            f"Occurred {error_count} times consecutively.\n"
            f"View logs: https://github.com/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/{run_id}\n\n"
        )

        # Mention previous error context
        if previous_error.get("active") and previous_error.get("sent"):
             prev_type = previous_error.get('type')
             prev_count = previous_error.get('count')
             msg += f"📋 <b>Note:</b> Previous <b>{prev_type}</b> error had occurred {prev_count} times before this crash."

        if send_telegram_message(msg):
            error_data["last_error"]["sent"] = True

    save_error_state(error_data)

if __name__ == "__main__":
    handle_failure()
