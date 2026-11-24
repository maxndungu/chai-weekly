#!/usr/bin/env python3
"""Turn a published issue into a listmonk campaign DRAFT (never sends).

Usage:
  LISTMONK_URL=https://list.chaiweekly.co.ke LISTMONK_LIST_ID=3 \
  LISTMONK_API_USER=... LISTMONK_API_TOKEN=... SITE_URL=https://... \
  python3 tools/to_listmonk.py _posts/<file>.md

The draft appears under Campaigns in listmonk; Maxwell checks it and presses Start to send.
Links in the email get ?utm_source=newsletter so site visits from the email can be counted.
listmonk's email template adds the unsubscribe link to every email.
"""
import json
import os
import pathlib
import re
import sys
import urllib.request

path = pathlib.Path(sys.argv[1])
text = path.read_text()
_, front, body = text.split("---", 2)
if re.search(r"^preview:\s*true", front, re.M):
    print("Preview issue: no email draft created."); sys.exit(0)
title = re.search(r'^title:\s*"?(.*?)"?\s*$', front, re.M).group(1)
issue = re.search(r"^issue:\s*(\d+)", front, re.M).group(1)
deck = (re.search(r'^deck:\s*"?(.*?)"?\s*$', front, re.M) or [None, ""])[1]


# URL of the issue on the site, matching the permalink in _config.yml
y, m, d, slug = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.*)\.md", path.name).groups()
site = os.environ["SITE_URL"].rstrip("/")
web = f"{site}/issues/{y}/{m}/{d}/{slug}/"

body = re.sub(r"^\{:[^}]*\}\s*$", "", body, flags=re.M)  # kramdown attribute lines


def read_ads(p=pathlib.Path("_data/ads.yml")):
    """Tiny reader for the flat list in _data/ads.yml (stdlib only)."""
    ads, cur = [], None
    for line in p.read_text().splitlines() if p.exists() else []:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(-\s+|\s+)(\w+):\s*(.*?)\s*(#.*)?$", line)
        if not m:
            continue
        if m.group(1).startswith("-"):
            cur = {}
            ads.append(cur)
        if cur is not None:
            cur[m.group(2)] = m.group(3).strip().strip('"').strip("'")
    return ads


def issue_ad(issue_date):
    """Markdown for the 'issue' sponsor box active on the issue date, or ''. Clearly labelled as sponsored."""
    for a in read_ads():
        if a.get("slot") == "issue" and a.get("start", "") <= issue_date <= a.get("end", ""):
            img = a.get("image", "")
            if img and "://" not in img:
                img = f"{site}/{img.lstrip('/')}"
            out = f"---\n\n**SPONSORED · Supported by {a.get('sponsor', '')}**\n\n"
            if img:
                out += f"[![{a.get('alt') or a.get('sponsor', '')}]({img})]({a.get('link', '')})\n\n"
            return out + f"{a.get('text', '')} [{a.get('link_text') or 'Find out more'} →]({a.get('link', '')})\n\n---\n"
    return ""


body = re.sub(r"^\{%\s*include ad\.html[^%]*%\}\s*$", issue_ad(f"{y}-{m}-{d}"), body, flags=re.M)
body = re.sub(r"^\{%.*?%\}\s*$", "", body, flags=re.M)  # any other Liquid tags
# Links to the site's own pages, e.g. {{ '/weather/' | relative_url }}, become full web addresses.
body = re.sub(r"\{\{\s*['\"]([^'\"]*)['\"]\s*\|\s*(?:relative|absolute)_url\s*\}\}", lambda m: site + "/" + m.group(1).lstrip("/"), body)
tag = "utm_source=newsletter&utm_medium=email&utm_campaign=issue-" + issue
email = (
    f"*{deck}*\n\n[Read this edition on the web]({web}?{tag})\n\n{body.strip()}\n\n---\n\n"
    f"[Read online]({web}?{tag}) · [All editions]({site}/archive/?{tag})\n"
)

# listmonk reads {{ ... }} as its own template code; issues never need it, so take any stray braces apart.
email = email.replace("{{", "{ {").replace("}}", "} }")

base = os.environ["LISTMONK_URL"].rstrip("/")
payload = {
    "name": f"Chai Weekly No. {issue}",
    "subject": f"Chai Weekly No. {issue}: {title}",
    "lists": [int(x) for x in os.environ["LISTMONK_LIST_ID"].replace(" ", "").split(",") if x],
    "type": "regular",
    "content_type": "markdown",
    "body": email,
    "messenger": "email",
    "tags": ["issue"],
}
if os.environ.get("LISTMONK_FROM"):
    payload["from_email"] = os.environ["LISTMONK_FROM"]
req = urllib.request.Request(
    f"{base}/api/campaigns",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"token {os.environ['LISTMONK_API_USER']}:{os.environ['LISTMONK_API_TOKEN']}",
        "Content-Type": "application/json",
    },
    method="POST",
)
# A new campaign is always created as a draft; sending needs a person to press Start in listmonk.
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.load(r).get("data", {})
    print(f"listmonk draft created: {base}/admin/campaigns/{data.get('id')} (status: {data.get('status')})")
