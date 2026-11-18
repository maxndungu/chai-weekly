"""Checks a built site folder (default _site). Run after `bundle exec jekyll build`:
    python3 tests/check_site.py _site
Fails if internal links or #anchors are broken, private folders are published, or share tags are missing."""
import html.parser, pathlib, re, sys, urllib.parse, xml.etree.ElementTree as ET

SITE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
BASE = re.search(r'^baseurl:\s*"?([^"\n]*)', (pathlib.Path(__file__).resolve().parent.parent / "_config.yml").read_text(), re.M).group(1).rstrip("/")
if len(sys.argv) > 2:
    BASE = sys.argv[2].rstrip("/")
problems = []


class Page(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.links, self.ids, self.meta = [], set(), {}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"): self.ids.add(a["id"])
        if tag == "a" and a.get("href"): self.links.append(a["href"])
        if tag in ("img", "script") and a.get("src"): self.links.append(a["src"])
        if tag == "link" and a.get("href") and a.get("rel") == "stylesheet": self.links.append(a["href"])
        if tag == "meta" and (a.get("property") or a.get("name")): self.meta[a.get("property") or a.get("name")] = a.get("content", "")


pages = {}
for f in SITE.rglob("*.html"):
    p = Page(); p.feed(f.read_text(encoding="utf-8")); pages[f] = p

for leak in ("submissions", "tools", "tests", "sources"):
    if (SITE / leak).exists():
        problems.append(f"private folder published: /{leak}/")


def target(path):
    if BASE and not path.startswith(BASE):
        return None
    rel = path[len(BASE):]
    t = SITE / rel.lstrip("/")
    return t / "index.html" if (t.is_dir() or rel.endswith("/")) else t


for f, p in pages.items():
    name = f.relative_to(SITE)
    if "og:title" not in p.meta or "og:description" not in p.meta:
        problems.append(f"{name}: no share preview tags")
    for link in p.links:
        u = urllib.parse.urlparse(link)
        if u.scheme or link.startswith("//") or link.startswith("mailto:"):
            continue
        if not u.path:  # same-page anchor
            if u.fragment and u.fragment not in p.ids:
                problems.append(f"{name}: #{u.fragment} has no matching heading")
            continue
        t = target(urllib.parse.unquote(u.path))
        if t is None:
            problems.append(f"{name}: link {link} is missing the site's base path {BASE or '/'}")
        elif not t.exists():
            problems.append(f"{name}: broken link {link}")
        elif u.fragment and t in pages and u.fragment not in pages[t].ids:
            problems.append(f"{name}: {link} points at a heading that doesn't exist")

feed = SITE / "feed.xml"
try:
    ET.parse(feed)
    if re.search(r'href=&quot;/', feed.read_text()):
        problems.append("feed.xml: issue text has links without the site address")
except ET.ParseError as e:
    problems.append(f"feed.xml is not valid XML: {e}")

print(f"Checked {len(pages)} pages.")
for x in sorted(set(problems))[:50]:
    print("PROBLEM:", x)
sys.exit(1 if problems else 0)
