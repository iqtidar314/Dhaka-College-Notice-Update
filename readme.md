# College Notice MonitorX

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Enabled-green.svg)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot_API-blue.svg)

*An automated monitoring system that tracks new notices from Dhaka College and sends real-time notifications via Telegram.*

</div>

## 🚀 Features

- **🔄 Automated Monitoring**: Checks for new notices every 5 minutes using GitHub Actions
- (On free GitHub accounts, it may take 5–30 minutes due to scheduling limits)
- ⚡Fast Execution – Runs in ~15 seconds on GitHub runner (no risk of hitting the 2000 min/month limit)
- **📱 Telegram Integration**: Instant notifications sent directly to your Telegram chat
- **🛡️ Robust Error Handling – Detects errors, retries, and alerts you if failures persist
- **💾 Smart Caching – Prevents duplicate or repeated notifications
- **📊 Detailed Logging – Execution logs with runtime tracking
- **🔧 Self-Healing – Recovers automatically from temporary failures

## 📋 Prerequisites

- GitHub account (for automated deployment)
- Telegram account
- Python 3.9+ (for local setup)

## 🔧 Setup Instructions

### Option 1: GitHub Actions (Recommended)

#### 1. Create a Telegram Bot

1. Start a chat with [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the instructions
3. Save the bot token (format: `123456789:ABCDEF...`)
4. Get your chat ID:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your `chat.id` in the response

#### 2. Fork and Configure Repository

1. **Fork this repository** to your GitHub account

2. **Set up GitHub Secrets**:
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add the following repository secrets:
     ```
     TELEGRAM_TOKEN: Your bot token from BotFather
     TELEGRAM_CHAT_ID: Your Telegram chat ID
     ```


#### 4. Enable GitHub Actions

1. Go to your repository → Actions tab
2. Enable workflows if prompted
3. The monitor will now run automatically every 5 minutes

#### 5. Manual Testing

- Go to Actions → College Notice Monitor → Run workflow
- Check the execution logs for any issues

### Option 2: Local Setup

#### 1. Clone and Install

```bash
# Clone your forked repository
git clone https://github.com/iqtidar314/Dhaka-College-Notice-Update.git
cd Dhaka-College-Notice-Update

# Create virtual environment
python -m venv venv
#for windows
venv\Scripts\activate    # for linux:    source venv/bin/activate 

# Install dependencies
pip install -r requirements.txt

# Set environment variables

$env:TELEGRAM_TOKEN="your_bot_token"   #for linux: export TELEGRAM_TOKEN="your_bot_token" 
$env:TELEGRAM_CHAT_ID="your_chat_id"   #for linux: export TELEGRAM_CHAT_ID="your_chat_id"

# Run the monitor
python monitor.py
```


#### 4. Schedule Regular Runs (Optional)

**Using cron (Linux/macOS)**:
```bash
# Edit crontab
crontab -e

# Add this line to run every 5 minutes
*/5 * * * * cd /path/to/college-notice-monitor && source venv/bin/activate && python monitor.py
```

**Using Task Scheduler (Windows)**:
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to repeat every 5 minutes
4. Set action to run your Python script

## 📁 File Structure

```
college-notice-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml          # GitHub Actions workflow
├── monitor.py                   # Main monitoring script
├── requirements.txt             # Python dependencies
├── notice_cache.json           # Cached notices (auto-generated)
├── error_state.json            # Error tracking (auto-generated)
├── log.txt                     # Execution logs (auto-generated)
└── README.md                   # This file
```

## 🔧 Configuration

### Monitoring Frequency
To change the monitoring frequency, edit the cron schedule in `.github/workflows/monitor.yml`:

```yaml
schedule:
  # Current: every 5 minutes
  - cron: '*/5 * * * *'
  
  # Every 10 minutes
  - cron: '*/10 * * * *'
  
  # Every hour
  - cron: '0 * * * *'
  
  # Every day at 9 AM
  - cron: '0 9 * * *'
```

###Monitoring & Logs

- 🔍 GitHub Actions → execution history
- 📱 Telegram → instant alerts
- 📜 Logs (log.txt) → execution details
- 🗂️ Cache (notice_cache.json) → prevents duplicates
- ⚠️ Error State (error_state.json) → tracks failures

### Notice Filtering
To customize notice filtering or add keywords, modify the parsing logic in the `parse_notices` method.

## 📊 Monitoring and Logs

- **🔍GitHub Actions**: Check the Actions tab for execution history
- **📱Telegram**: Receive real-time notifications
- **📜Logs**: View `log.txt` for detailed execution history
- **🗂️Cache**: `notice_cache.json` stores previously seen notices
- **⚠️Error State**: `error_state.json` tracks error occurrences

## 🚨 Troubleshooting

### Common Issues

**1. No notifications received**
- Verify Telegram bot token and chat ID
- Check GitHub Actions logs for errors
- Ensure the bot can send messages to your chat

**2. GitHub Actions failing**
- Check if secrets are correctly set
- Verify workflow file syntax
- Review Actions logs for specific errors

**3. Website structure changes**
- The monitor includes smart fallback parsing
- Error notifications will alert you to structural changes
- Update the CSS selectors in `parse_notices` if needed

### Debug Mode

For local debugging, add print statements or run with verbose output:

```python
# In monitor.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## ⚠️ Disclaimer

This tool is for educational and personal use only. Please respect the college website's terms of service and implement appropriate rate limiting to avoid overloading their servers.

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/iqtidar314/Dhaka-College-Notice-Update/issues) section
2. Create a new issue with detailed information
3. Include relevant logs and error messages

---

<div align="center">

**Made with ❤️ by [iqtidar3.14](https://github.com/iqtidar314/) for Dhaka College students**

⭐ If this project helps you, please consider giving it a star!

</div>
