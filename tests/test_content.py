"""Checks the magazine's content files (stdlib only, no internet):
issue front matter (stories, categories, cover, images), the Colombo and Chittagong price files,
and the photo library. Run: python3 -m unittest discover -s tests"""
import csv
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "_data"
POSTS = sorted((ROOT / "_posts").glob("*.md"))


def front(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    return m.group(1), m.group(2)


def flow_map(line):
    """Reads a one-line YAML flow mapping such as { section: "Markets", anchor: "x" }."""
    return dict(re.findall(r'(\w+):\s*"((?:[^"\\]|\\.)*)"', line))


def stories(fm):
    block = re.search(r"^stories:[ \t]*\n((?:[ \t]+- \{.*\}[ \t]*\n)+)", fm + "\n", re.M)
    return [flow_map(l) for l in block.group(1).splitlines() if l.strip()] if block else []


def categories():
    text = (DATA / "categories.yml").read_text(encoding="utf-8")
    ids = re.findall(r"^- id: (\w+)", text, re.M)
    sections = {}
    for cid, secs in zip(ids, re.findall(r"^\s+sections: \[(.*)\]", text, re.M)):
        for s in secs.split(","):
            sections[s.strip()] = cid
    return ids, sections


def photo_ids():
    text = (DATA / "photos.yml").read_text(encoding="utf-8")
    return re.findall(r"^- id: ([\w-]+)", text, re.M), text


def slug(heading):
    """kramdown's automatic heading id."""
    s = heading.strip().lower()
    s = re.sub(r"[^a-z0-9 \-]", "", s)
    return s.replace(" ", "-")


class Issues(unittest.TestCase):
    def test_every_story_has_a_category(self):
        ids, sections = categories()
        for p in POSTS:
            fm, _ = front(p)
            for s in stories(fm):
                if s.get("category"):
                    self.assertIn(s["category"], ids, f"{p.name}: unknown category {s['category']!r}")
                else:
                    self.assertIn(s.get("section"), sections, f"{p.name}: section {s.get('section')!r} has no category in _data/categories.yml")

    def test_story_anchors_and_cover_match_headings(self):
        for p in POSTS:
            fm, body = front(p)
            heads = {slug(h) for h in re.findall(r"^## (.+)$", body, re.M)}
            anchors = [s["anchor"] for s in stories(fm)]
            for a in anchors:
                self.assertIn(a, heads, f"{p.name}: story anchor {a!r} has no matching ## heading")
            cover = re.search(r"^cover:\s*\"?([\w-]+)", fm, re.M)
            if cover:
                self.assertIn(cover.group(1), anchors, f"{p.name}: cover {cover.group(1)!r} is not one of the stories' anchors")

    def test_images_come_from_the_photo_library(self):
        ids, _ = photo_ids()
        for p in POSTS:
            fm, body = front(p)
            for img in re.findall(r"^image:\s*\"?([\w-]+)", fm, re.M) + re.findall(r'image:\s*"([\w-]+)"', fm) + re.findall(r'figure\.html photo="([\w-]+)"', body):
                self.assertIn(img, ids, f"{p.name}: image {img!r} is not in _data/photos.yml")

    def test_reader_slugs(self):
        self.assertEqual(slug("Shamba tip: fertilizer and wet weather"), "shamba-tip-fertilizer-and-wet-weather")
        self.assertEqual(slug("Tea culture: the chai that isn't \"tea\""), "tea-culture-the-chai-that-isnt-tea")


class PhotoLibrary(unittest.TestCase):
    def test_every_photo_exists_and_is_credited(self):
        ids, text = photo_ids()
        entries = re.split(r"^- id: ", text, flags=re.M)[1:]
        for e in entries:
            pid = e.split("\n", 1)[0].strip()
            f = re.search(r"^\s+file:\s*\"?([^\"\n]+)", e, re.M)
            self.assertTrue(f and (ROOT / f.group(1).strip()).exists(), f"photo {pid}: file missing")
            for key in ("alt", "credit"):
                self.assertRegex(e, rf"(?m)^\s+{key}:\s*\S", f"photo {pid}: no {key}")
        self.assertEqual(len(ids), len(set(ids)), "two photos share an id")


class BrokerPrices(unittest.TestCase):
    FILES = {
        "colombo_sales.csv": ["sale", "sale_dates", "avg_local", "currency", "avg_usd_kg", "change", "sold", "note", "source", "source_url", "reported"],
        "chittagong_sales.csv": ["sale", "sale_date", "avg_local", "currency", "change", "sold_pct", "note", "source", "source_url", "reported"],
    }

    def test_columns_sources_and_numbers(self):
        for name, cols in self.FILES.items():
            with open(DATA / name, encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
                self.assertEqual(list(rows[0].keys()) if rows else cols, cols, f"{name}: columns changed")
            last = 0
            for i, r in enumerate(rows, 2):
                self.assertRegex(r["sale"], r"^\d+$", f"{name} line {i}: sale number")
                self.assertGreater(int(r["sale"]), last, f"{name} line {i}: sales must be in order, one line each")
                last = int(r["sale"])
                self.assertTrue(r["source"].strip(), f"{name} line {i}: no source")
                self.assertRegex(r["source_url"], r"^https?://", f"{name} line {i}: source_url must be a link")
                self.assertRegex(r["reported"], r"^\d{4}-\d{2}-\d{2}$", f"{name} line {i}: reported must be YYYY-MM-DD")
                price = r.get("avg_usd_kg") or r["avg_local"]
                self.assertRegex(price, r"^\d+(\.\d+)?$", f"{name} line {i}: no price (leave the sale out rather than guess)")
                if r["avg_local"]:
                    self.assertRegex(r["avg_local"], r"^\d+(\.\d+)?$", f"{name} line {i}: avg_local must be a plain number, no commas")
                    self.assertTrue(r["currency"], f"{name} line {i}: avg_local needs a currency")


if __name__ == "__main__":
    unittest.main()
