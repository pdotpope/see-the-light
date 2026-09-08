"""Weekly checker for new event dates/locations on The Lights Fest.

The site (thelightsfest.com) has no email subscription, RSS feed, or JSON
API. The registration subdomain (register3.thelightsfest.com) renders the
current event list as static HTML, so this scrapes that page, diffs it
against a committed state file, and emails a notification only when a
genuinely new event shows up.
"""
import json
import os
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

EVENTS_URL = "https://register3.thelightsfest.com/"
STATE_PATH = Path(__file__).parent / "state.json"

# A browser-like User-Agent avoids being served a stripped-down response;
# the site doesn't require one, but it's cheap insurance against that changing.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)


def fetch_current_events():
    """Scrape the live event list into {absolute_url: {title, date, start_epoch}}."""
    resp = requests.get(EVENTS_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    events = {}
    for card in soup.select("#standard .singleEvent"):
        link = card.select_one(".eventTitle a")
        if link is None or not link.get("href"):
            continue

        # The event URL slug (e.g. /event/the-lights-kansas-city-area-10-3-2026)
        # encodes city + date and is unique per event, so it doubles as a
        # stable dedup key even if the display date text is reworded later.
        url = urljoin(EVENTS_URL, link["href"])

        # .eventDate's own text is its first text node; the rest of the div
        # is a nested .priceRangeBlock we don't want folded into the date string.
        date_node = card.select_one(".eventDate")
        date_text = date_node.find(string=True, recursive=False) if date_node else None
        date_text = date_text.strip() if date_text else ""

        events[url] = {
            "title": link.get_text(strip=True),
            "date": date_text,
            "start_epoch": card.get("data-start-date"),
        }
    return events


def load_known_events():
    if not STATE_PATH.exists():
        return {}
    with STATE_PATH.open() as f:
        return json.load(f).get("known_events", {})


def save_known_events(known_events):
    with STATE_PATH.open("w") as f:
        json.dump({"known_events": known_events}, f, indent=2, sort_keys=True)
        f.write("\n")


def send_notification(new_events):
    lines = ["New event(s) found on The Lights Fest:", ""]
    for url, info in sorted(new_events.items(), key=lambda kv: kv[1]["start_epoch"] or ""):
        lines.append(f"- {info['title']} ({info['date']})")
        lines.append(f"  {url}")
        lines.append("")
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"The Lights Fest: {len(new_events)} new event(s)"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = os.environ["NOTIFY_EMAIL"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)


def main():
    current_events = fetch_current_events()
    if not current_events:
        # An empty parse almost certainly means the page markup changed
        # underneath the CSS selectors above, not that events dried up.
        print("No events parsed from the page — selector may need updating.", file=sys.stderr)
        sys.exit(1)

    known_events = load_known_events()
    new_events = {url: info for url, info in current_events.items() if url not in known_events}

    if new_events:
        print(f"Found {len(new_events)} new event(s), sending notification.")
        send_notification(new_events)
    else:
        print("No new events.")

    # Merge rather than replace: an event that later disappears from the page
    # (past, canceled) is still remembered, so it won't re-trigger a
    # notification if the same URL slug ever reappears.
    merged_events = {**known_events, **current_events}
    save_known_events(merged_events)


if __name__ == "__main__":
    main()
