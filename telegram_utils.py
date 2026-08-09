"""
Telegram Utilities for Dhaka College Notice Monitor
Handles media groups, documents, and dashboard editing.
"""

import os
import re
import json
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta


# ─── Constants ────────────────────────────────────────────────────────────────

_CHANGE_LABEL = {
    "NEW":                 "New Notice",
    "EDITED":              "Updated",
    "PDF_REPLACED":        "PDF Replaced",
    "REMOVED_FROM_PAGE_1": "Moved Off Front Page",
}

_WEBSITE  = "https://thedcarchive.pages.dev/"
_FACEBOOK = "https://www.facebook.com/thedcarchive"
_CHANNEL  = "https://t.me/thedcarchive_notice"
_GITHUB   = "https://github.com/iqtidar314/Dhaka-College-Notice-Update"
_DISCUSSION = "https://t.me/DcNoticeChat"

# Characters allowed in a PDF filename:
# Bangla (U+0980–U+09FF), ASCII letters/digits, space, hyphen, underscore, dot
_SAFE_FILENAME_RE = re.compile(
    r"[^\u0980-\u09FF\w \-_\.]",
    re.UNICODE,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def sanitise_filename(title: str, max_len: int = 80) -> str:
    """
    Strip characters that would cause filesystem or Telegram API issues,
    then truncate to max_len. Returns 'notice_unnamed' if nothing remains.
    """
    cleaned = _SAFE_FILENAME_RE.sub("", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_.")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(" -_.")
    return cleaned or "notice_unnamed"


def _link_footer() -> str:
    """Multi-line hyperlink footer — one link per line."""
    parts = []
    parts.append(f"fb page: <a href='{_FACEBOOK}'>The DC Archive</a>\n")
    parts.append(f"main channel: <a href='{_CHANNEL}'>@thedcarchive_notice</a>\n")
    parts.append(f"Discussion group: <a href='{_DISCUSSION}'>@DcNoticeChat</a>\n")
    parts.append(f"Result web: <a href='{_WEBSITE}'>The DC Archive</a>")
    return "".join(parts)




# ─── TelegramUtils ────────────────────────────────────────────────────────────

class TelegramUtils:
    def __init__(self):
        self.token   = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.api_base = f"https://api.telegram.org/bot{self.token}"

    # ── Core request ──────────────────────────────────────────────────────────

    def _make_request(self, method: str, data: Dict, files: Dict = None) -> Optional[Dict]:
        """Make a request to the Telegram Bot API."""
        try:
            url = f"{self.api_base}/{method}"
            response = requests.post(url, data=data, files=files, timeout=60)
            result = response.json()
            if result.get('ok'):
                return result.get('result')
            print(f"Telegram API error ({method}): {result.get('description')}")
            print(f"  Response: {result}")
            return None
        except Exception as e:
            print(f"Error calling {method}: {e}")
            try:
                print(f"  Response text: {response.text}")
            except Exception:
                pass
            return None

    # ── Caption helpers ───────────────────────────────────────────────────────

    _CAPTION_LIMIT = 1024

    def _safe_title(self, title: str, overhead: int = 0) -> str:
        """
        Clamp title to fit within Telegram's caption limit.
        overhead = number of chars taken by fixed parts of the caption (footer,
        tags, part indicators, etc.) so the title never pushes the total over
        _CAPTION_LIMIT.
        The title contains no HTML so slicing it is always safe.
        """
        budget = self._CAPTION_LIMIT - overhead
        if len(title) > budget:
            title = title[:max(budget, 0)].rstrip()
        return title

    # ── Caption builders ──────────────────────────────────────────────────────

    def build_notice_caption(self, notice: Dict, change_type: str) -> str:
        """Single-image or text-only notice caption."""
        title        = notice.get('title', 'Unknown')
        footer       = _link_footer()
        # overhead: <blockquote></blockquote>\n\n + footer
        overhead     = len("<blockquote></blockquote>\n\n") + len(footer)
        title        = self._safe_title(title, overhead)

        caption = (
            f"<blockquote>{title}</blockquote>\n\n"
        )
        caption += footer
        return caption

    def build_album_caption(self, notice: Dict, change_type: str,
                            part: int, total_parts: int) -> str:
        """
        Caption for a media-group post.
        First and last posts carry the full header and footer;
        middle posts carry only the part indicator.
        """
        if total_parts == 1:
            return self.build_notice_caption(notice, change_type)

        label        = _CHANGE_LABEL.get(change_type, "Notice")
        title        = notice.get('title', 'Unknown')
        download_url = notice.get('download_url', '')

        if part == 1:
            footer   = _link_footer()
            # overhead: <code>Part X of Y</code>\n + <blockquote></blockquote>\n\n + footer
            overhead = len(f"<code>Part {part} of {total_parts}</code>\n") \
                     + len("<blockquote></blockquote>\n\n") \
                     + len(footer)
            safe_t   = self._safe_title(title, overhead)
            return (
                f"<code>Part {part} of {total_parts}</code>\n"
                f"<blockquote>{safe_t}</blockquote>\n\n"
                f"{footer}"
            )
        elif part == total_parts:
            return (
                f"<code>Part {part} of {total_parts} — end</code>\n"
                f"<blockquote>{title}</blockquote>\n"
            )
        else:
            return f"<code>Part {part} of {total_parts}</code>"

    def format_removed_caption(self, notice: Dict) -> str:
        """Short notification that a notice has been removed."""
        title = notice.get('title', 'Unknown')
        date  = notice.get('date', 'Unknown')
        return (
            f"<b>Removed</b>\n"
            f"<b>{title}</b>\n"
            f"<code>{date}</code>"
        )

    def format_deleted_label(self, original_caption: str) -> str:
        """
        Prepend a short removal marker to an existing caption.
        The original content (text, links) is preserved below the tag.
        """
        return f"<b>[Removed]</b>\n{original_caption}"

    # ── Send methods ──────────────────────────────────────────────────────────

    def send_photo(self, photo_bytes: bytes, caption: str,
                   disable_notification: bool = False) -> Optional[Dict]:
        """Send a single photo with caption (no inline keyboard)."""
        data = {
            "chat_id": self.chat_id,
            "caption": caption,   # already safe-truncated by build_*_caption
            "parse_mode": "HTML",
            "disable_notification": disable_notification,
        }
        files  = {"photo": ("notice.png", photo_bytes, "image/png")}
        result = self._make_request("sendPhoto", data, files)
        if result:
            print(f"Photo sent: message_id={result.get('message_id')}")
        return result

    def send_media_group(self, images: List[bytes], notice: Dict, change_type: str,
                         disable_notification: bool = False) -> Tuple[Optional[List[Dict]], bool]:
        """
        Send images as media group albums (max 10 per group).

        Returns:
            (results_list, all_sent)
            all_sent is True only when every group was delivered successfully.
        """
        if not images:
            return None, False

        results     = []
        total_parts = (len(images) + 9) // 10
        all_sent    = True

        for i in range(0, len(images), 10):
            group  = images[i:i + 10]
            part   = (i // 10) + 1
            caption = self.build_album_caption(notice, change_type, part, total_parts)

            media = []
            files = {}
            for idx, img_bytes in enumerate(group):
                media.append({
                    "type":       "photo",
                    "media":      f"attach://photo{idx}",
                    "caption":    caption[:1024] if idx == 0 else "",
                    "parse_mode": "HTML",
                })
                files[f"photo{idx}"] = (f"page_{i + idx}.png", img_bytes, "image/png")

            data = {
                "chat_id":              self.chat_id,
                "media":                json.dumps(media),
                "disable_notification": disable_notification,
            }

            result = self._make_request("sendMediaGroup", data, files)
            if result:
                print(f"Media group sent: {len(group)} images (Part {part}/{total_parts})")
                results.extend(result)
            else:
                print(f"Media group FAILED: Part {part}/{total_parts}")
                all_sent = False

        return (results if results else None), all_sent

    def send_document(self, file_bytes: bytes, filename: str,
                      caption: str = None,
                      disable_notification: bool = True) -> Optional[Dict]:
        """Send a PDF document."""
        data = {
            "chat_id":                    self.chat_id,
            "caption":                    caption[:1024] if caption else None,
            "parse_mode":                 "HTML",
            "disable_notification":       disable_notification,
            "disable_content_type_detection": True,
        }
        files  = {"document": (filename, file_bytes, "application/pdf")}
        result = self._make_request("sendDocument", data, files)
        if result:
            print(f"Document sent: {filename}")
        return result

    def send_message(self, text: str,
                     disable_notification: bool = False) -> Optional[Dict]:
        """Send a plain text message (HTML, no keyboard)."""
        data = {
            "chat_id":                self.chat_id,
            "text":                   text,
            "parse_mode":             "HTML",
            "disable_notification":   disable_notification,
            "disable_web_page_preview": True,
        }
        result = self._make_request("sendMessage", data)
        if result:
            print(f"Message sent: message_id={result.get('message_id')}")
        return result

    def edit_message(self, message_id: int, text: str) -> Optional[Dict]:
        """Edit the text of an existing text message."""
        data = {
            "chat_id":                  self.chat_id,
            "message_id":               message_id,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_web_page_preview": True,
        }
        result = self._make_request("editMessageText", data)
        if result:
            print(f"Message edited: {message_id}")
        return result

    def edit_message_caption(self, message_id: int, caption: str) -> Optional[Dict]:
        """Edit the caption of an existing photo/document message (preserves media)."""
        data = {
            "chat_id":     self.chat_id,
            "message_id":  message_id,
            "caption":     caption[:1024],
            "parse_mode":  "HTML",
        }
        result = self._make_request("editMessageCaption", data)
        if result:
            print(f"Caption edited: {message_id}")
        return result

    def reply_to_message(self, reply_to_message_id: int, text: str,
                         disable_notification: bool = False) -> Optional[Dict]:
        """Send a message as a reply to another message."""
        data = {
            "chat_id":                  self.chat_id,
            "reply_to_message_id":      reply_to_message_id,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_notification":     disable_notification,
            "disable_web_page_preview": True,
        }
        result = self._make_request("sendMessage", data)
        if result:
            print(f"Reply sent to message {reply_to_message_id}: message_id={result.get('message_id')}")
        return result

    def pin_message(self, message_id: int,
                    disable_notification: bool = True) -> Optional[Dict]:
        """Pin a message in the chat."""
        data = {
            "chat_id":            self.chat_id,
            "message_id":         message_id,
            "disable_notification": disable_notification,
        }
        result = self._make_request("pinChatMessage", data)
        if result:
            print(f"Message pinned: {message_id}")
        return result

    # ── High-level notice sender ───────────────────────────────────────────────

    def send_notice_with_media(self, notice: Dict, change_type: str,
                               images: List[bytes],
                               pdf_bytes: bytes = None) -> Tuple[List[Dict], bool]:
        """
        Send a complete notice notification.

        PDF delivery policy:
          - 0 images              → always send PDF (if available)
          - 1+ images, all sent   → skip PDF
          - 1+ images, any failed → send PDF as fallback

        Returns:
            (results_list, images_all_sent)
        """
        results         = []
        images_all_sent = False

        if len(images) == 1:
            caption     = self.build_notice_caption(notice, change_type)
            photo_result = self.send_photo(images[0], caption=caption)
            if photo_result:
                results.append(photo_result)
                images_all_sent = True

        elif len(images) > 1:
            media_results, images_all_sent = self.send_media_group(
                images, notice, change_type
            )
            if media_results:
                results.extend(media_results)

        else:
            # No images — send text message
            caption     = self.build_notice_caption(notice, change_type)
            msg_result  = self.send_message(caption)
            if msg_result:
                results.append(msg_result)
            # Treat as "not all sent" so PDF fallback applies
            images_all_sent = False

        # Send PDF only if image delivery was not fully successful
        pdf_sent = False
        should_send_pdf = pdf_bytes and not images_all_sent
        if should_send_pdf:
            title     = notice.get('title', '')
            safe_name = sanitise_filename(title) + ".pdf"
            doc_result = self.send_document(pdf_bytes, safe_name)
            if doc_result:
                results.append(doc_result)
                pdf_sent = True

        # Last resort: if images disrupted AND PDF also failed
        if not images_all_sent and not pdf_sent:
            title        = notice.get('title', '')
            download_url = notice.get('download_url', '')
            footer       = _link_footer()

            if download_url:
                # Has a URL — show download link + footer
                overhead     = len("<blockquote></blockquote>\n\n") \
                             + len("<a href=''>Download PDF</a>\n\n") \
                             + len(footer)
                safe_t       = self._safe_title(title, overhead)
                fallback_msg = (
                    f"<blockquote>{safe_t}</blockquote>\n\n"
                    f"<a href='{download_url}'>Download PDF</a>\n\n"
                    f"{footer}"
                )
                fallback_result = self.send_message(fallback_msg)
                if fallback_result:
                    print(f"\u26a0\ufe0f Fallback URL sent for: {title}")
                    results.append(fallback_result)
            else:
                # No URL either — send caption + footer so notice is at least acknowledged
                overhead     = len("<blockquote></blockquote>\n\n") + len(footer)
                safe_t       = self._safe_title(title, overhead)
                fallback_msg = (
                    f"<blockquote>{safe_t}</blockquote>\n\n"
                    f"{footer}"
                )
                fallback_result = self.send_message(fallback_msg)
                if fallback_result:
                    print(f"\u26a0\ufe0f No-media fallback sent for: {title}")
                    results.append(fallback_result)

        return results, images_all_sent

    def send_removed_notification(self, notice: Dict) -> Optional[Dict]:
        """Send a removed-from-front-page notification."""
        caption = self.format_removed_caption(notice)
        return self.send_message(caption)


# ─── Manual test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    utils = TelegramUtils()

    test_notice = {
        'title':        'ঢাকা কলেজ ভর্তি বিজ্ঞপ্তি ২০২৬',
        'date':         '2026-08-06',
        'serial':       '123',
        'download_url': 'https://example.com/notice.pdf',
    }

    print("Single caption:")
    print(utils.build_notice_caption(test_notice, "NEW"))
    print("\nRemoved caption:")
    print(utils.format_removed_caption(test_notice))
    print("\nFilename sanitise:")
    print(sanitise_filename("ঢাকা কলেজ ভর্তি বিজ্ঞপ্তি (২০২৬) [Important!] #1"))
