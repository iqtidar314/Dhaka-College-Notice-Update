import requests
import hashlib
import os

URL = "https://your-college-notice-page.com"   # Replace with your notice page
STATE_FILE = "state.txt"

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def main():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    new_hash = get_hash(r.text)

    old_hash = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            old_hash = f.read().strip()

    if old_hash != new_hash:
        send_message("⚡ College Notice Page Changed!")
        with open(STATE_FILE, "w") as f:
            f.write(new_hash)

if __name__ == "__main__":
    main()
