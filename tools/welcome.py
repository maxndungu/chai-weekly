#!/usr/bin/env python3
"""Send each new subscriber the latest issue once, so they don't wait until next Wednesday.

Runs on a schedule (.github/workflows/welcome.yml). It asks listmonk for everyone confirmed on the
Chai Weekly list, and sends the "Chai Weekly welcome" email (made by tools/to_listmonk.py from the
newest issue) to those who joined on or after WELCOME_SINCE and have not had it yet. Each one is then
marked in listmonk with the attribute chai_welcomed (the date), so nobody gets it twice.

Usage:
  LISTMONK_URL=https://list.chaiweekly.co.ke LISTMONK_LIST_ID=3 \
  LISTMONK_API_USER=... LISTMONK_API_TOKEN=... WELCOME_SINCE=2026-11-26 \
  python3 tools/welcome.py

Optional:
  WELCOME_MAX=20       send at most this many in one run (keeps inside the mailbox's daily limit)
  WELCOME_DRY_RUN=1    only list who would get it
Standard library only.
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

WELCOME_NAME = "Chai Weekly welcome"
base = os.environ["LISTMONK_URL"].rstrip("/")
list_id = int(os.environ["LISTMONK_LIST_ID"].split(",")[0])
since = os.environ.get("WELCOME_SINCE", "").strip()
most = int(os.environ.get("WELCOME_MAX") or 20)
dry = bool(os.environ.get("WELCOME_DRY_RUN"))
sender = os.environ.get("LISTMONK_FROM") or "Chai Weekly <newsletter@chaiweekly.co.ke>"
auth = {"Authorization": f"token {os.environ['LISTMONK_API_USER']}:{os.environ['LISTMONK_API_TOKEN']}",
        "Content-Type": "application/json"}

if not since:
    print("WELCOME_SINCE (welcome_since in _config.yml) is empty: welcome emails are off."); sys.exit(0)


def api(method, path, payload=None):
    req = urllib.request.Request(f"{base}{path}", data=json.dumps(payload).encode() if payload is not None else None,
                                 headers=auth, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("data")


try:
    tpl = [t for t in (api("GET", "/api/templates") or []) if t.get("name") == WELCOME_NAME and t.get("type") == "tx"]
except urllib.error.HTTPError as e:
    print(f"::warning::listmonk refused to list templates ({e.code}). Tick templates (get) for the Drafts role."); sys.exit(0)
if not tpl:
    print("No welcome email yet: it is made when the next issue is merged (or run Email draft by hand)."); sys.exit(0)
tpl_id = tpl[0]["id"]

# Everyone confirmed on the list, page by page.
people, page = [], 1
while True:
    q = urllib.parse.urlencode({"list_id": list_id, "subscription_status": "confirmed", "per_page": 100, "page": page})
    d = api("GET", f"/api/subscribers?{q}") or {}
    rows = d.get("results") or []
    people += rows
    if len(rows) < 100:
        break
    page += 1


def joined(p):
    """When they joined this list (falls back to when the subscriber was created).
    In a subscriber's lists, created_at is when the LIST was made; the join date is subscription_created_at."""
    for l in p.get("lists") or []:
        if l.get("id") == list_id:
            return (l.get("subscription_created_at") or p.get("created_at") or "")[:10]
    return (p.get("created_at") or "")[:10]


todo = [p for p in people
        if p.get("status") == "enabled" and not (p.get("attribs") or {}).get("chai_welcomed") and joined(p) >= since]
print(f"{len(people)} confirmed readers; {len(todo)} still to welcome" + (f" (sending {most} this run)" if len(todo) > most else ""))
today = datetime.date.today().isoformat()
sent = 0
for p in todo[:most]:
    who = p["email"]
    if dry:
        print("would welcome", who); continue
    # Mark them first (keeping their name, lists and other details), so a failure can never send it twice.
    keep = {"email": who, "name": p.get("name") or "", "status": p.get("status"),
            "lists": [l["id"] for l in p.get("lists") or [] if l.get("subscription_status") != "unsubscribed"],
            "preserve_subscription_status": True}
    try:
        api("PUT", f"/api/subscribers/{p['id']}", dict(keep, attribs=dict(p.get("attribs") or {}, chai_welcomed=today)))
    except urllib.error.HTTPError as e:
        print(f"::warning::Could not mark subscriber {p['id']} ({e.code}: {e.read()[:200]!r}), so nothing was sent. "
              "If it says permission denied: listmonk > Users > User roles > Drafts > add the Chai Weekly list with get and manage.")
        continue
    try:
        api("POST", "/api/tx", {"subscriber_id": p["id"], "template_id": tpl_id, "from_email": sender,
                                "messenger": "email", "content_type": "html"})
    except urllib.error.HTTPError as e:
        print(f"::warning::Could not send to subscriber {p['id']} ({e.code}: {e.read()[:200]!r}). "
              "If it is 403, tick tx (send) for the Drafts role in listmonk > Users > User roles.")
        api("PUT", f"/api/subscribers/{p['id']}", dict(keep, attribs=p.get("attribs") or {}))  # try again next run
        break
    sent += 1
print(f"Welcome email sent to {sent} new reader(s).")
