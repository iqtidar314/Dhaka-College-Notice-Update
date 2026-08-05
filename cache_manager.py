"""
Versioned Cache Manager for Dhaka College Notice Monitor
Handles notice caching with integrity checks and page-1 tracking
"""

import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set


class CacheManager:
    def __init__(self, cache_file: str = 'notice_cache.json'):
        self.cache_file = cache_file
        self.current_version = 2
    
    def _compute_integrity_hash(self, data: Dict) -> str:
        """Compute SHA-256 hash of cache data for integrity check"""
        # Remove fields that change on every save
        data_copy = {k: v for k, v in data.items() if k not in ['integrity_check', 'last_check']}
        data_str = json.dumps(data_copy, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def _create_empty_cache(self) -> Dict:
        """Create a new empty cache structure"""
        return {
            "version": self.current_version,
            "notices": {},
            "previous_page_1_ids": [],
            "dashboard_message_id": None,
            "uptime_streak": 0,
            "last_check": None,
            "integrity_check": ""
        }
    
    def load_cache(self) -> Dict:
        """Load cache from file, with integrity verification and migration"""
        try:
            if not os.path.exists(self.cache_file):
                print("📦 Creating new cache file")
                return self._create_empty_cache()
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Migrate from v1 to v2 if needed (this handles schema changes)
            if data.get('version', 1) < self.current_version:
                print(f"📦 Migrating cache from v{data.get('version', 1)} to v{self.current_version}")
                data = self._migrate_cache(data)
            
            # Ensure all required fields exist
            if 'uptime_streak' not in data:
                data['uptime_streak'] = 0
            
            print(f"✅ Cache loaded: {len(data.get('notices', {}))} notices")
            return data
        
        except Exception as e:
            print(f"❌ Error loading cache: {e}")
            return self._create_empty_cache()
    
    def _migrate_cache(self, old_data: Dict) -> Dict:
        """Migrate old cache format to new format"""
        new_cache = self._create_empty_cache()
        
        # Handle v1 format (list of notices)
        if isinstance(old_data.get('notices'), list):
            for notice in old_data['notices']:
                notice_id = notice.get('id')
                if notice_id:
                    new_cache['notices'][notice_id] = {
                        **notice,
                        'pdf_hash': None,
                        'content_hash': None,
                        'file_type': 'unknown',
                        'first_seen': notice.get('timestamp', datetime.now().isoformat()),
                        'last_seen': datetime.now().isoformat(),
                        'history': [],
                        'was_on_page_1': True  # Assume all v1 notices were on page 1
                    }
        # Handle v2 format (dict of notices)
        elif isinstance(old_data.get('notices'), dict):
            new_cache['notices'] = old_data['notices']
        
        # Preserve other fields
        if 'dashboard_message_id' in old_data:
            new_cache['dashboard_message_id'] = old_data['dashboard_message_id']
        
        return new_cache
    
    def save_cache(self, data: Dict) -> bool:
        """Save cache to file with integrity hash"""
        try:
            # Update integrity check
            data['integrity_check'] = self._compute_integrity_hash(data)
            data['version'] = self.current_version
            data['last_check'] = datetime.now(timezone(timedelta(hours=6))).isoformat()
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Cache saved: {len(data.get('notices', {}))} notices")
            return True
        
        except Exception as e:
            print(f"❌ Error saving cache: {e}")
            return False
    
    def get_notice(self, notice_id: str, cache_data: Dict) -> Optional[Dict]:
        """Get a specific notice from cache"""
        return cache_data.get('notices', {}).get(notice_id)
    
    def update_notice(self, notice: Dict, cache_data: Dict, 
                      pdf_hash: Optional[str] = None, 
                      file_type: Optional[str] = None,
                      was_on_page_1: bool = False) -> Dict:
        """Update or add a notice in cache"""
        notice_id = notice['id']
        notices = cache_data.get('notices', {})
        
        if notice_id in notices:
            # Update existing notice
            cached = notices[notice_id]
            
            # Track history for changes
            history_entry = None
            if cached.get('title') != notice['title']:
                history_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'field': 'title',
                    'old': cached.get('title'),
                    'new': notice['title']
                }
            elif cached.get('date') != notice['date']:
                history_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'field': 'date',
                    'old': cached.get('date'),
                    'new': notice['date']
                }
            
            if history_entry:
                cached.setdefault('history', []).append(history_entry)
            
            # Update fields
            cached['title'] = notice['title']
            cached['date'] = notice['date']
            cached['serial'] = notice['serial']
            cached['download_url'] = notice['download_url']
            cached['last_seen'] = datetime.now().isoformat()
            cached['was_on_page_1'] = was_on_page_1
            
            if pdf_hash:
                cached['pdf_hash'] = pdf_hash
            if file_type:
                cached['file_type'] = file_type
            
            notices[notice_id] = cached
        else:
            # Add new notice
            notices[notice_id] = {
                'id': notice_id,
                'serial': notice['serial'],
                'title': notice['title'],
                'date': notice['date'],
                'download_url': notice['download_url'],
                'pdf_hash': pdf_hash,
                'content_hash': None,
                'file_type': file_type or 'unknown',
                'first_seen': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat(),
                'history': [],
                'was_on_page_1': was_on_page_1
            }
        
        cache_data['notices'] = notices
        return cache_data
    
    def set_previous_page_1_ids(self, ids: List[str], cache_data: Dict) -> Dict:
        """Store the previous page 1 notice IDs"""
        cache_data['previous_page_1_ids'] = ids
        return cache_data
    
    def get_previous_page_1_ids(self, cache_data: Dict) -> Set[str]:
        """Get the previous page 1 notice IDs as a set"""
        return set(cache_data.get('previous_page_1_ids', []))
    
    def set_dashboard_message_id(self, message_id: int, cache_data: Dict) -> Dict:
        """Store the dashboard message ID"""
        cache_data['dashboard_message_id'] = message_id
        return cache_data
    
    def get_dashboard_message_id(self, cache_data: Dict) -> Optional[int]:
        """Get the dashboard message ID"""
        return cache_data.get('dashboard_message_id')
    
    def get_all_cached_ids(self, cache_data: Dict) -> Set[str]:
        """Get all cached notice IDs"""
        return set(cache_data.get('notices', {}).keys())
    
    def mark_notice_removed(self, notice_id: str, cache_data: Dict) -> Dict:
        """Mark a notice as removed (keep in cache for history)"""
        if notice_id in cache_data.get('notices', {}):
            cache_data['notices'][notice_id]['status'] = 'removed'
            cache_data['notices'][notice_id]['removed_at'] = datetime.now().isoformat()
        return cache_data
    
    def increment_uptime_streak(self, cache_data: Dict) -> Dict:
        """Increment the uptime streak counter"""
        cache_data['uptime_streak'] = cache_data.get('uptime_streak', 0) + 1
        return cache_data


if __name__ == "__main__":
    # Test cache manager
    cm = CacheManager()
    cache = cm.load_cache()
    print(f"Cache version: {cache.get('version')}")
    print(f"Total notices: {len(cache.get('notices', {}))}")
