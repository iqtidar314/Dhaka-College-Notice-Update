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
        self.error_cache_file = 'error_cache.json'
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
    
    def load_error_cache(self):
        """Load error tracking cache"""
        try:
            if os.path.exists(self.error_cache_file):
                with open(self.error_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "structure_error": {"active": False, "last_selectors": None, "count": 0},
                "network_error": {"active": False, "last_error": None, "count": 0}
            }
        except Exception as e:
            print(f"Error loading error cache: {e}")
            return {
                "structure_error": {"active": False, "last_selectors": None, "count": 0},
                "network_error": {"active": False, "last_error": None, "count": 0}
            }
    
    def save_cache(self, data):
        """Save data to cache file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def save_error_cache(self, data):
        """Save error tracking cache"""
        try:
            with open(self.error_cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving error cache: {e}")
    
    def get_current_selectors(self, soup):
        """Get current selectors that are actually working"""
        selectors = {"tbody": None, "tr": None}
        
        # Try to find tbody with various selectors
        tbody_selectors = [
            "body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:flex-row.lg\\:gap-8 > div > table > tbody",
            "main table tbody",
            "table tbody",
            "tbody"
        ]
        
        tbody = None
        for selector in tbody_selectors:
            tbody = soup.select_one(selector)
            if tbody:
                selectors["tbody"] = selector
                break
        
        if tbody:
            # Find tr elements
            rows = tbody.find_all('tr', class_='hover:bg-gray-50')
            if rows:
                selectors["tr"] = "tr.hover\\:bg-gray-50"
            else:
                rows = tbody.find_all('tr')
                if rows:
                    selectors["tr"] = "tr"
        
        return selectors
    
    def send_error_notification(self, error_type, message):
        """Send error notification to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            error_message = f"🚨 <b>Dhaka College Monitor Error</b>\n\n"
            error_message += f"<b>Type:</b> {error_type}\n"
            error_message += f"<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            error_message += message
            
            data = {
                "chat_id": self.telegram_chat_id,
                "text": error_message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            print(f"Error notification sent: {error_type}")
            return True
            
        except Exception as e:
            print(f"Failed to send error notification: {e}")
            return False
    
    def fetch_webpage(self):
        """Fetch the college notice webpage with error tracking"""
        error_cache = self.load_error_cache()
        
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Success - check if we need to send resolution message
            if error_cache["network_error"]["active"]:
                resolution_msg = f"✅ <b>Network Issue Resolved</b>\n\n"
                resolution_msg += f"The website is now accessible again.\n"
                resolution_msg += f"Previous error occurred {error_cache['network_error']['count']} times."
                
                self.send_error_notification("Network Resolution", resolution_msg)
                
                # Reset network error status
                error_cache["network_error"] = {"active": False, "last_error": None, "count": 0}
                self.save_error_cache(error_cache)
            
            return response.text
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout) as e:
            error_msg = f"Connection timeout after 30 seconds"
            self.handle_network_error(error_cache, "Timeout", error_msg)
            return None
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection failed: {str(e)}"
            self.handle_network_error(error_cache, "Connection Error", error_msg)
            return None
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {response.status_code}: {str(e)}"
            self.handle_network_error(error_cache, "HTTP Error", error_msg)
            return None
            
        except Exception as e:
            error_msg = f"Unexpected network error: {str(e)}"
            self.handle_network_error(error_cache, "Network Error", error_msg)
            return None
    
    def handle_network_error(self, error_cache, error_type, error_msg):
        """Handle network errors with notification logic"""
        if not error_cache["network_error"]["active"]:
            # First occurrence of network error
            message = f"<b>Details:</b> {error_msg}\n\n"
            message += "The monitor will continue trying. You'll be notified when it's resolved."
            
            self.send_error_notification(error_type, message)
            
            error_cache["network_error"] = {
                "active": True,
                "last_error": error_msg,
                "count": 1
            }
        else:
            # Ongoing network error - just increment count, don't send message
            error_cache["network_error"]["count"] += 1
            print(f"Network error continues (count: {error_cache['network_error']['count']})")
        
        self.save_error_cache(error_cache)
    
    def parse_notices(self, html_content):
        """Parse notices from HTML content with structure error tracking"""
        error_cache = self.load_error_cache()
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            current_selectors = self.get_current_selectors(soup)
            
            # Original selector attempt
            selector = "body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:flex-row.lg\\:gap-8 > div > table > tbody"
            tbody = soup.select_one(selector)
            
            if not tbody:
                # Fallback attempt
                tbody = soup.select_one("main table tbody")
                
            if not tbody:
                # Structure error detected
                self.handle_structure_error(error_cache, current_selectors)
                return []
            
            # Try to find rows
            rows = tbody.find_all('tr', class_='hover:bg-gray-50')
            
            if not rows:
                # Different tr structure
                rows = tbody.find_all('tr')
                if not rows:
                    self.handle_structure_error(error_cache, current_selectors)
                    return []
            
            # Success - check if we need to send resolution message
            if error_cache["structure_error"]["active"]:
                resolution_msg = f"✅ <b>Structure Issue Resolved</b>\n\n"
                resolution_msg += f"The website structure is working again.\n"
                resolution_msg += f"Previous error occurred {error_cache['structure_error']['count']} times.\n\n"
                resolution_msg += f"<b>Current working selectors:</b>\n"
                resolution_msg += f"• tbody: {current_selectors['tbody']}\n"
                resolution_msg += f"• tr: {current_selectors['tr']}"
                
                self.send_error_notification("Structure Resolution", resolution_msg)
                
                # Reset structure error status
                error_cache["structure_error"] = {"active": False, "last_selectors": None, "count": 0}
                self.save_error_cache(error_cache)
            
            # Parse notices (your existing logic)
            notices = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 4:
                    serial = cells[0].get_text(strip=True)
                    title = cells[1].get_text(strip=True)
                    date = cells[2].get_text(strip=True)
                    
                    download_link = ""
                    link_element = cells[3].find('a')
                    if link_element and link_element.get('href'):
                        download_link = link_element.get('href')
                    
                    notice_id = hashlib.md5(f"{title}{download_link}".encode()).hexdigest() #{notice.get('date', '')}
                    
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
            current_selectors = {"tbody": "parsing_error", "tr": "parsing_error"}
            self.handle_structure_error(error_cache, current_selectors)
            return []
    
    def handle_structure_error(self, error_cache, current_selectors):
        """Handle structure errors with notification logic"""
        if not error_cache["structure_error"]["active"]:
            # First occurrence of structure error
            original_selectors = {
                "tbody": "body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:flex-row.lg\\:gap-8 > div > table > tbody",
                "tr": "tr.hover\\:bg-gray-50"
            }
            
            message = f"The website's HTML structure has changed.\n\n"
            message += f"<b>Expected selectors (before):</b>\n"
            message += f"• tbody: <code>{original_selectors['tbody']}</code>\n"
            message += f"• tr: <code>{original_selectors['tr']}</code>\n\n"
            message += f"<b>Current detected selectors (after):</b>\n"
            message += f"• tbody: <code>{current_selectors['tbody'] or 'NOT FOUND'}</code>\n"
            message += f"• tr: <code>{current_selectors['tr'] or 'NOT FOUND'}</code>\n\n"
            message += "The script needs to be updated to work with the new structure."
            
            self.send_error_notification("Structure Change", message)
            
            error_cache["structure_error"] = {
                "active": True,
                "last_selectors": current_selectors,
                "count": 1
            }
        else:
            # Ongoing structure error - just increment count
            error_cache["structure_error"]["count"] += 1
            print(f"Structure error continues (count: {error_cache['structure_error']['count']})")
        
        self.save_error_cache(error_cache)
    
	def get_notices_hash(self, notices):
	    """Generate hash of notices content for change detection"""
	    try:
	        notices_content = []
	        for notice in notices:
	            content = f"{notice.get('title', '')}{notice.get('date', '')}{notice.get('download_url', '')}"
	            notices_content.append(content)  # ✅ added append

	        notices_content.sort()
	        combined_content = "".join(notices_content)

	        return hashlib.md5(combined_content.encode()).hexdigest()
	    except Exception as e:
	        print(f"Error generating notices hash: {e}")
	        return ""



    
    def get_new_notices(self, current_notices, cached_notices):
        """Compare current notices with cached ones to find new notices"""
        cached_ids = {notice['id'] for notice in cached_notices}
        new_notices = []
        
        for notice in current_notices:
            if notice['id'] not in cached_ids:
                new_notices.append(notice)
        
        return new_notices
    
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
            """Main execution function with improved cache management"""
            print(f"Starting notice monitor at {datetime.now()}")
        
            # Validate environment variables
            if not self.telegram_token or not self.telegram_chat_id:
                print("Error: TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
                sys.exit(1)
        
            # Load cached data
            cache_data = self.load_cache()
        
            # Fetch current webpage (now with error tracking)
            html_content = self.fetch_webpage()
            if not html_content:
                print("Failed to fetch webpage - exiting without cache update")
                sys.exit(1)
        
            # Parse current notices (now with structure error tracking)
            current_notices = self.parse_notices(html_content)
            if not current_notices:
                print("No notices found on the webpage - exiting without cache update")
                return
        
            print(f"Found {len(current_notices)} total notices")
        
            # Find new notices
            new_notices = self.get_new_notices(current_notices, cache_data.get("notices", []))
        
            # Check if content has changed (for existing notices)
            current_notices_hash = self.get_notices_hash(current_notices)
            cached_notices_hash = self.get_notices_hash(cache_data.get("notices", []))
            content_changed = current_notices_hash != cached_notices_hash
        
            # Flag to track if we should update cache
            should_update_cache = False
        
            if new_notices:
                print(f"Found {len(new_notices)} new notices")
            
                # Send Telegram notification
                message = self.format_notice_message(new_notices)
                if message:
                    success = self.send_telegram_message(message)
                    if success:
                        print("Notification sent successfully")
                        should_update_cache = True
                    else:
                        print("Failed to send notification - cache not updated")
            elif content_changed:
                print("No new notices, but existing content changed")
                should_update_cache = True
            else:
                print("No new notices and no content changes detected")
                # Update last_check timestamp only, but keep same notices
                cache_data["last_check"] = datetime.now().isoformat()
                self.save_cache(cache_data)
                print("Updated last_check timestamp only")
                return
        
            # Update cache only when there are actual changes
            if should_update_cache:
                cache_data["notices"] = current_notices
                cache_data["last_check"] = datetime.now().isoformat()
                self.save_cache(cache_data)
                print("Cache updated with current notices")
        
            print("Monitor execution completed")
if __name__ == "__main__":
    monitor = NoticeMonitor()
    monitor.run()
