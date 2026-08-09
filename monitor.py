
"""
Dhaka College Notice Monitor v2
Orchestrates all modules for the complete rebrand
"""

import os
import re
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

# Import modules
from scraper import NoticeScraper
from cache_manager import CacheManager
from change_detector import ChangeDetector, ChangeType
from content_processor import ContentProcessor
from telegram_utils import TelegramUtils
from dashboard_manager import DashboardManager

# ─── NOC filter ───────────────────────────────────────────────────────────────
# Whole-word match for "noc" (case-insensitive) or Bangla "এনওসি"
_NOC_RE = re.compile(r'\bnoc\b', re.IGNORECASE)


def _is_noc_notice(notice: Dict) -> bool:
    title = notice.get('title', '')
    return bool(_NOC_RE.search(title)) or 'এনওসি' in title


class NoticeMonitor:
    def __init__(self):
        self.scraper           = NoticeScraper()
        self.cache_manager     = CacheManager()
        self.change_detector   = ChangeDetector()
        self.content_processor = ContentProcessor()
        self.telegram          = TelegramUtils()
        self.dashboard         = DashboardManager(self.telegram)

        self.error_file = 'error_state.json'
        self.log_file   = 'log.json'

    # ── Error state ───────────────────────────────────────────────────────────

    def load_error_state(self) -> Dict:
        """Load error state from file."""
        try:
            if os.path.exists(self.error_file):
                with open(self.error_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading error state: {e}")
        return {"last_error": {"type": None, "active": False}}

    def save_error_state(self, data: Dict):
        """Save error state to file."""
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving error state: {e}")

    def send_error_notification(self, error_type: str, details: Dict = None):
        """Send error notification with 3-strike rule."""
        error_data    = self.load_error_state()
        last_error    = error_data.get("last_error", {})
        current_type  = last_error.get("type")
        current_count = last_error.get("count", 0)
        current_sent  = last_error.get("sent", False)
        current_active = last_error.get("active", False)

        if current_type == error_type and current_active:
            error_count = current_count + 1
            error_data["last_error"] = {
                "type":         error_type,
                "active":       True,
                "count":        error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent":         current_sent,
            }
        elif current_type != error_type:
            if current_active and current_sent and current_count >= 3:
                error_data["previous_error"] = {
                    "type":   current_type,
                    "count":  current_count,
                    "sent":   True,
                    "active": True,
                }
            error_count = 1
            error_data["last_error"] = {
                "type":         error_type,
                "active":       True,
                "count":        error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent":         False,
            }
        else:
            error_count = 1
            error_data["last_error"] = {
                "type":         error_type,
                "active":       True,
                "count":        error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent":         False,
            }

        if error_count >= 3 and not error_data["last_error"].get("sent", False):
            msg  = f"<b>{error_type.upper()} Error</b>\n"
            msg += f"Occurred {error_count} times consecutively.\n"
            if details and details.get('error'):
                msg += f"Details: {str(details['error'])[:200]}"
            if self.telegram.send_message(msg):
                error_data["last_error"]["sent"] = True

        self.save_error_state(error_data)

    def send_resolved_notification(self):
        """Send resolved notification if an error was previously active."""
        error_data = self.load_error_state()
        last_error = error_data.get("last_error", {})

        if last_error.get("active", False) and last_error.get("sent", False):
            error_type = last_error.get("type", "Unknown")
            count      = last_error.get("count", 0)
            msg = (
                f"<b>Error Resolved</b>\n"
                f"The {error_type} error occurred {count} time(s). "
                f"Monitor is working again."
            )
            self.telegram.send_message(msg)

        error_data["last_error"]    = {"type": None, "active": False, "count": 0, "sent": False, "detail_error": ""}
        error_data["previous_error"] = {"type": None, "count": 0, "sent": False, "active": False}
        self.save_error_state(error_data)

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_run(self, stats: Dict):
        """Append run statistics to log.json (keeps last 100 entries)."""
        log_entry = {
            "timestamp": datetime.now(timezone(timedelta(hours=6))).isoformat(),
            "stats":     stats,
        }

        logs = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append(log_entry)
        if len(logs) > 100:
            logs = logs[-100:]

        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    # ── Notice processing ──────────────────────────────────────────────────────

    def process_and_send_notice(self, notice: Dict, change_type: ChangeType,
                                cache_data: Dict) -> bool:
        """
        Process a notice: render images, send to Telegram, track message IDs.
        Returns True on successful dispatch.
        """
        try:
            # Dedup guard within a single run
            if not hasattr(self, '_dispatched_this_run'):
                self._dispatched_this_run = set()
            if notice['id'] in self._dispatched_this_run:
                print(f"Skipping duplicate dispatch for {notice['id']}")
                return False
            self._dispatched_this_run.add(notice['id'])

            download_url = notice.get('download_url', '')

            # ── No PDF URL → text-only ────────────────────────────────────────
            if not download_url:
                print(f"No PDF URL for: {notice.get('title', 'Unknown')[:50]}")
                results, _ = self.telegram.send_notice_with_media(
                    notice, change_type.value, [], None
                )
                self._record_message_ids(notice['id'], results, cache_data)
                return len(results) > 0

            # ── REMOVED_FROM_PAGE_1 — no render/download needed ──────────────
            if change_type == ChangeType.REMOVED_FROM_PAGE_1:
                result = self.telegram.send_removed_notification(notice)
                if result:
                    msg_id = result.get('message_id')
                    cache_data = self.cache_manager.set_removed_message_id(
                        notice['id'], msg_id, cache_data
                    )
                    self._mark_notice_deleted(notice, cache_data)
                return result is not None

            # ── Download & render ─────────────────────────────────────────────
            print(f"Downloading PDF: {download_url}")
            images, pdf_hash, file_type = self.content_processor.process_notice_media(notice)

            # Always get raw PDF bytes (needed for fallback)
            pdf_bytes, _ = self.content_processor.download_file(download_url)

            image_bytes = self.content_processor.images_to_bytes(images) if images else []

            print(f"Sending {len(image_bytes)} images (PDF fallback available: {bool(pdf_bytes)})")

            # ── Normal send ───────────────────────────────────────────────────
            results, _ = self.telegram.send_notice_with_media(
                notice, change_type.value, image_bytes, pdf_bytes
            )
            self._record_message_ids(notice['id'], results, cache_data)
            return len(results) > 0


        except Exception as e:
            print(f"Error processing notice {notice.get('id')}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _record_message_ids(self, notice_id: str, results: List[Dict], cache_data: Dict):
        """Store returned Telegram message IDs in the notice cache entry."""
        ids = [r.get('message_id') for r in results if r and r.get('message_id')]
        if ids:
            self.cache_manager.append_telegram_message_ids(notice_id, ids, cache_data)

    def _mark_notice_deleted(self, notice: Dict, cache_data: Dict):
        """
        Prepend a [Removed] tag to all previously sent Telegram messages for this
        notice.  If no message history exists, does nothing.

        For photo/media posts the caption is edited (image preserved).
        For plain text posts the message text is edited.
        Both fall back silently if the API call fails.
        """
        notice_record = cache_data.get('notices', {}).get(notice['id'], {})
        prev_ids      = notice_record.get('telegram_message_ids', [])

        if not prev_ids:
            print(f"No message history for notice {notice['id'][:12]}… — skipping deletion tag")
            return

        for msg_id in prev_ids:
            # Try editMessageCaption first (works on photo/video/document messages)
            result = self.telegram.edit_message_caption(msg_id, "<b>[Removed]</b>")
            if result is None:
                # Fall back to editMessageText (works on plain text messages)
                self.telegram.edit_message(msg_id, "<b>[Removed]</b>")

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(self) -> Dict:
        """Main execution flow."""
        self._dispatched_this_run = set()

        print("=" * 60)
        print(f"The DC Archive — Notice Monitor v2")
        print(f"{datetime.now(timezone(timedelta(hours=6))).strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        stats = {
            "status":              "started",
            "pages_scraped":       0,
            "total_notices":       0,
            "new_count":           0,
            "edited_count":        0,
            "pdf_replaced_count":  0,
            "removed_count":       0,
            "noc_skipped":         0,
            "errors":              [],
        }

        # Validate Telegram credentials
        if not os.getenv('TELEGRAM_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            print("TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
            stats["status"] = "error"
            stats["errors"].append("Missing Telegram credentials")
            return stats

        # Load cache
        cache_data = self.cache_manager.load_cache()

        # Scrape
        try:
            all_notices, page_notices = self.scraper.scrape_all_pages()
            stats["pages_scraped"] = len(page_notices)
            stats["total_notices"] = len(all_notices)

            if not all_notices:
                self.send_error_notification("structure", {"error": "No notices found"})
                stats["status"] = "error"
                stats["errors"].append("No notices found")
                return stats

        except Exception as e:
            self.send_error_notification("network", {"error": str(e)})
            stats["status"] = "error"
            stats["errors"].append(str(e))
            return stats

        # Page 1 IDs
        page_1_notices = page_notices.get(1, [])
        page_1_ids     = {n['id'] for n in page_1_notices}

        # Compute PDF hashes (skip NOC notices to avoid unnecessary downloads)
        pdf_hashes = {}
        file_types = {}
        cached_notices = cache_data.get('notices', {})
        
        for notice in all_notices:
            nid = notice['id']
            if _is_noc_notice(notice):
                continue
            
            download_url = notice.get('download_url')
            if not download_url:
                continue
                
            cached_notice = cached_notices.get(nid, {})
            # Reuse cached values to avoid expensive network calls (prevents 15m timeout on server failure)
            if cached_notice and cached_notice.get('file_type') and cached_notice.get('file_type') != 'unknown':
                file_types[nid] = cached_notice['file_type']
                if cached_notice.get('pdf_hash'):
                    pdf_hashes[nid] = cached_notice['pdf_hash']
                continue
            
            file_type = self.content_processor.detect_file_type(download_url)
            file_types[nid] = file_type
            
            if file_type == 'pdf':
                _, pdf_hash = self.content_processor.download_file(download_url)
                if pdf_hash:
                    pdf_hashes[nid] = pdf_hash

        # Detect changes
        changes = self.change_detector.detect_changes(
            all_notices, page_1_notices, cache_data, pdf_hashes
        )

        # Send resolved notification if applicable
        self.send_resolved_notification()

        # Process each change
        new_count        = 0
        page_1_ids_set   = set(n['id'] for n in page_1_notices)

        for change in changes:
            notice = change.notice_data

            # ── NOC filter ─────────────────────────────────────────────────────
            if _is_noc_notice(notice):
                print(f"[NOC BLOCKED] {notice.get('title', 'Unknown')[:60]}")
                stats["noc_skipped"] += 1
                continue

            # Only process NEW notices that were on page 1
            if change.change_type == ChangeType.NEW:
                if change.notice_id not in page_1_ids_set:
                    print(f"Skipping NEW notice not from page 1: {notice.get('title', 'Unknown')[:30]}")
                    continue
                if new_count >= 10:
                    print("Reached limit of 10 new notices per run")
                    continue

            try:
                print(f"Processing [{change.change_type.name}]: {notice.get('title', 'Unknown')[:40]}")
                success = self.process_and_send_notice(notice, change.change_type, cache_data)

                if success:
                    if change.change_type == ChangeType.NEW:
                        stats["new_count"] += 1
                        new_count += 1
                    elif change.change_type == ChangeType.EDITED:
                        stats["edited_count"] += 1
                    elif change.change_type == ChangeType.PDF_REPLACED:
                        stats["pdf_replaced_count"] += 1
                    elif change.change_type == ChangeType.REMOVED_FROM_PAGE_1:
                        stats["removed_count"] += 1

            except Exception as e:
                print(f"Error sending change notification: {e}")
                stats["errors"].append(str(e))

        # Update cache
        for notice in all_notices:
            nid = notice['id']
            was_on_page_1 = nid in page_1_ids
            ftype = file_types.get(nid, 'unknown') if not _is_noc_notice(notice) else 'unknown'
            
            cache_data = self.cache_manager.update_notice(
                notice, cache_data,
                pdf_hash=pdf_hashes.get(nid),
                file_type=ftype,
                was_on_page_1=was_on_page_1,
            )

        cache_data = self.cache_manager.set_previous_page_1_ids(list(page_1_ids), cache_data)
        cache_data = self.cache_manager.increment_uptime_streak(cache_data)
        cache_data = self.cache_manager.record_run(cache_data)
        if stats["new_count"] > 0:
            cache_data = self.cache_manager.increment_total_new_notices(stats["new_count"], cache_data)

        # Update dashboard
        dashboard_stats = self.dashboard.calculate_stats(
            cache_data, changes, page_1_notices, stats["pages_scraped"],
            self.load_error_state()
        )
        message_id = self.dashboard.create_or_update_dashboard(cache_data, dashboard_stats)
        if message_id:
            cache_data = self.cache_manager.set_dashboard_message_id(message_id, cache_data)

        # Save cache
        self.cache_manager.save_cache(cache_data)

        # Log run
        stats["status"] = "success"
        self.log_run(stats)

        # Print summary
        print("\n" + "=" * 60)
        print("RUN SUMMARY")
        print("=" * 60)
        print(f"Status:          {stats['status']}")
        print(f"Pages scraped:   {stats['pages_scraped']}")
        print(f"Total notices:   {stats['total_notices']}")
        print(f"New:             {stats['new_count']}")
        print(f"Edited:          {stats['edited_count']}")
        print(f"PDF replaced:    {stats['pdf_replaced_count']}")
        print(f"Removed pg1:     {stats['removed_count']}")
        print(f"NOC blocked:     {stats['noc_skipped']}")
        if stats['errors']:
            print(f"Errors:          {len(stats['errors'])}")
        print("=" * 60)

        return stats


if __name__ == "__main__":
    monitor = NoticeMonitor()
    stats = monitor.run()

    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(f"## Run Summary\n")
            f.write(f"- Status: {stats['status']}\n")
            f.write(f"- Pages scraped: {stats['pages_scraped']}\n")
            f.write(f"- Total notices: {stats['total_notices']}\n")
            f.write(f"- New: {stats['new_count']}\n")
            f.write(f"- Edited: {stats['edited_count']}\n")
            f.write(f"- Removed: {stats['removed_count']}\n")
            f.write(f"- NOC blocked: {stats['noc_skipped']}\n")
