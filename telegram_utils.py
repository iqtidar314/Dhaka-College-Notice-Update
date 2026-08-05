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
            result = response.json()
            
            if result.get('ok'):
                return result.get('result')
            else:
                print(f"❌ Telegram API error ({method}): {result.get('description')}")
                print(f"   Response: {result}")
                return None
        
        except Exception as e:
            print(f"❌ Error calling {method}: {e}")
            try:
                print(f"   Response text: {response.text}")
            except:
                pass
            return None
    
    def build_notice_caption(self, notice: Dict, change_type: str) -> str:
        change_icons = {
            "NEW":               "🆕",
            "EDITED":            "✏️",
            "PDF_REPLACED":      "🔄",
            "REMOVED_FROM_PAGE_1": "📤",
        }
        change_label = {
            "NEW":               "NEW NOTICE",
            "EDITED":            "UPDATED",
            "PDF_REPLACED":      "PDF REPLACED",
            "REMOVED_FROM_PAGE_1": "MOVED OFF PAGE 1",
        }

        icon  = change_icons.get(change_type, "📌")
        label = change_label.get(change_type, "NOTICE")
        
        # Truncate title if too long
        title = notice.get('title', 'Unknown')
        if len(title) > 100:
            title = title[:97] + "..."

        caption = (
            f"{icon} <b>{label}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>{title}</b>\n"
            f"\n"
            f"<code>📅 {notice.get('date', 'Unknown')}  |  #️⃣ Serial {notice.get('serial', '?')}</code>\n"
        )
        return caption

    def build_album_caption(self, notice: Dict, change_type: str, part: int, total_parts: int) -> str:
        if total_parts == 1:
            return self.build_notice_caption(notice, change_type)
        
        change_icons = {
            "NEW":               "🆕",
            "EDITED":            "✏️",
            "PDF_REPLACED":      "🔄",
            "REMOVED_FROM_PAGE_1": "📤",
        }
        change_label = {
            "NEW":               "NEW NOTICE",
            "EDITED":            "UPDATED",
            "PDF_REPLACED":      "PDF REPLACED",
            "REMOVED_FROM_PAGE_1": "MOVED OFF PAGE 1",
        }

        icon  = change_icons.get(change_type, "📌")
        label = change_label.get(change_type, "NOTICE")
        title = notice.get('title', 'Unknown')
        if len(title) > 100:
            title = title[:97] + "..."
            
        if part == 1:
            return (
                f"{icon} <b>{label}</b>  <code>Part 1 of {total_parts}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>{title}</b>\n\n"
                f"<code>📅 {notice.get('date', 'Unknown')}  |  #️⃣ Serial {notice.get('serial', '?')}</code>"
            )
        else:
            return (
                f"<code>📄 Continued — Part {part} of {total_parts}</code>\n"
                f"<b>{title}</b>"
            )

    def get_forward_footer(self) -> str:
        return (
            "\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🏛 <b>The DC Archive</b> — Dhaka College Notice Monitor\n"
            "📢 <a href='https://t.me/thedcarchive_notice'>Subscribe for instant alerts</a>"
        )

    def format_removed_caption(self, notice: Dict) -> str:
        """Format a removed notice notification"""
        title = notice.get('title', 'Unknown')
        date = notice.get('date', 'Unknown')
        serial = notice.get('serial', '?')
        
        return f"""📤 <b>Notice Removed from Website</b>
━━━━━━━━━━━━━━━━━━━━
<b>{title}</b>

<code>📅 {date}  |  #️⃣ Serial {serial}</code>

This notice was on the front page and is no longer available.
{self.get_forward_footer()}"""
    
    def build_inline_keyboard(self, notice: Dict) -> Dict:
        """Generate inline keyboard markup 2x2 grid"""
        download_url = notice.get('download_url') or self.website_link
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "⬇️ Download PDF",
                        "url": download_url
                    },
                    {
                        "text": "🌐 View on Website",
                        "url": self.website_link
                    }
                ],
                [
                    {
                        "text": "👥 Facebook",
                        "url": self.facebook_link
                    },
                    {
                        "text": "📢 Join Channel",
                        "url": self.telegram_link
                    }
                ]
            ]
        }
        return keyboard
    
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
    
    def send_media_group(self, images: List[bytes], notice: Dict, change_type: str,
                         disable_notification: bool = False) -> Optional[List[Dict]]:
        """
        Send a media group (album) of images
        Telegram limits to 10 media per group
        """
        if not images:
            return None
        
        import json
        
        results = []
        total_parts = (len(images) + 9) // 10
        
        # Split into groups of 10
        for i in range(0, len(images), 10):
            group = images[i:i+10]
            part = (i // 10) + 1
            
            # Build media array
            media = []
            files = {}
            
            caption = self.build_album_caption(notice, change_type, part, total_parts)
            caption += self.get_forward_footer()
            
            # Ensure caption is under 1024 characters
            if len(caption) > 1024:
                caption = caption[:1020] + "..."
            
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
                "media": json.dumps(media),
                "disable_notification": disable_notification
            }
            
            result = self._make_request("sendMediaGroup", data, files)
            if result:
                print(f"✅ Media group sent: {len(group)} images (Part {part}/{total_parts})")
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
        import json
        
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_notification": disable_notification,
            "disable_web_page_preview": True
        }
        
        if inline_buttons:
            data["reply_markup"] = json.dumps(inline_buttons)
        
        result = self._make_request("sendMessage", data)
        if result:
            print(f"✅ Message sent: message_id={result.get('message_id')}")
        return result
    
    def edit_message(self, message_id: int, text: str, 
                     inline_buttons: Dict = None) -> Optional[Dict]:
        """Edit an existing message"""
        import json
        
        data = {
            "chat_id": self.chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        
        if inline_buttons:
            data["reply_markup"] = json.dumps(inline_buttons)
        
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
    
    def send_notice_with_media(self, notice: Dict, change_type: str, images: List[bytes], 
                                pdf_bytes: bytes = None) -> List[Dict]:
        """
        Send a complete notice notification:
        1. Single photo with inline buttons OR Media group + inline buttons in separate message
        2. PDF document (if provided)
        """
        import json
        results = []
        inline_buttons = self.build_inline_keyboard(notice)
        
        if len(images) == 1:
            # Single image -> use sendPhoto which supports reply_markup
            caption = self.build_notice_caption(notice, change_type) + self.get_forward_footer()
            if len(caption) > 1024:
                caption = caption[:1020] + "..."
            
            photo_result = self.send_photo(
                images[0], 
                caption=caption, 
                inline_buttons=json.dumps(inline_buttons)
            )
            if photo_result:
                results.append(photo_result)
        
        elif len(images) > 1:
            # Media group -> use sendMediaGroup (no reply_markup support)
            media_result = self.send_media_group(images, notice, change_type)
            if media_result:
                results.extend(media_result)
                
            # Send separate message with inline buttons replying to the media group or just right after
            btn_msg_text = f"🔗 Links for <b>{notice.get('title', 'Notice')}</b>:"
            btn_result = self.send_message(btn_msg_text, inline_buttons)
            if btn_result:
                results.append(btn_result)
                
        else:
            # No images, send text only
            caption = self.build_notice_caption(notice, change_type) + self.get_forward_footer()
            if len(caption) > 1024:
                caption = caption[:1020] + "..."
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
    print(utils.build_notice_caption(test_notice, "NEW"))
    print("\nRemoved notification test:")
    print(utils.format_removed_caption(test_notice))
