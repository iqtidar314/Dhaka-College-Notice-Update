import os
import json
import requests
from bs4 import BeautifulSoup
import hashlib
from datetime import datetime
import sys

class NoticeMonitor:
    def __init__(self):
        self.url = "https://www.dhakacollege.edu.bd/en/notice"
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.cache_file = 'notice_cache.json'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def load_cache(self):
        """Load cached data from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"notices": [], "last_update": None}
        except Exception as e:
            print(f"Error loading cache: {e}")
            return {"notices": [], "last_update": None}
    
    def save_cache(self, data):
        """Save data to cache file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def fetch_webpage(self):
        """Fetch the college notice webpage"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching webpage: {e}")
            return None
    
    def parse_notices(self, html_content):
        """Parse notices from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the specific table body using the CSS selector
            selector = "body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:flex-row.lg\\:gap-8 > div > table > tbody"
            tbody = soup.select_one(selector)
            
            if not tbody:
                # Fallback to find table tbody in main section
                tbody = soup.select_one("main table tbody")
                
            if not tbody:
                print("Could not find the notices table")
                return []
            
            notices = []
            rows = tbody.find_all('tr', class_='hover:bg-gray-50')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    # Extract notice details
                    serial = cells[0].get_text(strip=True)
                    title = cells[1].get_text(strip=True)
                    date = cells[2].get_text(strip=True)
                    
                    # Extract download link
                    download_link = ""
                    link_element = cells[3].find('a')
                    if link_element and link_element.get('href'):
                        download_link = link_element.get('href')
                    
                    # Create unique ID for the notice
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
        return new_notices[:3]
    
    def send_telegram_message(self, message):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
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
        """Main execution function"""
        print(f"Starting notice monitor at {datetime.now()}")
        
        # Validate environment variables
        if not self.telegram_token or not self.telegram_chat_id:
            print("Error: TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
            sys.exit(1)
        
        # Load cached data
        cache_data = self.load_cache()
        
        # Fetch current webpage
        html_content = self.fetch_webpage()
        if not html_content:
            print("Failed to fetch webpage")
            sys.exit(1)
        
        # Parse current notices
        current_notices = self.parse_notices(html_content)
        if not current_notices:
            print("No notices found on the webpage")
            return
        
        print(f"Found {len(current_notices)} total notices")
        
        # Find new notices
        new_notices = self.get_new_notices(current_notices, cache_data.get("notices", []))
        
        if new_notices:
            print(f"Found {len(new_notices)} new notices")
            
            # Send Telegram notification
            message = self.format_notice_message(new_notices)
            if message:
                success = self.send_telegram_message(message)
                if success:
                    print("Notification sent successfully")
                    # Update cache with current data
                    cache_data["notices"] = current_notices
                    cache_data["last_update"] = datetime.now().isoformat()
                    self.save_cache(cache_data)
                else:
                    print("Failed to send notification")
        else:
            print("No new notices found")
            
        print("Monitor execution completed")

if __name__ == "__main__":
    monitor = NoticeMonitor()
    monitor.run()
