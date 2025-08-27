#!/usr/bin/env python3
"""
Website Change Monitor for Dhaka College Notice Board
Monitors changes and sends notifications via Telegram
"""

import os
import sys
import json
import time
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration
COLLEGE_URL = "https://www.dhakacollege.edu.bd/en/notice"
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CACHE_DIR = "cache"
CACHE_FILE = f"{CACHE_DIR}/last_state.json"
ERROR_COUNT_FILE = f"{CACHE_DIR}/error_count.json"

# CSS Selector for the target table body
TARGET_SELECTOR = "body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:flex-row.lg\\:gap-8 > div > table > tbody"

def ensure_cache_dir():
    """Create cache directory if it doesn't exist"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def load_cache():
    """Load previous state from cache"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                print(json.load(f))
                return json.load(f)
    except Exception as e:
        print(f"Error loading cache: {e}")
    
    return {"last_hash": "", "last_notices": []}

def save_cache(data):
    """Save current state to cache"""
    try:
        ensure_cache_dir()
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def load_error_count():
    """Load error count from cache"""
    try:
        if os.path.exists(ERROR_COUNT_FILE):
            with open(ERROR_COUNT_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {"count": 0}

def save_error_count(count):
    """Save error count to cache"""
    try:
        ensure_cache_dir()
        with open(ERROR_COUNT_FILE, 'w') as f:
            json.dump({"count": count}, f)
    except Exception as e:
        print(f"Error saving error count: {e}")

def send_telegram_message(message):
    """Send message to Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram credentials")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print("Telegram message sent successfully")
            return True
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def fetch_webpage():
    """Fetch the college notice webpage"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(COLLEGE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching webpage: {e}")
        return None

def parse_notices(html_content):
    """Parse notices from HTML content"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the target table body
        tbody = soup.select_one("main section div table tbody")
        
        if not tbody:
            print("Could not find the target table body")
            return None, None
        
        # Get all table rows
        rows = tbody.find_all('tr')
        notices = []
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 4:
                # Extract notice data
                serial = cells[0].get_text(strip=True)
                title = cells[1].get_text(strip=True)
                date = cells[2].get_text(strip=True)
                
                # Extract download link
                download_link = ""
                link_elem = cells[3].find('a')
                if link_elem and link_elem.get('href'):
                    download_link = link_elem.get('href')
                
                notices.append({
                    'serial': serial,
                    'title': title,
                    'date': date,
                    'download_link': download_link
                })
        
        # Create hash of the table content for change detection
        table_html = str(tbody)
        content_hash = hashlib.md5(table_html.encode('utf-8')).hexdigest()
        
        return notices, content_hash
        
    except Exception as e:
        print(f"Error parsing notices: {e}")
        return None, None

def get_new_notices(current_notices, last_notices):
    """Compare current and last notices to find new ones"""
    if not last_notices:
        return []
    
    # Get the top 3 current notices for comparison
    current_top = current_notices[:3] if len(current_notices) >= 3 else current_notices
    last_top = last_notices[:3] if len(last_notices) >= 3 else last_notices
    
    new_notices = []
    
    # Check if there are new notices at the top
    for i, current_notice in enumerate(current_top):
        if i < len(last_top):
            if current_notice['title'] != last_top[i]['title']:
                # New notice found at position i
                new_notices.append(current_notice)
        else:
            # More notices than before
            new_notices.append(current_notice)
    
    return new_notices

def format_telegram_message(new_notices):
    """Format new notices for Telegram message"""
    if not new_notices:
        return ""
    
    message = "🆕 <b>New Notice(s) Added to Dhaka College!</b>\n\n"
    
    for i, notice in enumerate(new_notices, 1):
        message += f"{i}. <b>{notice['title']}</b>\n"
        message += f"📅 Date: {notice['date']}\n"
        if notice['download_link']:
            message += f"📎 <a href='{notice['download_link']}'>Download PDF</a>\n"
        message += "\n"
    
    message += f"⏰ Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    return message

def handle_error():
    """Handle errors and send notification if needed"""
    error_data = load_error_count()
    error_count = error_data.get('count', 0) + 1
    
    save_error_count(error_count)
    
    # Send error notification every 10th check
    if error_count % 10 == 0:
        error_message = f"⚠️ <b>Website Monitor Alert</b>\n\n"
        error_message += f"The Dhaka College notice website has been inaccessible for the last {error_count} checks.\n\n"
        error_message += f"Last check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        error_message += f"Website: {COLLEGE_URL}"
        
        send_telegram_message(error_message)
    
    print(f"Error count: {error_count}")

def reset_error_count():
    """Reset error count when website is accessible"""
    save_error_count(0)

def main():
    """Main monitoring function"""
    print(f"Starting website monitor at {datetime.now()}")
    
    # Load previous state
    cache_data = load_cache()
    last_hash = cache_data.get('last_hash', '')
    last_notices = cache_data.get('last_notices', [])
    print("hash and last notice loaded")
    # Fetch current webpage
    html_content = fetch_webpage()
    if not html_content:
        handle_error()
        return
    
    # Parse notices
    current_notices, current_hash = parse_notices(html_content)
    if current_notices is None:
        handle_error()
        return
    
    # Reset error count on successful fetch
    reset_error_count()
    
    print(f"Found {len(current_notices)} notices")
    
    # Check for changes
    if current_hash != last_hash:
        print("Changes detected!")
        
        # Get new notices (only from the top)
        new_notices = get_new_notices(current_notices, last_notices)
        
        if new_notices:
            print(f"Found {len(new_notices)} new notice(s)")
            
            # Send notification
            message = format_telegram_message(new_notices)
            if send_telegram_message(message):
                print("Notification sent successfully")
            else:
                print("Failed to send notification")
        else:
            print("Changes detected but no new notices at the top")
    else:
        print("No changes detected")
    
    # Save current state
    cache_data = {
        'last_hash': current_hash,
        'last_notices': current_notices,
        'last_check': datetime.now().isoformat()
    }
    save_cache(cache_data)
    
    print("Monitor check completed")

if __name__ == "__main__":
    main()
