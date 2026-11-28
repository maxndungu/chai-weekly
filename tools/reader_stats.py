"""Counts Chai Weekly's readers in listmonk for the weekly draft notes. Prints numbers only, never addresses.

Env: LISTMONK_URL, LISTMONK_LIST_ID, LISTMONK_API_USER, LISTMONK_API_TOKEN. Run by .github/workflows/reader-stats.yml.
"""
import datetime
import json
import os
import urllib.parse
import urllib.request

base = os.environ["LISTMONK_URL"].rstrip("/")
list_id = int(os.environ["LISTMONK_LIST_ID"].split(",")[0])
auth = {"Authorization": f"token {os.environ['LISTMONK_API_USER'].strip()}:{os.environ['LISTMONK_API_TOKEN'].strip()}"}
week_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).isoformat()[:19]

people, page = [], 1
while True:
    q = urllib.parse.urlencode({"list_id": list_id, "per_page": 100, "page": page})
    with urllib.request.urlopen(urllib.request.Request(f"{base}/api/subscribers?{q}", headers=auth), timeout=30) as r:
        data = json.load(r)["data"]
    people += data.get("results") or []
    if page * 100 >= (data.get("total") or 0):
        break
    page += 1

count = {"confirmed": 0, "unconfirmed": 0, "unsubscribed": 0}
new = gone = 0
for p in people:
    sub = next((l for l in p.get("lists") or [] if l.get("id") == list_id), {})
    status = sub.get("subscription_status", "")
    if p.get("status") == "blocklisted":
        status = "unsubscribed"
    count[status] = count.get(status, 0) + 1
    if status in ("confirmed", "unconfirmed") and (sub.get("subscription_created_at") or "")[:19] >= week_ago:
        new += 1
    if status == "unsubscribed" and (sub.get("subscription_updated_at") or "")[:19] >= week_ago:
        gone += 1

print(f"READERS: {count['confirmed']} confirmed subscribers; {new} new sign-ups in the last 7 days; "
      f"{gone} unsubscribed in the last 7 days; {count['unconfirmed']} signed up but not yet confirmed.")
