
import os
import json
import requests
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime, timezone, timedelta
import sys
import html


class NoticeMonitor:
    def __init__(self):
        self.url = "https://www.dhakacollege.edu.bd/en/notice"
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.cache_file = 'notice_cache.json'
        self.error_file = 'error_state.json'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def load_cache(self):
        """Load cached data from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"notices": [], "last_check": None}
        except Exception as e:
            print(f"Error loading cache: {e}")
            return {"notices": [], "last_check": None}
    
    def save_cache(self, data):
        """Save data to cache file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def load_error_state(self):
        try:
            if os.path.exists(self.error_file):
                with open(self.error_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading error state: {e}")
        return {"last_error": {"type": None, "active": False}}

    def save_error_state(self, data):
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving error state: {e}")

    def send_error_notification(self, error_type, details=None):
        error_data = self.load_error_state()
        last_error = error_data.get("last_error", {})
        previous_error = error_data.get("previous_error", {})
    
        current_error_type = last_error.get("type")
        current_count = last_error.get("count", 0)
        current_sent = last_error.get("sent", False)
        current_active = last_error.get("active", False)
    
        # Case 1: Same error type as currently tracked
        if current_error_type == error_type and current_active:
            error_count = current_count + 1
            
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent": current_sent
            }
    
        # Case 2: Different error type
        elif current_error_type != error_type:
            # Check if we need to restore previous error that matches current error_type
            if (previous_error.get("active", False) and 
                previous_error.get("type") == error_type and 
                current_count < 3 and not current_sent):
                # Restore previous error and continue its count
                error_count = previous_error.get("count", 0) + 1
                
                error_data["last_error"] = {
                    "type": error_type,
                    "active": True,
                    "count": error_count,
                    "detail_error": str(details.get('error', '')) if details else "",
                    "sent": previous_error.get("sent", False)
                }
                
                # Clear previous error since we restored it
                error_data["previous_error"] = {"type": None, "count": 0, "sent": False, "active": False}
            
            else:
                # If current error was sent (>=3 times), store it as previous_error
                if current_active and current_sent and current_count >= 3:
                    error_data["previous_error"] = {
                        "type": current_error_type,
                        "count": current_count,
                        "sent": True,
                        "active": True  # Mark as active so we know to track it
                    }
                
                # Start new error tracking from 1
                error_count = 1
                error_data["last_error"] = {
                    "type": error_type,
                    "active": True,
                    "count": error_count,
                    "detail_error": str(details.get('error', '')) if details else "",
                    "sent": False
                }
    
        # Case 3: First error or reactivating
        else:
            error_count = 1
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent": False
            }
    
        # Send message logic
        if error_count >= 3 and not error_data["last_error"].get("sent", False):
            # Check if there's a previous error that was being tracked
            if previous_error.get("active", False) and previous_error.get("sent", False):
                # New error reached 3 times during ongoing previous error
                prev_type = previous_error.get("type", "Unknown")
                prev_count = previous_error.get("count", 0)
                
                if error_type == "structure":
                    err = html.escape(str(details.get('error', '')))
                    msg = (
                        "⚠️ <b>Website Structure Changed!</b>\n"
                        f"Error details: <code>{err}</code>\n"
                        f"Occurred {error_count} times consecutively.\n"
                        "Please check and update the parser.\n\n"
                        f"📋 <b>Note:</b> Previous <b>{prev_type}</b> error had occurred {prev_count} times before this new error appeared."
                    )
                elif error_type == "manualTimeout":
                    err = html.escape(str(details.get('error', '')))
                    msg = (
                        "⚠️ <b>Manual Timeout Error!</b>\n"
                        f"Error details: <code>{err}</code>\n"
                        f"Occurred {error_count} times consecutively.\n"
                        "Could not fetch the notice page.\n\n"
                        f"📋 <b>Note:</b> Previous <b>{prev_type}</b> error had occurred {prev_count} times before this new error appeared."
                    )
                elif error_type == "network":
                    err = html.escape(str(details.get('error', '')))
                    msg = (
                        "⚠️ <b>Network Error!</b>\n"
                        f"Error details: <code>{err}</code>\n"
                        f"Occurred {error_count} times consecutively.\n"
                        "Could not fetch the notice page.\n\n"
                        f"📋 <b>Note:</b> Previous <b>{prev_type}</b> error had occurred {prev_count} times before this new error appeared."
                    )
                else:
                    msg = (
                        f"⚠️ <b>Unknown Error:</b> {html.escape(str(details))}\n"
                        f"Occurred {error_count} times consecutively.\n\n"
                        f"📋 <b>Note:</b> Previous <b>{prev_type}</b> error had occurred {prev_count} times before this new error appeared."
                    )
                
                # Forget the previous error after mentioning it
                error_data["previous_error"] = {"type": None, "count": 0, "sent": False, "active": False}
                
            else:
                # Regular error message (no previous error context)
                if error_type == "structure":
                    err = html.escape(str(details.get('error', '')))
                    msg = (
                        "⚠️ <b>Website Structure Changed!</b>\n"
                        f"Error details: <code>{err}</code>\n"
                        f"Occurred {error_count} times consecutively.\n"
                        "Please check and update the parser."
                    )
                elif error_type == "manualTimeout":
                    err = html.escape(str(details.get('error', '')))
                    msg = (
                        "⚠️ <b>Manual Timeout Error!</b>\n"
                        f"Error details: <code>{err}</code>\n"
                        f"Occurred {error_count} times consecutively.\n"
                        "Could not fetch the notice page."
                    )
                elif error_type == "network":
                    err = html.escape(str(details.get('error', '')))
                    msg = (
                        "⚠️ <b>Network Error!</b>\n"
                        f"Error details: <code>{err}</code>\n"
                        f"Occurred {error_count} times consecutively.\n"
                        "Could not fetch the notice page."
                    )
                else:
                    msg = f"⚠️ <b>Unknown Error:</b> {html.escape(str(details))}\nOccurred {error_count} times consecutively."
    
            if self.send_telegram_message(msg, disable_sound=True):
                error_data["last_error"]["sent"] = True
    
        self.save_error_state(error_data)
    def send_resolved_notification(self):
        error_data = self.load_error_state()
        last_error = error_data.get("last_error", {})
        previous_error = error_data.get("previous_error", {})

        # ---------------------------------------------------------
        # PRIORITY 1: Check if we are recovering from a GitHub Runner crash
        # ---------------------------------------------------------
        # If this script is running, the Runner is obviously fixed. 
        # We check if the last recorded error was a runner failure.
        if last_error.get("type") == "runner_failure" and last_error.get("active", False):
            
            # Only send a message if we actually alerted the user about the crash
            if last_error.get("sent", False):
                count = last_error.get("count", 0)
                msg = (
                    f"✅ <b>GitHub Action Fixed!</b>\n"
                    f"The internal runner failure occurred {count} times consecutively.\n"
                    "The monitor script has successfully started running again."
                )
                self.send_telegram_message(msg, disable_sound=True)
            
            # CRITICAL: Reset state completely. A runner crash resets the board.
            error_data["last_error"] = {"type": None, "active": False, "count": 0, "sent": False, "detail_error": ""}
            error_data["previous_error"] = {"type": None, "count": 0, "sent": False, "active": False}
            self.save_error_state(error_data)
            return  # Exit immediately, we are done.

        # ---------------------------------------------------------
        # PRIORITY 2: Standard Error Resolution (Network, Structure, etc.)
        # ---------------------------------------------------------
        if last_error.get("active", False):
            count = last_error.get("count", 0)
            error_type = last_error.get("type", "Unknown")
            was_sent = last_error.get("sent", False)
            
            # Case A: The current error was significant (>= 3 strikes) and sent
            if was_sent:
                msg = (
                    f"✅ <b>Error Resolved!</b>\n"
                    f"The previous error <b>{error_type}</b> occurred {count} time(s) consecutively.\n"
                    "The monitor is working again as expected."
                )
                self.send_telegram_message(msg, disable_sound=True)
            
            # Case B: Current error wasn't sent (<3 strikes), but we had a previous major error
            # Example: Network Error (Sent) -> Structure Error (1 time) -> Success
            elif not was_sent and previous_error.get("active", False):
                
                if previous_error.get("sent", False):
                    prev_type = previous_error.get("type", "Unknown")
                    prev_count = previous_error.get("count", 0)
                    msg = (
                        f"✅ <b>Error Resolved!</b>\n"
                        f"The previous error <b>{prev_type}</b> occurred {prev_count} time(s) consecutively.\n"
                        "The monitor is working again as expected."
                    )
                    self.send_telegram_message(msg, disable_sound=True)

        # ---------------------------------------------------------
        # FINAL STEP: Reset everything
        # ---------------------------------------------------------
        # Since the script ran successfully (reached this point), we clear all errors.
        error_data["last_error"] = {"type": None, "active": False, "count": 0, "sent": False, "detail_error": ""}
        error_data["previous_error"] = {"type": None, "count": 0, "sent": False, "active": False}
        
        self.save_error_state(error_data)
    def fetch_webpage(self):
        """Fetch the college notice webpage"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            return response.text
        except requests.exceptions.Timeout as e:
            self.send_error_notification("manualTimeout", {"error": str(e)})
            print(f"❌Timeout fetching webpage: {e}")
            runState= f"❌Timeout error fetching webpage: {e}"
            return runState
        except requests.exceptions.RequestException as e:
            self.send_error_notification("network", {"error": str(e)})
            print(f"Network error fetching webpage: {e}")
            runState = f"❌Network error fetching webpage: {e}"
            return runState
        

    def parse_notices(self, html_content):
        """Parse notices from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Try the main selector first
            tbody = soup.select_one("body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:gap-8 > div > table > tbody")
            rows = []
            if tbody:
                rows = tbody.find_all('tr', class_='hover:bg-gray-50')
            # Smart fallback: look for any table where a tr has 4 tds
            if not rows:
                for table in soup.find_all("table"):
                    for tr in table.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) >= 4:
                            rows = table.find_all("tr")
                            break
                    if rows:
                        print("used # Smart fallback: look for any table where a tr has 4 tds or more")
                        break
            if not rows:
                self.send_error_notification(
                    "structure",
                    {"error": "Could not find any table with rows containing 4 <td> elements."}
                )
                print("Could not find notice rows")
                return []
            notices = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >=4:
                    serial = cells[0].get_text(strip=True)
                    title = cells[1].get_text(strip=True)
                    date = cells[2].get_text(strip=True)
                    download_link = ""
                    link_element = cells[3].find('a')
                    if link_element and link_element.get('href'):
                        download_link = link_element.get('href')
                    notice_id = hashlib.md5(f"{title}{date}{download_link}".encode()).hexdigest()
                    notice = {
                        "id": notice_id,
                        "serial": serial,
                        "title": title,
                        "date": date,
                        "download_url": download_link,
                        "timestamp": datetime.now().isoformat()
                    }
                    notices.append(notice)
            return notices
        except Exception as e:
            self.send_error_notification("structure", {"error": f"Exception during parsing: {str(e)}"})
            print(f"Error parsing notices: {e}")
            return []
    
    def get_new_notices(self, current_notices, cached_notices):
        """Compare current notices with cached ones to find new notices"""
        cached_ids = {notice['id'] for notice in cached_notices}
        new_notices = []
        
        for notice in current_notices:
            if notice['id'] not in cached_ids:
                new_notices.append(notice)
        
        # Return latest 3 new notices
        return new_notices  #[:3]
    
    def send_telegram_message(self, message, disable_sound=False):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            print(disable_sound)
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
                "disable_notification": disable_sound
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            print("Telegram message sent successfully")
            return True
            
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
    
    def format_notice_message(self, notices):
        """Format notices for Telegram message"""
        if not notices:
            return None
        
        with open("log.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Take the last 3 lines (or fewer if file has less than 3 lines)
        last_lines = [line.strip() for line in lines[-3:]]

        # Split by "|" and take the 3rd portion (index 2) if available
        third_parts = []
        for line in last_lines:
            parts = line.split("|")
            if len(parts) >= 3:
                third_parts.append(parts[2].strip())
            else:
                third_parts.append("")  # fallback if line has < 3 parts

        # Compare third portions
        if len(set(third_parts)) == 1:
            # All same → just print last line
            message ="previously checked:\n"+ last_lines[-1]
        else:
            # Different → print all 3
            #for line in last_lines:
            third_parts_str = "\n".join(last_lines)
            message ="previously checked:\n" +  third_parts_str
        current_time = datetime.now(timezone(timedelta(hours=6)))
        message += f"\n🕐 Currently Checked at:\n{current_time.strftime('%Y-%m-%d %H:%M:%S')}"
        message  += f"\n🔔 <b>New Notice(s) from Dhaka College!</b>\n\n"
        
        for i, notice in enumerate(notices, 1):
            message += f"<b>{i}. {notice['title']}</b>\n"
            message += f"📅 Date: {notice['date']}\n"
            if notice['download_url']:
                message += f"📎 <a href='{notice['download_url']}'>Download PDF</a>\n"
            message += "\n"
        
        
        message += f"🌐 <a href='{self.url}'>View All Notices</a>"
        
        return message
    
    def run(self):

        print(f"Starting notice monitor at {datetime.now()}")
        runState="📢script started"
        
        # Validate environment variables
        if not self.telegram_token or not self.telegram_chat_id:
            print("Error: TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
            runState="❌telegram token or chat id is invalid"
            return runState
        
        # Load cached data
        cache_data = self.load_cache()
        
        # Fetch current webpage
        html_content = self.fetch_webpage()
        if html_content == None:
            print("❌error fetching webpage(html_content is None)")
            runState = "❌error fetching webpage(html_content is None)"
            return runState
        if "error fetching webpage" in html_content.lower():  
            runState = html_content
            print(html_content)
            return runState 
        else:
            print("✅Page fetched successfully")
            runState = "✅Page fetched successfully"
        
        # Parse current notices
        current_notices = self.parse_notices(html_content)
        
        if not current_notices:
            print("❌No notices found on the webpage")
            self.send_error_notification(
                "structure",
                {"error": "No notices found on the webpage. The HTML structure may have changed."}
            )
            runState="❌No notices found on the webpage. The HTML structure may have changed."
            return runState

        self.send_resolved_notification()
        print(f"Found {len(current_notices)} total notices")
        runState = f"📢Found {len(current_notices)} total notices"
        
        # Find new notices
        new_notices = self.get_new_notices(current_notices, cache_data.get("notices", []))
        
        if new_notices:
            print(f"Found {len(new_notices)} new notices")
            runState = f"📢Found {len(new_notices)} new notices"
            
            # Send Telegram notification
            message = self.format_notice_message(new_notices)
            if message:
                if "noc" in message.lower() and {len(new_notices)} == 1:
                    disable_sound = True
                else:
                    disable_sound = False
                success = self.send_telegram_message(message, disable_sound)
                if success:
                    print("Notification sent successfully")
                    runState += " --> sent to telegram bot"
                    # Update cache with current data
                    cache_data["notices"] = current_notices
                    cache_data["last_check"] = datetime.now().isoformat()
                    self.save_cache(cache_data)
                else:
                    print("Failed to send notification")
                    runState += " -->❌ filed to send notification"
        else:
            print("No new notices found")
            runState = "🎈No new notices found"
        
        print("Monitor execution completed")
        return runState

if __name__ == "__main__":
    start = datetime.now(timezone(timedelta(hours=6)))
    monitor = NoticeMonitor()
    runState = monitor.run()
    end = datetime.now(timezone(timedelta(hours=6)))
    elapsed = (end - start).total_seconds()  
    logTxt = f"{start.strftime('%Y-%m-%d %H:%M:%S')} |  {elapsed:.2f}s   | {runState}"
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(logTxt + "\n")
        summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        print(runState)
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(runState + "\n")
    else:
        # Local run: just print instead of writing to GitHub summary
        print(f"[Local Summary] {runState}")
