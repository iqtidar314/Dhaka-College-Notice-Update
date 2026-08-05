# Project Cache

## Metadata
- Project: The DC Archive — Notice Monitor
- Created: 2026-04-28
- Last Updated: 2026-04-29
- Version: 2.0.0
- Repository: https://github.com/iqtidar314/Dhaka-College-Notice-Update

---

# Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Components](#3-components)
4. [Configuration](#4-configuration)
5. [Data Structures](#5-data-structures)
6. [Error Handling](#6-error-handling)
7. [External APIs](#7-external-apis)
8. [Deployment](#8-deployment)
9. [Known Issues](#9-known-issues)
10. [Change Log](#10-change-log)

---

# 1. Overview

## [OVR-001] Project Summary
Status: active
Last Updated: 2026-04-29

Premium automated monitoring system for Dhaka College notices with PDF-to-image conversion, rich media notifications, live status dashboard, and "The DC Archive" branding. Uses modular architecture with separate components for scraping, caching, change detection, content processing, and Telegram integration.

Tags: #core #overview #monitoring

Related:
- CMP-001 through CMP-007
- DEP-001

---

## [OVR-002] Purpose
Status: active
Last Updated: 2026-04-29

Provide students with premium, visually rich notifications when notices are published, edited, or removed from Dhaka College website. Features PDF-to-image conversion with branding overlay and inline buttons for quick access.

Tags: #purpose #use-case

---

## [OVR-003] Branding
Status: active
Last Updated: 2026-04-29

- **Name**: The DC Archive — Notice
- **Logo**: `assets/logo.png`
- **Facebook**: https://www.facebook.com/thedcarchive
- **Telegram**: https://t.me/thedcarchive_notice
- **Website**: https://www.dhakacollege.edu.bd/en/notice

Tags: #branding #identity

---

# 2. Architecture

## [ARC-001] System Architecture
Status: active
Last Updated: 2026-04-29

**Modular Architecture:**
1. GitHub Actions triggers workflow (scheduled every 15 minutes)
2. `monitor.py` orchestrates all modules
3. `scraper.py` scrapes pages 1-3 for notices
4. `cache_manager.py` loads/saves versioned cache
5. `change_detector.py` detects NEW, EDITED, PDF_REPLACED, REMOVED_FROM_PAGE_1
6. `content_processor.py` downloads PDFs, renders to images, adds branding
7. `telegram_utils.py` sends media groups, documents, dashboard updates
8. `dashboard_manager.py` manages pinned live status message
9. On failure, `runner_handler.py` executes error notification logic

Tags: #architecture #flow #modular

Related:
- CMP-001 through CMP-007
- DEP-001

---

## [ARC-002] Error Handling Strategy
Status: active
Last Updated: 2026-04-29

**3-Strike Rule:**
- Errors tracked in `error_state.json`
- Same error must occur 3 times consecutively before notification
- Supports tracking two error types simultaneously (last_error + previous_error)
- Automatic recovery notifications when errors resolve

Tags: #architecture #error-handling

Related:
- CMP-003
- CMP-004
- DS-002

---

# 3. Components

## [CMP-001] Monitor Orchestrator (monitor.py)
Status: active
Last Updated: 2026-04-29

Main orchestrator that coordinates all modules. Handles error notifications, resolved notifications, and logging.

Dependencies:
- All internal modules

---

## [CMP-002] Scraper Module (scraper.py)
Status: active
Last Updated: 2026-04-29

Multi-page scraper that fetches pages 1-3 from Dhaka College notice board. Returns all notices and per-page breakdown.

Dependencies:
- requests==2.31.0
- beautifulsoup4==4.12.2
- lxml==4.9.3

---

## [CMP-003] Cache Manager (cache_manager.py)
Status: active
Last Updated: 2026-04-29

Versioned cache with integrity checks, migration support, and page-1 tracking. Schema version 2.

---

## [CMP-004] Change Detector (change_detector.py)
Status: active
Last Updated: 2026-04-29

Detects 4 change types: NEW, EDITED, PDF_REPLACED, REMOVED_FROM_PAGE_1. Uses page-1 tracking for accurate removal detection.

---

## [CMP-005] Content Processor (content_processor.py)
Status: active
Last Updated: 2026-04-29

Downloads PDFs, renders all pages to images using PyMuPDF, adds branding overlay with logo and links.

Dependencies:
- Pillow==10.3.0
- PyMuPDF==1.24.5

---

## [CMP-006] Telegram Utils (telegram_utils.py)
Status: active
Last Updated: 2026-04-29

Handles media groups, documents, inline buttons, dashboard editing, and message pinning.

---

## [CMP-007] Dashboard Manager (dashboard_manager.py)
Status: active
Last Updated: 2026-04-29

Manages pinned live status message with statistics, uptime streak, and error display.

Key Methods:
- `fetch_webpage()` - Fetches HTML with timeout and error handling
- `parse_notices()` - Parses notices with fallback selectors
- `get_new_notices()` - Compares current vs cached notices
- `send_telegram_message()` - Sends formatted messages
- `send_error_notification()` - Implements 3-strike error logic
- `send_resolved_notification()` - Notifies when errors resolve

Related:
- ARC-001
- ARC-002
- API-001
- API-002

Notes:
- Uses MD5 hashing for notice IDs (title + date + download_url)
- Timezone: UTC+6 (Bangladesh time)
- Execution time: ~1-5 seconds

Tags: #core #monitoring #parsing

---

## [CMP-002] Runner Handler (runner_handler.py)
Status: active
Last Updated: 2026-04-28
Files:
- runner_handler.py (153 lines)

Dependencies:
- urllib.request
- urllib.parse
- html

Summary:
GitHub Actions failure handler that implements same 3-strike error logic as monitor.py. Notifies when workflow fails repeatedly.

Key Functions:
- `handle_failure()` - Main failure handling logic
- `send_telegram_message()` - Sends error notifications
- `load_error_state()` / `save_error_state()` - State management

Related:
- ARC-002
- DEP-001
- DS-002

Notes:
- Only runs when workflow fails (if: failure())
- Uses GitHub environment variables for context
- Shares error_state.json with monitor.py

Tags: #error-handling #github-actions

---

## [CMP-003] GitHub Actions Workflow
Status: active
Last Updated: 2026-04-28
Files:
- .github/workflows/monitor.yml

Summary:
Scheduled workflow that runs monitor.py every 15 minutes (0, 15, 30, 45). Includes Python setup, caching, and automatic state commit.

Schedule:
- cron: '0 * * * *'
- cron: '15 * * * *'
- cron: '30 * * * *'
- cron: '45 * * * *'

Steps:
1. Checkout repository
2. Set up Python 3.9
3. Cache virtual environment
4. Install dependencies
5. Run monitor.py
6. On failure: run runner_handler.py
7. Always: commit and push state files

Related:
- DEP-001
- OVR-001

Notes:
- Free GitHub accounts may delay execution (5-30 min)
- Commits notice_cache.json, error_state.json, log.txt

Tags: #deployment #github-actions #scheduling

---

# 4. Configuration

## [CFG-001] Environment Variables
Status: active
Last Updated: 2026-04-28

Required Secrets (GitHub Actions):
- `TELEGRAM_TOKEN` - Bot token from @BotFather
- `TELEGRAM_CHAT_ID` - Target chat ID for notifications

Local Environment Variables:
- `TELEGRAM_TOKEN` - Same as above
- `TELEGRAM_CHAT_ID` - Same as above

Related:
- DEP-001
- DEP-002
- API-001

Tags: #configuration #secrets

---

## [CFG-002] Monitoring Frequency
Status: active
Last Updated: 2026-04-28

Current: Every 15 minutes (0, 15, 30, 45 past each hour)

To modify: Edit `.github/workflows/monitor.yml` cron schedule

Examples:
- Every 5 minutes: `*/5 * * * *`
- Every hour: `0 * * * *`
- Daily at 9 AM: `0 9 * * *`

Related:
- CMP-003

Tags: #configuration #scheduling

---

# 5. Data Structures

## [DS-001] Notice Cache (notice_cache.json)
Status: active
Last Updated: 2026-04-28
Files:
- notice_cache.json (auto-generated)

Structure:
```json
{
  "notices": [
    {
      "id": "md5_hash",
      "serial": "1",
      "title": "Notice Title",
      "date": "DD-MM-YYYY",
      "download_url": "https://...",
      "timestamp": "ISO_8601"
    }
  ],
  "last_check": "ISO_8601"
}
```

Purpose:
- Prevent duplicate notifications
- Track previously seen notices
- Persist state between runs

Related:
- CMP-001
- ARC-001

Tags: #data #cache #persistence

---

## [DS-002] Error State (error_state.json)
Status: active
Last Updated: 2026-04-28
Files:
- error_state.json (auto-generated)

Structure:
```json
{
  "last_error": {
    "type": "error_type",
    "active": true,
    "count": 3,
    "detail_error": "error_details",
    "sent": false
  },
  "previous_error": {
    "type": "error_type",
    "active": true,
    "count": 5,
    "sent": true
  }
}
```

Error Types:
- `structure` - Website HTML structure changed
- `network` - Network/timeout errors
- `manualTimeout` - Manual timeout errors
- `runner_failure` - GitHub Actions workflow failure

Purpose:
- Track consecutive errors (3-strike rule)
- Support dual error tracking
- Enable recovery notifications

Related:
- ARC-002
- CMP-001
- CMP-002

Tags: #data #error-tracking #state

---

## [DS-003] Execution Log (log.txt)
Status: active
Last Updated: 2026-04-28
Files:
- log.txt (auto-generated)

Format:
```
YYYY-MM-DD HH:MM:SS |  X.XXs   | status_message
```

Status Messages:
- "🎈No new notices found"
- "📢Found N new notices --> sent to telegram bot"
- "❌error fetching webpage..."
- "✅Page fetched successfully"

Purpose:
- Track execution history
- Monitor performance (execution time)
- Debug issues

Related:
- CMP-001
- ARC-001

Tags: #data #logging #debugging

---

# 6. Error Handling

## [ERR-001] 3-Strike Rule Implementation
Status: active
Last Updated: 2026-04-28

Logic:
1. First/second error: Track count, no notification
2. Third consecutive error: Send notification, mark as sent
3. Different error: Archive current as previous_error, start new count
4. Error resolves: Send recovery notification, reset state

Implementation:
- Both monitor.py and runner_handler.py use identical logic
- Shared error_state.json for coordination
- HTML escaping for security in error messages

Related:
- ARC-002
- CMP-001
- CMP-002
- DS-002

Tags: #error-handling #logic #notification

---

## [ERR-002] Fallback Parsing
Status: active
Last Updated: 2026-04-28

Primary Selector:
```css
body > main > section > div.mt-6.flex.flex-col.gap-6 > div > table > tbody
```

Fallback Strategy:
- If primary fails: Search for any table with rows containing ≥4 <td> elements
- If fallback fails: Send structure error notification

Related:
- CMP-001
- OVR-001

Tags: #error-handling #parsing #robustness

---

# 7. External APIs

## [API-001] Telegram Bot API
Status: active
Last Updated: 2026-04-28

Endpoint:
- `https://api.telegram.org/bot{TOKEN}/sendMessage`

Parameters:
- chat_id - Target chat
- text - Message content (HTML format)
- parse_mode - "HTML"
- disable_notification - Optional (true for silent)
- disable_web_page_preview - false

Usage:
- New notice notifications
- Error alerts (after 3 strikes)
- Recovery notifications
- Runner failure alerts

Related:
- CFG-001
- CMP-001
- CMP-002

Tags: #api #telegram #notifications

---

## [API-002] Dhaka College Website
Status: active
Last Updated: 2026-04-28

URL:
- `https://www.dhakacollege.edu.bd/en/notice`

Method:
- HTTP GET with User-Agent header
- Timeout: 10 seconds
- Retry logic: Manual timeout handling

Structure:
- Table-based notice listing
- Columns: Serial, Title, Date, Download Link
- PDF downloads via direct links

Related:
- CMP-001
- ERR-002

Tags: #api #scraping #target

---

# 8. Deployment

## [DEP-001] GitHub Actions Deployment
Status: active
Last Updated: 2026-04-28

Steps:
1. Fork repository to personal GitHub account
2. Set repository secrets:
   - TELEGRAM_TOKEN
   - TELEGRAM_CHAT_ID
3. Enable Actions in repository settings
4. Workflow runs automatically
5. Manual trigger available via Actions tab

Prerequisites:
- GitHub account
- Telegram bot token
- Telegram chat ID

Related:
- CMP-003
- CFG-001
- OVR-001

Tags: #deployment #github-actions #automation

---

## [DEP-002] Local Deployment
Status: active
Last Updated: 2026-04-28

Steps:
```bash
git clone https://github.com/iqtidar314/Dhaka-College-Notice-Update.git
cd Dhaka-College-Notice-Update
python -m venv venv
# Windows: venv\Scripts\activate
# Linux: source venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python monitor.py
```

Scheduling:
- Linux/macOS: cron job
- Windows: Task Scheduler

Related:
- CFG-001
- CMP-001

Tags: #deployment #local #manual

---

# 9. Known Issues

## [ISS-001] GitHub Actions Delay
Status: active
Last Updated: 2026-04-28

Description:
Free GitHub accounts may delay workflow execution by 5-30 minutes despite 15-minute schedule.

Impact:
- Notifications may not be truly real-time
- Unpredictable timing

Workaround:
- Upgrade to GitHub Pro for consistent scheduling
- Use local deployment for immediate monitoring

Related:
- CMP-003
- DEP-001

Tags: #issue #github-actions #limitation

---

## [ISS-002] Website Structure Changes
Status: pending-verification
Last Updated: 2026-04-28

Description:
If Dhaka College website changes HTML structure, parsing may fail.

Mitigation:
- Fallback parsing implemented
- Structure error notifications after 3 failures
- Manual parser update required if fallback fails

Related:
- ERR-002
- CMP-001

Tags: #issue #maintenance #scraping

---

# 10. Change Log

## 2026-04-29
- Fixed scraper table column index bug due to website structure change (added 'View' column).

## 2026-04-28
- Created project_cache.md
- Documented all components, architecture, and data structures
- Indexed all IDs and cross-references
- Added error handling documentation
- Documented deployment options

---

# Pending Verification

## [PV-001] Telegram Rate Limits
Status: pending-verification
Last Updated: 2026-04-28

Description:
Need to verify Telegram Bot API rate limits for high-frequency notifications.

Action Required:
- Test with multiple rapid notice updates
- Document any rate limit errors
- Implement backoff if needed

Tags: #pending #verification #telegram

---

## [PV-002] Cache Size Management
Status: pending-verification
Last Updated: 2026-04-28

Description:
Monitor notice_cache.json growth over time. Consider implementing cache pruning if file becomes too large.

Action Required:
- Track cache file size over months
- Implement rotation if >1000 notices
- Add cache cleanup logic

Tags: #pending #verification #performance
