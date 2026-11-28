"""Counts Chai Weekly's readers in listmonk and emails the numbers privately to Maxwell.

The repository and its Actions logs are public, so the numbers are never printed: they go only by email,
through listmonk, to READER_REPORT_TO (a repo secret holding the address of a subscriber on the list).
Env: LISTMONK_URL, LISTMONK_LIST_ID, LISTMONK_API_USER, LISTMONK_API_TOKEN, READER_REPORT_TO.
Run by .github/workflows/reader-stats.yml. READER_STATS_PRINT=1 prints instead (for local tests only).
"""
import datetime
import json
import os
import urllib.parse
import urllib.request

base = os.environ["LISTMONK_URL"].rstrip("/")
list_id = int(os.environ["LISTMONK_LIST_ID"].split(",")[0])
auth = {"Content-Type": "application/json", "Authorization": f"token {os.environ['LISTMONK_API_USER'].strip()}:{os.environ['LISTMONK_API_TOKEN'].strip()}"}
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

text = (f"{count['confirmed']} confirmed subscribers\n{new} new sign-ups in the last 7 days\n"
        f"{gone} unsubscribed in the last 7 days\n{count['unconfirmed']} signed up but not yet confirmed")
if os.environ.get("READER_STATS_PRINT"):
    print(text); raise SystemExit
to = os.environ.get("READER_REPORT_TO", "").strip()
if not to:
    print("READER_REPORT_TO is not set: no report sent."); raise SystemExit


def api(method, path, payload=None):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode() if payload else None, headers=auth, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("data")


NAME = "Chai Weekly reader report"
body = ('<div style="font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:1.6;color:#121212">'
        '<p><b>Chai Weekly readers this week</b></p><p style="white-space:pre-line">{{ .Tx.Data.text }}</p>'
        '<p style="color:#6e6a62;font-size:13px">Only you get this email. The numbers are not published anywhere.</p></div>')
tpl = [t for t in (api("GET", "/api/templates") or []) if t.get("name") == NAME]
tid = tpl[0]["id"] if tpl else api("POST", "/api/templates", {"name": NAME, "type": "tx", "subject": "Chai Weekly readers this week", "body": body})["id"]
api("POST", "/api/tx", {"subscriber_email": to, "template_id": tid, "data": {"text": text},
                        "from_email": "Chai Weekly <newsletter@chaiweekly.co.ke>", "content_type": "html"})
print("Reader report emailed.")
