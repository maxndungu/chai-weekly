#!/usr/bin/env python3
"""Turn a published issue into a Buttondown email draft (never sends).

Usage: BUTTONDOWN_API_KEY=... SITE_URL=https://... python3 tools/to_buttondown.py _posts/<file>.md
Links in the email get ?utm_source=newsletter so site visits from the email can be counted.
Buttondown adds its own unsubscribe link to every email.
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
tag = "utm_source=newsletter&utm_medium=email&utm_campaign=issue-" + issue
email = (
    f"*{deck}*\n\n[Read this edition on the web]({web}?{tag})\n\n{body.strip()}\n\n---\n\n"
    f"[Read online]({web}?{tag}) · [All editions]({site}/archive/?{tag})\n"
)

req = urllib.request.Request(
    "https://api.buttondown.com/v1/emails",
    data=json.dumps({"subject": f"Chai Weekly No. {issue}: {title}", "body": email, "status": "draft"}).encode(),
    headers={
        "Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}",
        "Content-Type": "application/json",
        "X-API-Version": "2026-04-01",  # this version defaults to draft and refuses to send without confirmation
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as r:
    print("Buttondown draft created:", json.load(r).get("id"))
