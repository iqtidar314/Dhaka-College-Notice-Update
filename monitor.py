import os, json, hashlib, requests, sys, time
from datetime import datetime
from selectolax.parser import HTMLParser

# === Config ===
URL = "https://www.dhakacollege.edu.bd/en/notice"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DATA_DIR = "data"
NOTICES_FILE = os.path.join(DATA_DIR, "notices.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

PRIMARY_SELECTOR = ("body > main > section > "
    "div.mt-6.flex.flex-col.gap-4.md\\:mt-8.md\\:gap-6."
    "lg\\:mt-10.lg\\:flex-row.lg\\:gap-8 > div > table > tbody")
FALLBACKS = [
    "main section table tbody",
]

# === Helpers ===
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_telegram(text: str) -> bool:
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print("Telegram send failed:", e, file=sys.stderr)
        return False

# === Parse notices ===
def parse_notices(html: str, state: dict):
    tree = HTMLParser(html)
    tbody = tree.css_first(PRIMARY_SELECTOR)
    used_selector = PRIMARY_SELECTOR

    if not tbody:
        # try fallbacks
        for fb in FALLBACKS:
            node = tree.css_first(fb)
            if node:
                tbody = node
                used_selector = fb
                break

    if not tbody:
        # heuristic: pick tbody with correct rows
        for node in tree.css("tbody"):
            rows = node.css("tr")
            if rows and all(len(r.css("td")) >= 4 for r in rows):
                if "Download" in rows[0].text():
                    tbody = node
                    used_selector = "heuristic:tbody"
                    break

    if not tbody:
        return None, None

    notices = []
    for row in tbody.css("tr"):
        tds = row.css("td")
        if len(tds) < 4:
            continue
        title = tds[1].text(strip=True)
        date = tds[2].text(strip=True)
        a = tds[3].css_first("a")
        href = a.attributes.get("href") if a else ""
        key = sha256(f"{title}|{date}|{href}")
        notices.append({"title": title, "date": date, "href": href, "key": key})

    return notices, used_selector

# === Main ===
def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    prev_notices = load_json(NOTICES_FILE, [])
    prev_keys = {n["key"] for n in prev_notices}
    state = load_json(STATE_FILE, {"last_error": None, "selector": PRIMARY_SELECTOR})

    # --- Fetch ---
    try:
        r = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        if state.get("last_error") != "network":
            send_telegram(f"⚠️ Network/timeout issue fetching notice page: {e}")
            state["last_error"] = "network"
            save_json(STATE_FILE, state)
        sys.exit(0)

    if state.get("last_error") == "network":
        send_telegram("✅ Network issue resolved")
        state["last_error"] = None
        save_json(STATE_FILE, state)

    # --- Parse ---
    notices, used_selector = parse_notices(html, state)
    if not notices:
        if state.get("last_error") != "structure":
            send_telegram(f"⚠️ Website structure changed.\nBefore: {PRIMARY_SELECTOR}\nAfter: None")
            state["last_error"] = "structure"
            save_json(STATE_FILE, state)
        sys.exit(0)

    if used_selector != PRIMARY_SELECTOR:
        if state.get("last_error") != "structure":
            send_telegram(f"⚠️ Website structure changed.\nBefore: {PRIMARY_SELECTOR}\nAfter: {used_selector}")
            state["last_error"] = "structure"
            state["selector"] = used_selector
            save_json(STATE_FILE, state)
    else:
        if state.get("last_error") == "structure":
            send_telegram("✅ Website structure resolved")
            state["last_error"] = None
            state["selector"] = PRIMARY_SELECTOR
            save_json(STATE_FILE, state)

    # --- Detect new notices ---
    new_notices = [n for n in notices if n["key"] not in prev_keys]

    if not new_notices:
        print("No changes at all")
        sys.exit(0)

    # --- Send all new notices ---
    msg_lines = ["🔔 New Dhaka College notices:"]
    for n in new_notices:
        msg_lines.append(f"- {n['title']}\n  {n['href']}")
    text = "\n".join(msg_lines)

    if send_telegram(text):
        # update cache
        save_json(NOTICES_FILE, notices)
        print("New notices found + notification sent   full update")
    else:
        print("New notices found + notification failed no update")
        sys.exit(1)

if __name__ == "__main__":
    main()
