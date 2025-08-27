# Dhaka College Notice Board Monitor

This repository contains an automated website change monitor that tracks the Dhaka College notice board and sends notifications via Telegram when new notices are posted.

## Features

- 🔄 Monitors the college notice board every 10 minutes
- 📱 Sends Telegram notifications for new notices
- 💾 Caches dependencies and state to save GitHub Actions free tier limits
- 🎯 Detects only new notices added to the top of the list
- 📋 Sends formatted messages with notice titles, dates, and download links
- ⚠️ Error handling with periodic status updates
- 🆓 Runs completely free on GitHub Actions

## Setup Instructions

### 1. Fork/Clone this Repository

1. Fork this repository to your GitHub account
2. Clone it locally or work directly on GitHub

### 2. Create a Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot` command
3. Get your `TELEGRAM_TOKEN`
4. Get your chat ID:
   - Message your bot
   - Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Find your `TELEGRAM_CHAT_ID` in the response

### 3. Set Repository Secrets

Go to your repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:
- `TELEGRAM_TOKEN`: Your bot token from BotFather
- `TELEGRAM_CHAT_ID`: Your chat ID

### 4. Enable GitHub Actions

1. Go to the "Actions" tab in your repository
2. Click "Enable Actions" if prompted
3. The workflow will start running automatically every 10 minutes

### 5. Manual Testing (Optional)

You can manually trigger the monitor:
1. Go to Actions tab
2. Click "Website Change Monitor"
3. Click "Run workflow" → "Run workflow"

## File Structure

```
├── .github/
│   └── workflows/
│       └── monitor.yml          # GitHub Actions workflow
├── cache/                       # Auto-generated cache directory
│   ├── last_state.json         # Previous state cache
│   └── error_count.json        # Error counter
├── monitor.py                   # Main monitoring script
├── requirements.txt             # Python dependencies
└── README.md                   # This file
```

## How It Works

1. **Monitoring**: Every 10 minutes, the script fetches the college notice page
2. **Change Detection**: Compares the current state with cached previous state
3. **New Notice Detection**: Checks if new notices are added to the top of the list
4. **Notification**: Sends formatted Telegram message with:
   - Notice title
   - Publication date
   - Download link (if available)
   - Numbered list format

## Error Handling

- **Website Down**: Sends notification every 10th consecutive failure
- **Network Errors**: Same as website down
- **Telegram API Failures**: Logs errors and retries on next run

## Monitoring Target

The script monitors changes in the notice table body:
```css
body > main > section > div.mt-6.flex.flex-col.gap-4.md:mt-8.md:gap-6.lg:mt-10.lg:flex-row.lg:gap-8 > div > table > tbody
```

## Sample Notification

```
🆕 New Notice(s) Added to Dhaka College!

1. একাদশ(২০২৪-২৫) শ্রেণির পুনঃপুনঃবার্ষিক পরীক্ষার সময়সূচী।
📅 Date: 27-08-2025
📎 Download PDF

⏰ Checked at: 2025-08-27 10:30:00
```

## Troubleshooting

### Common Issues:

1. **No notifications**: Check repository secrets are set correctly
2. **Actions not running**: Ensure Actions are enabled in repository settings
3. **Bot not responding**: Verify bot token and chat ID
4. **Rate limits**: The script includes caching to minimize GitHub Actions usage

### Logs:

Check the Actions tab → Latest workflow run → monitor job for detailed logs

## Contributing

Feel free to submit issues or pull requests for improvements!

## License

This project is open source and available under the MIT License.
