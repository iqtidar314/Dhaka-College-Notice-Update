import requests
from bs4 import BeautifulSoup
import hashlib
import os

URL = "https://www.dhakacollege.edu.bd/en/notice"   # 🔴 Replace with your notice page
STATE_FILE = "state.txt"

BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def get_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def main():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # 🔴 Select the specific tbody
    tbody = soup.select_one(
        "body > main > section > div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6.lg\\:mt-10.lg\\:flex-row.lg\\:gap-8 > div > table > tbody"
    )
    if not tbody:
        send_message("⚠ Could not find the notice table on the page.")
        return

    tbody_html = str(tbody)
    new_hash = get_hash(tbody_html)

    old_hash = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            old_hash = f.read().strip()

    if old_hash != new_hash:
        # Save new hash
        with open(STATE_FILE, "w") as f:
            f.write(new_hash)

        # Get latest 3 notices
        rows = tbody.select("tr")[:3]
        notices = []
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 4:
                title = cols[1].get_text(strip=True)  # 2nd <td> = title
                link_el = cols[3].select_one("a")     # 4th <td> = download link
                if link_el:
                    link = link_el.get("href")
                    if link and not link.startswith("http"):
                        from urllib.parse import urljoin
                        link = urljoin(URL, link)
                    notices.append(f"🔗 <a href='{link}'>{title}</a>")

        if notices:
            msg = "📢 <b>New College Notice(s)</b>\n\n" + "\n".join(notices)
            send_message(msg)
        else:
            send_message("⚡ College notice page changed, but no notices parsed.")

if __name__ == "__main__":
    main()
