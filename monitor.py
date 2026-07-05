#!/usr/bin/env python3
"""Cabane de Moiry availability monitor — Sept 18/19, 2026.

Checks the public availability API (no login required) and opens a GitHub
issue when Sept 19 opens up (need 3 places) or Sept 18 counts change.
Stdlib only — no dependencies.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

API = "https://booking.cabane-moiry.ch/api/checkDispoDu.php"
DATES = {"sept18": "18-09-2026", "sept19": "19-09-2026"}
HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "state.json")
LOG_FILE = os.path.join(HERE, "log.csv")
BOOKING_URL = "https://booking.cabane-moiry.ch/calendrier.php"

# "There are 65 places in the dormitory and 19 in mini-dormitory" (en)
# "Il reste 65 places en dortoir et 19 en mini-dortoir" (fr, just in case)
PATTERNS = [
    re.compile(r"There (?:are|is) (\d+) places? in the dormitory and (\d+) in mini-dormitory", re.I),
    re.compile(r"(\d+)\s+places?[^<\d]*(?:dortoir|dormitory)[^<\d]*?(\d+)", re.I),
]


def check(date_str):
    """Return (dortoirs, mini) for a dd-mm-yyyy date, or None on parse failure."""
    data = urllib.parse.urlencode({"date": date_str}).encode()
    req = urllib.request.Request(API, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (availability watch; personal use)",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    for pat in PATTERNS:
        m = pat.search(html)
        if m:
            return int(m.group(1)), int(m.group(2))
    # Full days may phrase things differently; waitlist marker => 0/0
    if "listeAttente" in html or "complète" in html.lower() or "waiting list" in html.lower():
        return 0, 0
    return None


def create_issue(title, body):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print(f"[no-github-env] Would open issue: {title}")
        return
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps({"title": title, "body": body}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "moiry-watch",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"Issue created: {json.loads(r.read())['html_url']}")


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            state = json.load(f)

    results = {}
    for key, date_str in DATES.items():
        res = check(date_str)
        if res is None:
            # Parse failure — alert once, not every run
            if not state.get("parse_error"):
                create_issue(
                    "⚠️ Moiry monitor: cannot parse availability response",
                    f"The response format for {date_str} changed. Check {API} and update monitor.py.",
                )
                state["parse_error"] = True
                with open(STATE_FILE, "w") as f:
                    json.dump(state, f, indent=1)
            print(f"{now} {key}: PARSE FAILURE")
            return
        results[key] = list(res)
    state.pop("parse_error", None)

    s18, s19 = results["sept18"], results["sept19"]
    prev18 = state.get("sept18")
    prev19 = state.get("sept19")
    print(f"{now} sept18={s18[0]}+{s18[1]} sept19={s19[0]}+{s19[1]}")

    with open(LOG_FILE, "a") as f:
        if f.tell() == 0:
            f.write("timestamp,sept18_dortoirs,sept18_mini,sept19_dortoirs,sept19_mini\n")
        f.write(f"{now},{s18[0]},{s18[1]},{s19[0]},{s19[1]}\n")

    # CRITICAL: Sept 19 has places (alert on every change while open)
    if sum(s19) > 0 and s19 != prev19:
        total = sum(s19)
        create_issue(
            f"🚨 SEPT 19 OPEN: {s19[0]} dortoir + {s19[1]} mini-dortoir — BOOK NOW (need 3)",
            f"Cabane de Moiry has **{total} place(s)** on Saturday 19 September 2026 "
            f"({s19[0]} dortoir, {s19[1]} mini-dortoir) as of {now}.\n\n"
            f"👉 **[Book immediately]({BOOKING_URL})** — plan: 3 people, 1 night, "
            f"any dortoir/mini mix, half-board.\n\n"
            f"Openings on a full hut usually vanish within minutes.",
        )
    elif prev19 is not None and sum(prev19) > 0 and sum(s19) == 0:
        create_issue(
            "😞 Sept 19 closed again (back to full)",
            f"The opening on 19 September 2026 is gone as of {now}.",
        )

    # Sept 18 changed
    if prev18 is not None and s18 != prev18:
        create_issue(
            f"⚠️ Sept 18 changed: {s18[0]} dortoir + {s18[1]} mini (was {prev18[0]}+{prev18[1]})",
            f"Availability for Friday 18 September 2026 moved from "
            f"{prev18[0]} dortoir + {prev18[1]} mini to {s18[0]} dortoir + {s18[1]} mini as of {now}.\n\n"
            f"Sept 19 status: {s19[0]} dortoir + {s19[1]} mini.\n\n"
            f"[Booking calendar]({BOOKING_URL})",
        )

    state["sept18"], state["sept19"] = s18, s19
    state["last_check"] = now
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(0)  # never fail the loop
