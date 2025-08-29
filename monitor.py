
import os
import json
import requests
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime
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

        # Increment error counter if same error, reset if different
        if last_error.get("type") == error_type:
            error_count = last_error.get("count", 0) + 1
        else:
            error_count = 1  # first occurrence of new error
        if last_error.get("sent", False) and last_error.get("type") == error_type:
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent": True
            }
        else: 
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent": False
            }

        # Only send Telegram message if error occurred 3 times consecutively
        if error_count >= 3 and not last_error.get("sent", False):
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

            if self.send_telegram_message(msg, disable_sound = True):
                error_data["last_error"]["sent"] = True

        self.save_error_state(error_data)

    def send_resolved_notification(self):
        error_data = self.load_error_state()
        last_error = error_data.get("last_error", {})

        if last_error.get("active", False):
            count = last_error.get("count", 0)
            error_type = last_error.get("type", "Unknown")
            msg = (
                f"✅ <b>Error Resolved!</b>\n"
                f"The previous error <b>{error_type}</b> occurred {count} time(s) consecutively.\n"
                "The monitor is working again as expected."
            )
            if last_error.get("sent", False):
                if not self.send_telegram_message(msg, disable_sound = True):
                    return
            # Reset error state
            error_data["last_error"] = {"type": None, "active": False, "count": 0, "sent": False, "detail_error": ""}
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
        
        message = "🔔 <b>New Notice(s) from Dhaka College!</b>\n\n"
        
        for i, notice in enumerate(notices, 1):
            message += f"<b>{i}. {notice['title']}</b>\n"
            message += f"📅 Date: {notice['date']}\n"
            if notice['download_url']:
                message += f"📎 <a href='{notice['download_url']}'>Download PDF</a>\n"
            message += "\n"
        
        message += f"🕐 Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
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
    start = datetime.now()
    monitor = NoticeMonitor()
    runState = monitor.run()
    end = datetime.now()
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
