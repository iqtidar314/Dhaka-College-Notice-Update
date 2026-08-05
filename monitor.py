
"""
Dhaka College Notice Monitor v2
Orchestrates all modules for the complete rebrand
"""

import os
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


class NoticeMonitor:
    def __init__(self):
        self.scraper = NoticeScraper()
        self.cache_manager = CacheManager()
        self.change_detector = ChangeDetector()
        self.content_processor = ContentProcessor()
        self.telegram = TelegramUtils()
        self.dashboard = DashboardManager(self.telegram)
        
        self.error_file = 'error_state.json'
        self.log_file = 'log.json'
    
    def load_error_state(self) -> Dict:
        """Load error state from file"""
        try:
            if os.path.exists(self.error_file):
                with open(self.error_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading error state: {e}")
        return {"last_error": {"type": None, "active": False}}
    
    def save_error_state(self, data: Dict):
        """Save error state to file"""
        try:
            with open(self.error_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Error saving error state: {e}")
    
    def send_error_notification(self, error_type: str, details: Dict = None):
        """Send error notification with 3-strike rule"""
        error_data = self.load_error_state()
        last_error = error_data.get("last_error", {})
        previous_error = error_data.get("previous_error", {})
        
        current_error_type = last_error.get("type")
        current_count = last_error.get("count", 0)
        current_sent = last_error.get("sent", False)
        current_active = last_error.get("active", False)
        
        # Same error type
        if current_error_type == error_type and current_active:
            error_count = current_count + 1
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent": current_sent
            }
        # Different error type
        elif current_error_type != error_type:
            if current_active and current_sent and current_count >= 3:
                error_data["previous_error"] = {
                    "type": current_error_type,
                    "count": current_count,
                    "sent": True,
                    "active": True
                }
            error_count = 1
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent": False
            }
        else:
            error_count = 1
            error_data["last_error"] = {
                "type": error_type,
                "active": True,
                "count": error_count,
                "detail_error": str(details.get('error', '')) if details else "",
                "sent": False
            }
        
        # Send message after 3 strikes
        if error_count >= 3 and not error_data["last_error"].get("sent", False):
            msg = f"⚠️ <b>{error_type.upper()} Error!</b>\n"
            msg += f"Occurred {error_count} times consecutively.\n"
            if details and details.get('error'):
                msg += f"Details: {details['error'][:200]}"
            
            if self.telegram.send_message(msg):
                error_data["last_error"]["sent"] = True
        
        self.save_error_state(error_data)
    
    def send_resolved_notification(self):
        """Send resolved notification if error was active"""
        error_data = self.load_error_state()
        last_error = error_data.get("last_error", {})
        
        if last_error.get("active", False) and last_error.get("sent", False):
            error_type = last_error.get("type", "Unknown")
            count = last_error.get("count", 0)
            
            msg = f"✅ <b>Error Resolved!</b>\n"
            msg += f"The {error_type} error occurred {count} time(s).\n"
            msg += "Monitor is working again."
            
            self.telegram.send_message(msg)
        
        # Reset error state
        error_data["last_error"] = {"type": None, "active": False, "count": 0, "sent": False, "detail_error": ""}
        error_data["previous_error"] = {"type": None, "count": 0, "sent": False, "active": False}
        self.save_error_state(error_data)
    
    def log_run(self, stats: Dict):
        """Log run to structured JSON file"""
        log_entry = {
            "timestamp": datetime.now(timezone(timedelta(hours=6))).isoformat(),
            "stats": stats
        }
        
        logs = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        # Keep last 100 runs
        if len(logs) > 100:
            logs = logs[-100:]
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def process_and_send_notice(self, notice: Dict, change_type: ChangeType) -> bool:
        """Process a notice and send to Telegram"""
        try:
            if hasattr(self, '_dispatched_this_run') and notice['id'] in self._dispatched_this_run:
                print(f"⏭️ Skipping duplicate dispatch for {notice['id']}")
                return False
                
            if not hasattr(self, '_dispatched_this_run'):
                self._dispatched_this_run = set()
                
            self._dispatched_this_run.add(notice['id'])
            
            download_url = notice.get('download_url', '')
            
            # Skip notices without PDF URLs - send text only notification
            if not download_url:
                print(f"⚠️ No PDF URL for: {notice.get('title', 'Unknown')[:50]}")
                results = self.telegram.send_notice_with_media(notice, change_type.value, [], None)
                return len(results) > 0
            
            # Download and process media
            print(f"📥 Downloading PDF: {download_url}")
            images, pdf_hash, file_type = self.content_processor.process_notice_media(notice)
            
            if not images:
                print(f"⚠️ No images rendered for: {notice.get('title', 'Unknown')[:50]}")
                results = self.telegram.send_notice_with_media(notice, change_type.value, [], None)
                return len(results) > 0
            
            # Get PDF bytes
            pdf_bytes, _ = self.content_processor.download_file(download_url)
            
            # Convert images to bytes
            image_bytes = self.content_processor.images_to_bytes(images)
            
            print(f"📤 Sending {len(image_bytes)} images + PDF document")
            
            # Send to Telegram
            if change_type == ChangeType.REMOVED_FROM_PAGE_1:
                return self.telegram.send_removed_notification(notice) is not None
            else:
                results = self.telegram.send_notice_with_media(notice, change_type.value, image_bytes, pdf_bytes)
                return len(results) > 0
        
        except Exception as e:
            print(f"❌ Error processing notice {notice.get('id')}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run(self) -> Dict:
        """Main execution flow"""
        self._dispatched_this_run = set()
        
        print("="*60)
        print(f"🚀 The DC Archive — Notice Monitor v2")
        print(f"⏰ {datetime.now(timezone(timedelta(hours=6))).strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        stats = {
            "status": "started",
            "pages_scraped": 0,
            "total_notices": 0,
            "new_count": 0,
            "edited_count": 0,
            "pdf_replaced_count": 0,
            "removed_count": 0,
            "errors": []
        }
        
        # Validate Telegram credentials
        if not os.getenv('TELEGRAM_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
            print("❌ TELEGRAM_TOKEN and TELEGRAM_CHAT_ID must be set")
            stats["status"] = "error"
            stats["errors"].append("Missing Telegram credentials")
            return stats
        
        # Load cache
        cache_data = self.cache_manager.load_cache()
        
        # Scrape all pages
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
        
        # Get page 1 notices for removal detection
        page_1_notices = page_notices.get(1, [])
        page_1_ids = {n['id'] for n in page_1_notices}
        
        # Process media and get PDF hashes
        pdf_hashes = {}
        for notice in all_notices:
            if notice.get('download_url'):
                file_type = self.content_processor.detect_file_type(notice['download_url'])
                if file_type == 'pdf':
                    _, pdf_hash = self.content_processor.download_file(notice['download_url'])
                    if pdf_hash:
                        pdf_hashes[notice['id']] = pdf_hash
        
        # Detect changes
        changes = self.change_detector.detect_changes(
            all_notices, page_1_notices, cache_data, pdf_hashes
        )
        
        # Send resolved notification if applicable
        self.send_resolved_notification()
        
        # Process each change
        new_count = 0
        page_1_ids_set = set(n['id'] for n in page_1_notices)
        
        for change in changes:
            # For NEW notices, optionally limit them
            if change.change_type == ChangeType.NEW:
                # Only process if notice was on page 1
                if change.notice_id not in page_1_ids_set:
                    print(f"⏭️ Skipping NEW notice not from page 1: {change.notice_data.get('title', 'Unknown')[:30]}")
                    continue
                
                # Limit to 10 new notices per run
                if new_count >= 10:
                    print(f"⏭️ Reached limit of 10 new notices per run")
                    continue
            
            try:
                print(f"📤 Processing change [{change.change_type.name}]: {change.notice_data.get('title', 'Unknown')[:40]}")
                success = self.process_and_send_notice(change.notice_data, change.change_type)
                
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
                print(f"❌ Error sending change notification: {e}")
                stats["errors"].append(str(e))
        
        # Update cache with current notices
        for notice in all_notices:
            was_on_page_1 = notice['id'] in page_1_ids
            cache_data = self.cache_manager.update_notice(
                notice, cache_data,
                pdf_hash=pdf_hashes.get(notice['id']),
                file_type=self.content_processor.detect_file_type(notice.get('download_url', '')),
                was_on_page_1=was_on_page_1
            )
        
        # Update page 1 tracking
        cache_data = self.cache_manager.set_previous_page_1_ids(list(page_1_ids), cache_data)
        
        # Increment uptime streak
        cache_data = self.cache_manager.increment_uptime_streak(cache_data)
        
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
        print("\n" + "="*60)
        print("📊 RUN SUMMARY")
        print("="*60)
        print(f"✅ Status: {stats['status']}")
        print(f"📄 Pages scraped: {stats['pages_scraped']}")
        print(f"📋 Total notices: {stats['total_notices']}")
        print(f"🆕 New: {stats['new_count']}")
        print(f"✏️ Edited: {stats['edited_count']}")
        print(f"📄 PDF replaced: {stats['pdf_replaced_count']}")
        print(f"🗑️ Removed from page 1: {stats['removed_count']}")
        if stats['errors']:
            print(f"⚠️ Errors: {len(stats['errors'])}")
        print("="*60)
        
        return stats


if __name__ == "__main__":
    monitor = NoticeMonitor()
    stats = monitor.run()
    
    # Write to GitHub step summary if available
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
