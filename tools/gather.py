#!/usr/bin/env python3
"""Collect this week's tea news from the RSS feeds in feeds.txt.

Writes sources/YYYY-MM-DD.md: a deduplicated, sectioned list of headlines
with links, ready to paste into Claude with DRAFT_PROMPT.md.
Standard library only, so it runs anywhere with Python 3.8+.
"""
import datetime as dt
import email.utils
import html.parser
import pathlib
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def read_feeds():
    for line in (HERE / "feeds.txt").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            section, url = (p.strip() for p in line.split("|", 1))
            yield section, url


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ChaiWeekly/1.0 (hobby newsletter)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return ET.fromstring(r.read())


def items(root):
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        source = (it.findtext("source") or "").strip()
        when = it.findtext("pubDate")
        try:
            date = email.utils.parsedate_to_datetime(when) if when else None
        except (TypeError, ValueError):
            date = None
        yield title, link, source, date


class LinkParser(html.parser.HTMLParser):
    """Collects (href, link text) pairs from an HTML page, in page order."""

    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None


def read_reports():
    year = str(dt.date.today().year)
    for line in (HERE / "reports.txt").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            market, url, pattern = (p.strip() for p in (line + "||").split("|", 2)[:3])
            pattern = pattern.rstrip("|").strip()
            yield market, url.replace("{year}", year), pattern


def latest_reports(url, pattern, keep=2):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ChaiWeekly hobby newsletter)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    parser = LinkParser()
    parser.feed(page)
    found, seen = [], set()
    for href, text in parser.links:
        full = urllib.parse.urljoin(url, href)
        if full not in seen and re.search(pattern, f"{full} {text}"):
            seen.add(full)
            name = urllib.parse.unquote(full.rsplit("/", 1)[-1])
            label = name if re.search(r"\.(pdf|docx?|xlsx?)$", name, re.I) or not text else text
            found.append((" ".join(label.split()), urllib.parse.quote(full, safe=":/?&=#%")))
    return found[:keep]  # listing pages put the newest report first


def report_lines():
    out = ["\n## Auction reports\n"]
    for market, url, pattern in read_reports():
        if not pattern:
            out.append(f"- **{market}**: check by hand <{url}>")
            continue
        try:
            found = latest_reports(url, pattern)
        except Exception as e:
            print(f"! skipped {url}: {e}", file=sys.stderr)
            found = []
        if not found:
            out.append(f"- **{market}**: no report link found, check by hand <{url}>")
        for text, link in found:
            out.append(f"- **{market}**: {text} <{link}>")
    return out


def main():
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)
    seen, by_section = set(), {}
    for section, url in read_feeds():
        try:
            root = fetch(url)
        except Exception as e:  # one bad feed shouldn't stop the run
            print(f"! skipped {url}: {e}", file=sys.stderr)
            continue
        for title, link, source, date in items(root):
            key = title.lower().rsplit(" - ", 1)[0]
            if not title or key in seen or (date and date < cutoff):
                continue
            seen.add(key)
            by_section.setdefault(section, []).append((date, title, link, source))

    today = dt.date.today().isoformat()
    out = [f"# Sources gathered {today} (last {DAYS} days)\n"]
    for section, rows in by_section.items():
        out.append(f"\n## {section}\n")
        for date, title, link, source in sorted(rows, key=lambda r: r[0] or cutoff, reverse=True):
            d = date.strftime("%d %b") if date else "?"
            out.append(f"- {d} · {title} ({source}) <{link}>")
    out += report_lines()
    path = ROOT / "sources" / f"{today}.md"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(out) + "\n")
    total = sum(len(r) for r in by_section.values())
    print(f"Wrote {total} items to {path}")


if __name__ == "__main__":
    main()
