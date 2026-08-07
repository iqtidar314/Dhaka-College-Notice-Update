"""
Dashboard Manager for Dhaka College Notice Monitor
Manages the pinned live status message in Telegram
"""

from typing import Dict, Optional
from datetime import datetime, timezone, timedelta
from telegram_utils import TelegramUtils, _link_footer


class DashboardManager:
    def __init__(self, telegram_utils: TelegramUtils = None):
        self.telegram = telegram_utils or TelegramUtils()
    
    def format_dashboard(self, stats: Dict) -> str:
        """Format the live status dashboard message."""
        status        = stats.get('status', 'unknown')
        status_icon   = 'ONLINE' if status == 'online' else 'OFFLINE'
        last_check    = stats.get('last_check', 'Never')
        total_notices = stats.get('total_notices', 0)
        page_1_count  = stats.get('page_1_count', 0)
        new_today     = stats.get('new_today', 0)
        edited_today  = stats.get('edited_today', 0)
        removed_today = stats.get('removed_today', 0)
        pages_scraped = stats.get('pages_scraped', 0)
        next_check    = stats.get('next_check', 'Unknown')
        uptime_streak = stats.get('uptime_streak', 0)
        total_runs    = stats.get('total_runs', 0)
        today_runs    = stats.get('today_runs', 0)
        total_new     = stats.get('total_new_notices', 0)

        error_line = ""
        last_error = stats.get('last_error')
        if last_error and last_error.get('active'):
            error_type  = last_error.get('type', 'Unknown')
            error_count = last_error.get('count', 0)
            error_line  = f"\n\n<b>Error:</b> {error_type} ({error_count} consecutive)"

        links = _link_footer()

        dashboard = (
            f"<blockquote><b>The DC Archive — Live Monitor</b>\n\n"
            f"Status: <code>{status_icon}</code>  ·  "
            f"Last check: <code>{last_check}</code>  ·  "
            f"Next: <code>{next_check}</code></blockquote>\n\n"
            f"<blockquote>Total notice delivered: <code>{total_new}</code>  ·  "
            f"All time checks: <code>{total_runs} times</code>\n\n"
            f"Today notice delivered: <code>{new_today}</code>  ·  "
            f"Checks today: <code>{today_runs} times</code></blockquote>"
            f"{error_line}\n\n"
            f"{links}"
        )
        return dashboard
    
    def create_or_update_dashboard(self, cache_data: Dict, stats: Dict) -> Optional[int]:
        """
        Create a new dashboard or update existing one
        Returns the message_id
        """
        message_id = cache_data.get('dashboard_message_id')
        dashboard_text = self.format_dashboard(stats)
        
        print(f"📊 Dashboard: message_id={message_id}")
        
        if message_id:
            # Update existing dashboard
            result = self.telegram.edit_message(message_id, dashboard_text)
            if result:
                print(f"✅ Dashboard updated: {message_id}")
                return message_id
            else:
                # Edit failed, create new
                print("⚠️ Dashboard edit failed, creating new")
                message_id = None
        
        if not message_id:
            # Create new dashboard
            result = self.telegram.send_message(dashboard_text)
            if result:
                message_id = result.get('message_id')
                
                # Pin the message
                self.telegram.pin_message(message_id)
                
                print(f"✅ Dashboard created and pinned: {message_id}")
                return message_id
        
        return None
    
    def calculate_stats(self, cache_data: Dict, changes: list, 
                         page_1_notices: list, pages_scraped: int,
                         error_state: Dict = None) -> Dict:
        """Calculate dashboard statistics"""
        now = datetime.now(timezone(timedelta(hours=6)))
        today_str = now.strftime('%Y-%m-%d')
        
        # Count notices
        total_notices = len(cache_data.get('notices', {}))
        page_1_count = len(page_1_notices)
        
        # Count today's changes
        new_today = 0
        edited_today = 0
        removed_today = 0
        
        for change in changes:
            change_date = change.timestamp[:10] if change.timestamp else ''
            if change_date == today_str:
                from change_detector import ChangeType
                if change.change_type == ChangeType.NEW:
                    new_today += 1
                elif change.change_type == ChangeType.EDITED:
                    edited_today += 1
                elif change.change_type == ChangeType.REMOVED_FROM_PAGE_1:
                    removed_today += 1
        
        # Calculate next check (15 minutes from now)
        next_check_time = now + timedelta(minutes=15)
        next_check = next_check_time.strftime('%I:%M %p')
        
        # Get uptime streak from cache
        uptime_streak = cache_data.get('uptime_streak', 0)
        
        # Error state
        last_error = None
        if error_state and error_state.get('last_error', {}).get('active'):
            last_error = error_state['last_error']
        
        # Get new metrics
        total_runs = cache_data.get('total_runs', 0)
        today_runs = cache_data.get('today_runs', 0)
        total_new_notices = cache_data.get('total_new_notices', 0)
        
        return {
            'status': 'online',
            'last_check': now.strftime('%Y-%m-%d %I:%M:%S %p'),
            'total_notices': total_notices,
            'page_1_count': page_1_count,
            'new_today': new_today,
            'edited_today': edited_today,
            'removed_today': removed_today,
            'pages_scraped': pages_scraped,
            'next_check': next_check,
            'uptime_streak': uptime_streak,
            'total_runs': total_runs,
            'today_runs': today_runs,
            'total_new_notices': total_new_notices,
            'last_error': last_error
        }


if __name__ == "__main__":
    # Test dashboard manager
    dm = DashboardManager()
    
    test_stats = {
        'status': 'online',
        'last_check': '2026-04-29 15:00:00',
        'total_notices': 150,
        'page_1_count': 10,
        'new_today': 2,
        'edited_today': 1,
        'removed_today': 0,
        'pages_scraped': 3,
        'next_check': '15:15',
        'uptime_streak': 42,
        'last_error': None
    }
    
    print("Dashboard format test:")
    print(dm.format_dashboard(test_stats))
