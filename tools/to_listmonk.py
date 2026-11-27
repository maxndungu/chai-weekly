#!/usr/bin/env python3
"""Turn a published issue into a listmonk campaign DRAFT (never sends), styled like the website.

Usage:
  LISTMONK_URL=https://list.chaiweekly.co.ke LISTMONK_LIST_ID=3 \
  LISTMONK_API_USER=... LISTMONK_API_TOKEN=... SITE_URL=https://... \
  python3 tools/to_listmonk.py _posts/<file>.md

Optional:
  LISTMONK_CAMPAIGN_ID=2   update that existing draft instead of making a new one (e.g. after a design change)
  LISTMONK_AUTOSEND_MINUTES=15  after making a NEW campaign, schedule it to send this many minutes later
                           (0 = start at once). Unset or empty = leave it as a draft for a person to start.
  LISTMONK_WELCOME=1       also copy this issue into the "Chai Weekly welcome" email, the one
                           tools/welcome.py sends once to each new subscriber
  LISTMONK_FROM=...        sender (default: Chai Weekly <newsletter@chaiweekly.co.ke>)
  EMAIL_HTML_OUT=file      also save the email as a local HTML file (for previews)
  LISTMONK_DRY_RUN=1       do not contact listmonk at all (with EMAIL_HTML_OUT, for previews)

The campaign appears under Campaigns in listmonk. On a merge the workflow schedules it to send a few minutes
later (listmonk_autosend_minutes in _config.yml); pause it there to stop it.
The email is built here (masthead, headline, contents and a link to the full edition on the web) as HTML with inline styles so it looks
like the newspaper website in Gmail and on phones. Its frame and footer (with the unsubscribe link) are
the listmonk template "Chai Weekly newspaper", kept in tools/email/listmonk-template.html and copied
into listmonk on every run. A plain-text copy goes along for mail apps that do not show HTML.
Links in the email get ?utm_source=newsletter so site visits from the email can be counted.
Needs the Python packages markdown and PyYAML (installed by the workflow).
"""
import html
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

import markdown
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE_FILE = ROOT / "tools" / "email" / "listmonk-template.html"
TEMPLATE_NAME = "Chai Weekly newspaper"

path = pathlib.Path(sys.argv[1])
text = path.read_text()
_, front, body = text.split("---", 2)
meta = yaml.safe_load(front) or {}
if meta.get("preview"):
    print("Preview issue: no email draft created."); sys.exit(0)
title = str(meta["title"])
issue = str(meta["issue"])
deck = str(meta.get("deck") or "")

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


def utm(url):
    """Add the newsletter tag to links to our own site (keeps any #section at the end)."""
    if not url.startswith(site) or "utm_source=" in url:
        return url
    base, _, frag = url.partition("#")
    return base + ("&" if "?" in base else "?") + tag + (f"#{frag}" if frag else "")


# ---- Plain-text copy (also what older mail apps show) ----
plain = (
    f"{deck}\n\nIn this edition:\n"
    + "".join(f"- {s_.get('section', '')}: {s_.get('headline', '')}\n" for s_ in (meta.get("stories") or []))
    + f"\nRead the full edition: {web}?{tag}\n\n---\n\n"
    f"Read online: {web}?{tag}\nAll editions: {site}/archive/?{tag}\n"
)

# ---- HTML email, styled like the newspaper website ----
INK, INK2, MUTED, RULE, HAIR, ACCENT, BOX = "#121212", "#3d3b37", "#6e6a62", "#1d1d1d", "#d9d5cc", "#1f5d34", "#f2efe6"
DISPLAY = "'Playfair Display', Georgia, 'Times New Roman', serif"
SERIF = "'Source Serif 4', Georgia, 'Times New Roman', serif"
SANS = "'Libre Franklin', Helvetica, Arial, sans-serif"
STYLES = {
    "p": "margin:0 0 16px;",
    "h2": f"font-family:{SANS}; font-size:13px; line-height:1.3; font-weight:800; letter-spacing:.12em; text-transform:uppercase; "
          f"color:{INK}; border-top:2px solid {RULE}; padding-top:10px; margin:40px 0 14px;",
    "h3": f"font-family:{DISPLAY}; font-size:22px; line-height:1.25; font-weight:700; color:{INK}; margin:28px 0 12px;",
    "a": f"color:{ACCENT};",
    "ul": "margin:0 0 16px; padding-left:22px;",
    "ol": "margin:0 0 16px; padding-left:22px;",
    "li": "margin:0 0 8px;",
    "hr": f"border:0; border-top:1px solid {HAIR}; margin:28px 0;",
    "blockquote": f"margin:24px 0; padding:0 0 0 16px; border-left:3px solid {ACCENT}; font-family:{DISPLAY}; font-style:italic; font-size:20px; line-height:1.4;",
    "table": f"width:100%; border-collapse:collapse; margin:4px 0 16px; font-family:{SANS}; font-size:13px; line-height:1.4;",
    "th": f"background:{BOX}; text-align:left; padding:8px 8px; border-bottom:2px solid {RULE}; font-size:11px; font-weight:800; "
          "letter-spacing:.06em; text-transform:uppercase; vertical-align:bottom;",
    "td": f"padding:8px 8px; border-bottom:1px solid {HAIR}; vertical-align:top;",
    "img": "max-width:100%; height:auto; border:0;",
}


def add_style(tag_html, style):
    """Put our inline style on one opening tag, keeping any style it already has (e.g. table column alignment)."""
    if 'style="' in tag_html:
        return tag_html.replace('style="', f'style="{style} ', 1)
    return tag_html[:-1].rstrip("/").rstrip() + f' style="{style}"' + (" />" if tag_html.endswith("/>") else ">")


def style_html(h):
    # Lines that are only a note in italics (the "Sources: ..." lines) look like the site's small grey notes.
    h = re.sub(r"<p><em>((?:(?!</p>).)*)</em></p>",
               lambda mm: f'<p style="margin:0 0 16px; font-family:{SANS}; font-size:13px; line-height:1.5; color:{MUTED};">{mm.group(1)}</p>', h, flags=re.S)
    for t, st in STYLES.items():
        h = re.sub(rf"<{t}(\s[^>]*)?/?>", lambda mm, st=st: add_style(mm.group(0), st), h)
    h = re.sub(r'href="([^"]+)"', lambda mm: f'href="{html.escape(utm(html.unescape(mm.group(1))), quote=True)}"', h)
    # Wide tables scroll sideways on phones instead of squeezing the page.
    return re.sub(r"(<table[^>]*>.*?</table>)", r'<div style="overflow-x:auto; -webkit-overflow-scrolling:touch;">\1</div>', h, flags=re.S)


def esc(v):
    return html.escape(str(v), quote=True)


months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
import datetime as _dt
day = _dt.date(int(y), int(m), int(d))
long_date = f"{day.strftime('%A')}, {day.day} {months[day.month - 1]} {day.year}"
short_date = f"{day.day} {months[day.month - 1]} {day.year}"
link = f"color:{INK}; text-decoration:none;"

masthead = f"""
<table role="presentation" class="cw-strip" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid {HAIR}; font-family:{SANS}; font-size:11px; font-weight:600; letter-spacing:.08em; text-transform:uppercase; color:{INK2};">
  <tr><td style="padding:8px 0; text-align:left;">Vol. I · No. {esc(issue)}</td>
      <td style="padding:8px 0; text-align:center;">{esc(long_date)}</td>
      <td style="padding:8px 0; text-align:right;">Free · Weekly</td></tr>
</table>
<div style="text-align:center;">
  <a href="{esc(utm(site + '/'))}" class="cw-nameplate" style="display:block; font-family:{DISPLAY}; font-weight:900; font-size:64px; line-height:1; letter-spacing:-.01em; color:{INK}; text-decoration:none; margin:18px 0 6px;">Chai Weekly</a>
  <div style="font-family:{SERIF}; font-style:italic; font-size:15px; color:{INK2}; margin:0 0 14px;">Tea news from East Africa and the world, every week</div>
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:3px double {RULE}; border-bottom:1px solid {RULE};">
  <tr><td align="center" style="padding:9px 0; font-family:{SANS}; font-size:11px; font-weight:600; letter-spacing:.1em; text-transform:uppercase; line-height:1.9;">
    <a href="{esc(utm(web))}" style="{link}">Read on the web</a> &nbsp;&nbsp;
    <a href="{esc(utm(site + '/auctions/'))}" style="{link}">Auctions</a> &nbsp;&nbsp;
    <a href="{esc(utm(site + '/weather/'))}" style="{link}">Tea weather</a> &nbsp;&nbsp;
    <a href="{esc(utm(site + '/events/'))}" style="{link}">Events</a> &nbsp;&nbsp;
    <a href="{esc(utm(site + '/archive/'))}" style="{link}">Archive</a>
  </td></tr>
</table>"""

snap = meta.get("snapshot") or []
ticker = ""
if snap:
    items = []
    for s_ in snap:
        note = f' <span style="color:{ACCENT}; font-weight:600;">{esc(s_.get("note"))}</span>' if s_.get("note") else ""
        items.append(f'<span style="display:inline-block; margin:2px 10px; white-space:nowrap;"><b style="font-size:10px; font-weight:800; '
                     f'letter-spacing:.06em; text-transform:uppercase;">{esc(s_.get("label", ""))}</b> {esc(s_.get("value", ""))}{note}</span>')
    ticker = (f'<div style="text-align:center; padding:7px 0; border-bottom:1px solid {HAIR}; font-family:{SANS}; font-size:13px; '
              f'line-height:1.5; color:{INK};">{"".join(items)}</div>')

contents = ""
stories = meta.get("stories") or []
if stories:
    rows = "".join(
        f'<tr><td style="padding:7px 0; border-top:{"0" if i == 0 else "1px solid " + HAIR};">'
        f'<a href="{esc(utm(web + "#" + str(s_.get("anchor", ""))))}" style="text-decoration:none; color:{INK};">'
        f'<span style="display:block; font-family:{SANS}; font-size:10px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:{ACCENT};">{esc(s_.get("section", ""))}</span>'
        f'<span style="font-family:{SERIF}; font-size:16px; font-weight:600; line-height:1.35;">{esc(s_.get("headline", ""))}</span></a></td></tr>'
        for i, s_ in enumerate(stories))
    contents = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{BOX}" style="background:{BOX}; border-top:2px solid {RULE}; margin:0 0 28px;">'
                f'<tr><td style="padding:14px 18px;"><div style="font-family:{SANS}; font-size:12px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; margin:0 0 6px;">In this edition</div>'
                f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr></table>')

words = len(re.findall(r"\w+", body))
# The email is the short version (Maxwell, 26 Nov 2026): headline, contents and a link to the full edition on the web.
# Only a booked sponsor box from the issue comes along with it.
_ad = issue_ad(f"{y}-{m}-{d}").strip().strip("-").strip()
ad_html = style_html(markdown.markdown(_ad, output_format="html")) if _ad else ""
if ad_html:
    ad_html = f'<div style="border-top:1px solid {HAIR}; margin-top:24px; padding-top:16px; font-family:{SANS}; font-size:14px;">{ad_html}</div>'

content = f"""{masthead}
{ticker}
<div style="padding-top:28px;">
  <div style="font-family:{SANS}; font-size:12px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:{ACCENT}; margin:0 0 10px;">Edition No. {esc(issue)} · {esc(short_date)}</div>
  <h1 class="cw-headline" style="font-family:{DISPLAY}; font-size:36px; line-height:1.1; font-weight:700; color:{INK}; margin:0 0 14px;">{esc(title)}</h1>
  {f'<div style="font-family:{SERIF}; font-size:20px; line-height:1.4; color:{INK2}; margin:0 0 14px;">{esc(deck)}</div>' if deck else ''}
  <div style="font-family:{SANS}; font-size:13px; color:{MUTED}; margin:0 0 22px;">By the Chai Weekly desk · {words // 220 + 1} min read · <a href="{esc(utm(web))}" style="color:{ACCENT}; font-weight:600; text-decoration:none;">Read on the web</a></div>
  {contents}
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 8px;"><tr><td bgcolor="{ACCENT}" style="background:{ACCENT};">
    <a href="{esc(utm(web))}" style="display:inline-block; padding:13px 26px; font-family:{SANS}; font-size:15px; font-weight:700; color:#ffffff; text-decoration:none;">Read the full edition →</a>
  </td></tr></table>
  {ad_html}
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{BOX}" style="background:{BOX}; border-top:2px solid {RULE}; margin-top:28px;">
  <tr><td style="padding:16px 18px; font-family:{SANS}; font-size:15px; line-height:1.5;">
    Got a story from your factory, shamba or tea cup?
    <a href="{esc(utm(site + '/submit/'))}" style="color:{ACCENT}; font-weight:700; text-decoration:none;">Send it to Chai Weekly →</a><br>
    <span style="font-size:13px; color:{MUTED};">Know someone in tea who would like this? Forward it, or send them to
    <a href="{esc(utm(site + '/'))}" style="color:{ACCENT};">chaiweekly.co.ke</a> to subscribe free.</span>
  </td></tr>
</table>"""

# listmonk reads {{ ... }} as its own template code; issues never need it, so take any stray braces apart.
content = content.replace("{{", "{ {").replace("}}", "} }")
plain = plain.replace("{{", "{ {").replace("}}", "} }")

if os.environ.get("EMAIL_HTML_OUT"):
    page = TEMPLATE_FILE.read_text().replace('{{ template "content" . }}', content)
    page = re.sub(r"\{\{[^}]*\}\}", lambda mm: "Chai Weekly No. " + issue if "Subject" in mm.group(0) else ("#" if "URL" in mm.group(0) else ""), page)
    pathlib.Path(os.environ["EMAIL_HTML_OUT"]).write_text(page)
    print("Email preview saved:", os.environ["EMAIL_HTML_OUT"], f"({len(page.encode()) // 1024} KB)")
if os.environ.get("LISTMONK_DRY_RUN"):
    sys.exit(0)

base = os.environ["LISTMONK_URL"].rstrip("/")
auth = {"Authorization": f"token {os.environ['LISTMONK_API_USER'].strip()}:{os.environ['LISTMONK_API_TOKEN'].strip()}",
        "Content-Type": "application/json"}


def api(method, url_path, payload=None):
    req = urllib.request.Request(f"{base}{url_path}", data=json.dumps(payload).encode() if payload is not None else None,
                                 headers=auth, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("data")


def sync_template():
    """Copy tools/email/listmonk-template.html into listmonk and return its id (None if the API user may not)."""
    tpl = {"name": TEMPLATE_NAME, "type": "campaign", "subject": "", "body": TEMPLATE_FILE.read_text()}
    try:
        found = [t for t in (api("GET", "/api/templates") or []) if t.get("name") == TEMPLATE_NAME]
        if found:
            api("PUT", f"/api/templates/{found[0]['id']}", tpl)
            return found[0]["id"]
        return api("POST", "/api/templates", tpl)["id"]
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print("::warning::The listmonk API user may not manage templates, so this draft uses listmonk's plain template. "
                  "Fix: listmonk > Users > User roles > Drafts > tick templates (get and manage).")
            return None
        raise


payload = {
    "name": f"Chai Weekly No. {issue}",
    "subject": f"Chai Weekly No. {issue}: {title}",
    "lists": [int(x) for x in os.environ["LISTMONK_LIST_ID"].replace(" ", "").split(",") if x],
    "type": "regular",
    "content_type": "html",
    "body": content,
    "altbody": plain,
    "messenger": "email",
    "tags": ["issue"],
}
template_id = sync_template()
if template_id:
    payload["template_id"] = template_id
# Always name the sender, so inboxes show "Chai Weekly" and not the mailbox name ("newsletter").
payload["from_email"] = os.environ.get("LISTMONK_FROM") or "Chai Weekly <newsletter@chaiweekly.co.ke>"

WELCOME_NAME = "Chai Weekly welcome"


def welcome_body():
    """The whole welcome email: the newspaper frame, a short welcome note, then this issue."""
    note = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{BOX}" style="background:{BOX}; border-top:2px solid {ACCENT}; margin:14px 0 6px;">'
            f'<tr><td style="padding:14px 18px; font-family:{SANS}; font-size:15px; line-height:1.55; color:{INK};">'
            f'<b style="font-family:{DISPLAY}; font-size:20px;">Welcome to Chai Weekly.</b><br>'
            f'Thank you for subscribing. Here is the latest edition, so you don\'t have to wait for Wednesday. '
            f'The next one comes to this inbox next Wednesday, free.</td></tr></table>')
    body_ = TEMPLATE_FILE.read_text()
    body_ = body_.replace('{{ template "content" . }}', note + content)
    body_ = body_.replace("{{ .Campaign.Subject }}", "Welcome to Chai Weekly")
    body_ = body_.replace("{{ MessageURL }}", esc(utm(web)))
    # A one-off welcome has no campaign, so listmonk offers no unsubscribe link here; say how instead.
    body_ = re.sub(r'<a href="\{\{ UnsubscribeURL \}\}"[^>]*>Unsubscribe</a>',
                   "To stop, reply to this email or use Unsubscribe in any weekly edition", body_)
    return body_.replace("{{ TrackView }}", "")


def sync_welcome():
    """Put this issue into the transactional template that tools/welcome.py sends to new subscribers."""
    tpl = {"name": WELCOME_NAME, "type": "tx", "subject": f"Welcome to Chai Weekly: No. {issue}, {title}", "body": welcome_body()}
    try:
        found = [t for t in (api("GET", "/api/templates") or []) if t.get("name") == WELCOME_NAME]
        if found:
            api("PUT", f"/api/templates/{found[0]['id']}", tpl)
        else:
            found = [api("POST", "/api/templates", tpl)]
        print(f"Welcome email now carries issue No. {issue} (template {found[0]['id']}).")
    except urllib.error.HTTPError as e:
        print(f"::warning::Could not update the welcome email (listmonk said {e.code}: {e.read()[:300]!r}). "
              "If it says 403: listmonk > Users > User roles > Drafts > tick templates (get and manage).")


cid = os.environ.get("LISTMONK_CAMPAIGN_ID", "").strip()
data = api("PUT", f"/api/campaigns/{int(cid)}", payload) if cid else api("POST", "/api/campaigns", payload)
data = data or {}
new_id = data.get("id", cid)
print(f"listmonk campaign {'updated' if cid else 'created'}: {base}/admin/campaigns/{new_id} (status: {data.get('status')})")

if os.environ.get("LISTMONK_WELCOME"):
    sync_welcome()

# Sending: only for a campaign made just now from a merge, and only when the workflow asks for it.
# A person can still pause or cancel it in listmonk before the time comes.
wait = os.environ.get("LISTMONK_AUTOSEND_MINUTES", "").strip()
if wait and not cid and new_id:
    import datetime
    try:
        if int(wait) <= 0:
            api("PUT", f"/api/campaigns/{new_id}/status", {"status": "running"})
            print("Sending now.")
        else:
            when = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=int(wait))).replace(microsecond=0)
            api("PUT", f"/api/campaigns/{new_id}", dict(payload, send_at=when.isoformat().replace("+00:00", "Z")))
            api("PUT", f"/api/campaigns/{new_id}/status", {"status": "scheduled"})
            print(f"Scheduled to send at {when:%H:%M} UTC ({wait} minutes from now). To stop it: pause it in listmonk > Campaigns.")
    except urllib.error.HTTPError as e:
        print(f"::warning::Left as a draft: listmonk would not let the API user send ({e.code}). Press Start in listmonk, "
              "or tick campaigns (send) for the Drafts role in listmonk > Users > User roles.")
