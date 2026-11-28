"""Writes the week's WhatsApp post and social media captions from an issue, ready to paste.

    python3 tools/social_text.py _posts/2026-11-25-issue-004.md > posts.md

Everything comes from the issue's front matter (title, snapshot, stories), so it matches what was published.
"""
import pathlib
import re
import sys

import yaml

SITE = "https://chaiweekly.co.ke"
post = pathlib.Path(sys.argv[1])
front = yaml.safe_load(post.read_text().split("---", 2)[1]) or {}
y, m, d, slug = post.stem[:4], post.stem[5:7], post.stem[8:10], post.stem[11:]
issue = front.get("issue")
url = f"{SITE}/issues/{y}/{m}/{d}/{slug}/"
link = lambda src: f"{url}?utm_source={src}&utm_campaign=issue-{issue}"
title = front.get("title", "")
snap = front.get("snapshot") or []
stories = front.get("stories") or []
price = next((s for s in snap if "mombasa" in s.get("label", "").lower()), snap[0] if snap else None)
# Social posts carry the plain figure; notes such as "provisional" stay in the issue itself.
note = re.sub(r",?\s*provisional", "", (price or {}).get("note", ""), flags=re.I).strip(" ,")
price_line = f"{price['label']}: {price['value'].replace('/kg', ' a kilo')}" + (f" ({note})" if note else "") if price else ""
top = [s for s in stories if s.get("headline")][:4]


def wa():
    lines = [f"*Chai Weekly No. {issue}*", "", f"*{title}*", ""]
    if price_line:
        lines += [f"☕ {price_line}", ""]
    lines += ["This week:"] + [f"• {s['headline']}" for s in top]
    lines += ["", f"Read it free: {link('whatsapp')}",
              "Get it by email every Wednesday: chaiweekly.co.ke"]
    return "\n".join(lines)


def caption(limit=None):
    text = f"{title}\n\n" + (f"{price_line}\n\n" if price_line else "") + \
           "Plus: " + "; ".join(s["headline"] for s in top[1:3]) + ".\n\n" + \
           "Chai Weekly is a free newsletter about tea. Read this week's edition free at chaiweekly.co.ke"
    return text


tags = "#ChaiWeekly #KenyaTea #TeaAuction #Mombasa #EastAfrica #TeaIndustry #Tea"
x_text = f"{title}. {price_line}." if price_line else title
x_text = (x_text[:200].rsplit(" ", 1)[0] + "…") if len(x_text) > 200 else x_text
x_text = f"{x_text}\n\nRead free: {link('x')} #KenyaTea #Tea"

print(f"""# Chai Weekly No. {issue}: posts to paste

## WhatsApp (channel or groups)

{wa()}

## Facebook and Instagram

{caption()}

{tags}

## TikTok

{title}{('. ' + price_line + '.') if price_line else ''}
Free every Wednesday at chaiweekly.co.ke (link in bio). {tags}

## X (Twitter)

{x_text}
""")
