import html
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


LIST_URL = "https://webbackend.daffodilvarsity.edu.bd/department-notice/cse"
BASE_URL = "https://webbackend.daffodilvarsity.edu.bd"
STATE_FILE = Path("last_notice_cse.json")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()


def normalize_chat_id(raw_chat_id: str) -> str:
    chat_id = raw_chat_id.strip()
    if not chat_id:
        raise ValueError("TELEGRAM_CHAT_ID cannot be empty.")

    if chat_id.startswith(("http://", "https://")):
        parsed = urlparse(chat_id)
        if parsed.netloc.lower() in {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}:
            path = parsed.path.strip("/")
            if path:
                chat_id = path.split("/")[0]

    if chat_id.lstrip("-").isdigit():
        return chat_id

    username = chat_id[1:] if chat_id.startswith("@") else chat_id
    username = username.strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{5,}", username):
        raise ValueError(
            "TELEGRAM_CHAT_ID must be a numeric chat ID, a valid @channel_username, or a t.me channel link."
        )

    return f"@{username}"


CHAT_ID = normalize_chat_id(os.environ["TELEGRAM_CHAT_ID"])


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) DIUNoticeBot/1.0",
        "Accept": "text/html,application/xhtml+xml",
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def clean_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return lines


def get_latest_notice() -> dict:
    html_doc = fetch_html(LIST_URL)
    soup = BeautifulSoup(html_doc, "html.parser")

    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = link.get_text(" ", strip=True)

        if "/noticed/" in href and title:
            url = urljoin(BASE_URL, href)
            notice_id_match = re.search(r"/noticed/(\d+)", url)

            if not notice_id_match:
                continue

            return {
                "id": notice_id_match.group(1),
                "title": title,
                "url": url,
            }

    raise RuntimeError("Could not find latest CSE notice link.")


def get_notice_detail(notice: dict) -> dict:
    html_doc = fetch_html(notice["url"])
    soup = BeautifulSoup(html_doc, "html.parser")

    lines = clean_lines(soup.get_text("\n"))

    title = notice["title"]

    start_index = None

    for i, line in enumerate(lines):
        if "Notice Detail" in line:
            start_index = i + 1
            break

    if start_index is None:
        for i, line in enumerate(lines):
            if line == title:
                start_index = i + 1
                break

    if start_index is None:
        raise RuntimeError("Could not find notice content.")

    stop_words = {
        "Tweet",
        "Get in Touch",
        "Branding",
        "Useful Links",
        "Subscribe Us!",
        "Connect With Us",
        "Visitor Counter:",
    }

    content_lines = []

    for line in lines[start_index:]:
        if line in stop_words:
            break

        if line == title:
            continue

        if line.lower() == "cse":
            continue

        if "Notice Detail" in line:
            continue

        content_lines.append(line)

    content = "\n".join(content_lines).strip()

    return {
        **notice,
        "title": title,
        "content": content,
    }


def load_last_notice_id() -> str | None:
    if not STATE_FILE.exists():
        return None

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data.get("id")
    except Exception:
        return None


def save_last_notice_id(notice_id: str) -> None:
    STATE_FILE.write_text(
        json.dumps({"id": notice_id}, indent=2),
        encoding="utf-8",
    )


def split_telegram_message(message: str, limit: int = 3900) -> list[str]:
    if len(message) <= limit:
        return [message]

    chunks = []
    current = ""

    for paragraph in message.split("\n\n"):
        if len(current) + len(paragraph) + 2 <= limit:
            current += ("\n\n" if current else "") + paragraph
        else:
            if current:
                chunks.append(current)
            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def send_telegram_message(text: str) -> None:
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for chunk in split_telegram_message(text):
        response = requests.post(
            api_url,
            json={
                "chat_id": CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=30,
        )
        response.raise_for_status()


def build_message(notice: dict) -> str:
    title = html.escape(notice["title"])
    content = html.escape(notice["content"])
    url = html.escape(notice["url"])

    return f"<b>DIU CSE Notice</b>\n\n<b>{title}</b>\n\n{content}\n\n<a href=\"{url}\">Open notice</a>"


def main() -> None:
    latest = get_latest_notice()
    last_id = load_last_notice_id()

    if latest["id"] == last_id:
        print(f"No new CSE notice. Latest notice id: {latest['id']}")
        return

    notice = get_notice_detail(latest)
    message = build_message(notice)

    send_telegram_message(message)
    save_last_notice_id(notice["id"])

    print(f"Sent CSE notice: {notice['title']}")


if __name__ == "__main__":
    main()
