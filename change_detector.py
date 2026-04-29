"""
Change Detector for Dhaka College Notice Monitor
Detects NEW, EDITED, PDF_REPLACED, and REMOVED_FROM_PAGE_1 changes
"""

from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    NEW = "new"
    EDITED = "edited"
    PDF_REPLACED = "pdf_replaced"
    REMOVED_FROM_PAGE_1 = "removed_from_page_1"


@dataclass
class ChangeEvent:
    """Represents a detected change"""
    change_type: ChangeType
    notice_id: str
    notice_data: Dict
    old_data: Optional[Dict] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone(timedelta(hours=6))).isoformat()


class ChangeDetector:
    def __init__(self):
        pass
    
    def detect_changes(
        self,
        current_notices: List[Dict],
        page_1_notices: List[Dict],
        cache_data: Dict,
        pdf_hashes: Dict[str, str] = None
    ) -> List[ChangeEvent]:
        """
        Detect all changes between current scrape and cache
        
        Args:
            current_notices: All notices from pages 1-3
            page_1_notices: Notices from page 1 only
            cache_data: Cached data from cache_manager
            pdf_hashes: Optional dict of notice_id -> pdf_hash
        
        Returns:
            List of ChangeEvent objects
        """
        changes = []
        pdf_hashes = pdf_hashes or {}
        
        # Get ID sets
        current_ids = {n['id'] for n in current_notices}
        current_page_1_ids = {n['id'] for n in page_1_notices}
        cached_ids = set(cache_data.get('notices', {}).keys())
        previous_page_1_ids = set(cache_data.get('previous_page_1_ids', []))
        
        # Create lookup dicts
        current_lookup = {n['id']: n for n in current_notices}
        cached_notices = cache_data.get('notices', {})
        
        # 1. Detect REMOVED_FROM_PAGE_1
        # Notice was on page 1 before, now not on any page
        for notice_id in previous_page_1_ids:
            if notice_id not in current_page_1_ids:
                if notice_id not in current_ids:
                    # Was on page 1, now completely gone
                    old_notice = cached_notices.get(notice_id, {})
                    changes.append(ChangeEvent(
                        change_type=ChangeType.REMOVED_FROM_PAGE_1,
                        notice_id=notice_id,
                        notice_data=old_notice,
                        old_data=old_notice
                    ))
                    print(f"🗑️ REMOVED_FROM_PAGE_1: {old_notice.get('title', 'Unknown')[:50]}")
        
        # 2. Detect NEW notices
        for notice_id in current_ids - cached_ids:
            notice = current_lookup[notice_id]
            changes.append(ChangeEvent(
                change_type=ChangeType.NEW,
                notice_id=notice_id,
                notice_data=notice
            ))
            print(f"🆕 NEW: {notice['title'][:50]}")
        
        # 3. Detect EDITED and PDF_REPLACED
        for notice_id in current_ids & cached_ids:
            current_notice = current_lookup[notice_id]
            cached_notice = cached_notices[notice_id]
            
            # Check for title/date edits
            if (current_notice.get('title') != cached_notice.get('title') or
                current_notice.get('date') != cached_notice.get('date')):
                changes.append(ChangeEvent(
                    change_type=ChangeType.EDITED,
                    notice_id=notice_id,
                    notice_data=current_notice,
                    old_data=cached_notice
                ))
                print(f"✏️ EDITED: {current_notice['title'][:50]}")
            
            # Check for PDF replacement
            current_pdf_hash = pdf_hashes.get(notice_id)
            cached_pdf_hash = cached_notice.get('pdf_hash')
            
            if current_pdf_hash and cached_pdf_hash:
                if current_pdf_hash != cached_pdf_hash:
                    changes.append(ChangeEvent(
                        change_type=ChangeType.PDF_REPLACED,
                        notice_id=notice_id,
                        notice_data=current_notice,
                        old_data=cached_notice
                    ))
                    print(f"📄 PDF_REPLACED: {current_notice['title'][:50]}")
        
        return changes
    
    def categorize_changes(self, changes: List[ChangeEvent]) -> Dict[str, List[ChangeEvent]]:
        """Group changes by type"""
        categorized = {
            'new': [],
            'edited': [],
            'pdf_replaced': [],
            'removed_from_page_1': []
        }
        
        for change in changes:
            categorized[change.change_type.value].append(change)
        
        return categorized
    
    def get_stats(self, changes: List[ChangeEvent]) -> Dict:
        """Get statistics about detected changes"""
        categorized = self.categorize_changes(changes)
        
        return {
            'total_changes': len(changes),
            'new_count': len(categorized['new']),
            'edited_count': len(categorized['edited']),
            'pdf_replaced_count': len(categorized['pdf_replaced']),
            'removed_count': len(categorized['removed_from_page_1'])
        }


if __name__ == "__main__":
    # Test change detector
    detector = ChangeDetector()
    
    # Mock data
    current_notices = [
        {'id': 'abc123', 'title': 'New Notice', 'date': '2026-04-29', 'serial': '1'},
        {'id': 'def456', 'title': 'Existing Notice EDITED', 'date': '2026-04-28', 'serial': '2'},
    ]
    
    page_1_notices = current_notices
    
    cache_data = {
        'notices': {
            'def456': {'id': 'def456', 'title': 'Existing Notice', 'date': '2026-04-28', 'serial': '2'},
            'xyz789': {'id': 'xyz789', 'title': 'Old Notice', 'date': '2026-04-27', 'serial': '3'},
        },
        'previous_page_1_ids': ['def456', 'xyz789']
    }
    
    changes = detector.detect_changes(current_notices, page_1_notices, cache_data)
    stats = detector.get_stats(changes)
    
    print("\n" + "="*50)
    print("CHANGE DETECTOR TEST RESULTS")
    print("="*50)
    print(f"Total changes: {stats['total_changes']}")
    print(f"New: {stats['new_count']}")
    print(f"Edited: {stats['edited_count']}")
    print(f"Removed from page 1: {stats['removed_count']}")
