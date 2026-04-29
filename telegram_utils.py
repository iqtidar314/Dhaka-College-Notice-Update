"""
Telegram Utilities for Dhaka College Notice Monitor
Handles media groups, inline buttons, documents, and dashboard editing
"""

import os
import requests
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta


class TelegramUtils:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.api_base = f"https://api.telegram.org/bot{self.token}"
        
        # Branding
        self.branding_name = "The DC Archive — Notice"
        self.facebook_link = "https://www.facebook.com/thedcarchive"
        self.telegram_link = "https://t.me/thedcarchive_notice"
        self.website_link = "https://www.dhakacollege.edu.bd/en/notice"
    
    def _make_request(self, method: str, data: Dict, files: Dict = None) -> Optional[Dict]:
        """Make a request to Telegram API"""
        try:
            url = f"{self.api_base}/{method}"
            response = requests.post(url, data=data, files=files, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                return result.get('result')
            else:
                print(f"❌ Telegram API error: {result.get('description')}")
                return None
        
        except Exception as e:
            print(f"❌ Error calling {method}: {e}")
            return None
    
    def format_notice_caption(self, notice: Dict) -> str:
        """Format a notice caption with HTML"""
        title = notice.get('title', 'Unknown')
        date = notice.get('date', 'Unknown')
        serial = notice.get('serial', '?')
        download_url = notice.get('download_url', '')
        
        caption = f"""📢 <b>{self.branding_name}</b>

<b>{title}</b>
📅 {date}
🔖 Serial: {serial}

"""
        
        if download_url:
            caption += f"🔗 <a href='{download_url}'>Download PDF</a>\n"
        
        caption += f"""🌐 <a href='{self.website_link}'>View on Website</a>
👥 <a href='{self.facebook_link}'>The DC Archive on Facebook</a>
📡 <a href='{self.telegram_link}'>Telegram Channel</a>"""
        
        return caption
    
    def format_removed_caption(self, notice: Dict) -> str:
        """Format a removed notice notification"""
        title = notice.get('title', 'Unknown')
        date = notice.get('date', 'Unknown')
        serial = notice.get('serial', '?')
        
        return f"""🗑️ <b>Notice Removed from Website</b>

<b>{title}</b>
📅 Was published: {date}
🔖 Serial: {serial}

This notice was on the front page and is no longer available."""
    
    def get_inline_keyboard(self, download_url: str = None) -> Dict:
        """Generate inline keyboard markup"""
        buttons = [
            {"text": "Visit DC Archive FB", "url": self.facebook_link},
        ]
        
        if download_url:
            buttons.append({"text": "Download PDF", "url": download_url})
        
        buttons.append({"text": "View on Website", "url": self.website_link})
        
        return {
            "inline_keyboard": [buttons]
        }
    
    def send_photo(self, photo_bytes: bytes, caption: str, 
                   inline_buttons: Dict = None, disable_notification: bool = False) -> Optional[Dict]:
        """Send a photo with caption"""
        data = {
            "chat_id": self.chat_id,
            "caption": caption,
            "parse_mode": "HTML",
            "disable_notification": disable_notification
        }
        
        if inline_buttons:
            data["reply_markup"] = inline_buttons
        
        files = {"photo": ("notice.png", photo_bytes, "image/png")}
        
        result = self._make_request("sendPhoto", data, files)
        if result:
            print(f"✅ Photo sent: message_id={result.get('message_id')}")
        return result
    
    def send_media_group(self, images: List[bytes], caption: str,
                         disable_notification: bool = False) -> Optional[List[Dict]]:
        """
        Send a media group (album) of images
        Telegram limits to 10 media per group
        """
        if not images:
            return None
        
        results = []
        
        # Split into groups of 10
        for i in range(0, len(images), 10):
            group = images[i:i+10]
            
            # Build media array
            media = []
            files = {}
            
            for idx, img_bytes in enumerate(group):
                media.append({
                    "type": "photo",
                    "media": f"attach://photo{idx}",
                    "caption": caption if idx == 0 else "",
                    "parse_mode": "HTML"
                })
                files[f"photo{idx}"] = (f"page_{i+idx}.png", img_bytes, "image/png")
            
            data = {
                "chat_id": self.chat_id,
                "media": str(media).replace("'", '"'),
                "disable_notification": disable_notification
            }
            
            result = self._make_request("sendMediaGroup", data, files)
            if result:
                print(f"✅ Media group sent: {len(group)} images")
                results.extend(result)
        
        return results if results else None
    
    def send_document(self, file_bytes: bytes, filename: str, 
                      caption: str = None, disable_notification: bool = True) -> Optional[Dict]:
        """Send a document (PDF) without preview"""
        data = {
            "chat_id": self.chat_id,
            "caption": caption,
            "parse_mode": "HTML",
            "disable_notification": disable_notification,
            "disable_content_type_detection": True
        }
        
        files = {"document": (filename, file_bytes, "application/pdf")}
        
        result = self._make_request("sendDocument", data, files)
        if result:
            print(f"✅ Document sent: {filename}")
        return result
    
    def send_message(self, text: str, inline_buttons: Dict = None,
                     disable_notification: bool = False) -> Optional[Dict]:
        """Send a text message"""
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_notification": disable_notification,
            "disable_web_page_preview": True
        }
        
        if inline_buttons:
            data["reply_markup"] = inline_buttons
        
        result = self._make_request("sendMessage", data)
        if result:
            print(f"✅ Message sent: message_id={result.get('message_id')}")
        return result
    
    def edit_message(self, message_id: int, text: str, 
                     inline_buttons: Dict = None) -> Optional[Dict]:
        """Edit an existing message"""
        data = {
            "chat_id": self.chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        if inline_buttons:
            data["reply_markup"] = inline_buttons
        
        result = self._make_request("editMessageText", data)
        if result:
            print(f"✅ Message edited: {message_id}")
        return result
    
    def pin_message(self, message_id: int, disable_notification: bool = True) -> Optional[Dict]:
        """Pin a message in the chat"""
        data = {
            "chat_id": self.chat_id,
            "message_id": message_id,
            "disable_notification": disable_notification
        }
        
        result = self._make_request("pinChatMessage", data)
        if result:
            print(f"✅ Message pinned: {message_id}")
        return result
    
    def send_notice_with_media(self, notice: Dict, images: List[bytes], 
                                pdf_bytes: bytes = None) -> List[Dict]:
        """
        Send a complete notice notification:
        1. Media group with all images
        2. PDF document (if provided)
        """
        results = []
        caption = self.format_notice_caption(notice)
        inline_buttons = self.get_inline_keyboard(notice.get('download_url'))
        
        # Send media group
        if images:
            media_result = self.send_media_group(images, caption)
            if media_result:
                results.extend(media_result)
        else:
            # No images, send text only
            msg_result = self.send_message(caption, inline_buttons)
            if msg_result:
                results.append(msg_result)
        
        # Send PDF document separately
        if pdf_bytes:
            filename = f"notice_{notice.get('serial', 'unknown')}.pdf"
            doc_caption = f"📄 Original PDF: {notice.get('title', 'Notice')[:50]}"
            doc_result = self.send_document(pdf_bytes, filename, doc_caption)
            if doc_result:
                results.append(doc_result)
        
        return results
    
    def send_removed_notification(self, notice: Dict) -> Optional[Dict]:
        """Send a removed notice notification"""
        caption = self.format_removed_caption(notice)
        return self.send_message(caption)


if __name__ == "__main__":
    # Test telegram utils
    utils = TelegramUtils()
    
    # Test caption formatting
    test_notice = {
        'title': 'Test Notice Title',
        'date': '2026-04-29',
        'serial': '123',
        'download_url': 'https://example.com/notice.pdf'
    }
    
    print("Caption format test:")
    print(utils.format_notice_caption(test_notice))
    print("\nRemoved notification test:")
    print(utils.format_removed_caption(test_notice))
