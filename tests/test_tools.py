"""Checks for the collector and email scripts. Run: python3 -m unittest discover -s tests
No network: every web call is replaced with a fake answer."""
import datetime as dt
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def load(name, argv=None):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    with mock.patch.object(sys, "argv", argv or [name]):
        spec.loader.exec_module(mod)
    return mod


def rss(*items):
    body = "".join(f"<item><title>{t}</title><link>https://x/{i}</link><pubDate>{d}</pubDate></item>" for i, (t, d) in enumerate(items))
    return ET.fromstring(f"<rss><channel>{body}</channel></rss>")


class Gather(unittest.TestCase):
    def setUp(self):
        self.g = load("gather")
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.g.ROOT = self.tmp
        self.g.report_lines = lambda: ["\n## Auction reports\n"]
        self.recent = email_date(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))

    def run_with(self, feeds, fetch):
        with mock.patch.object(self.g, "read_feeds", lambda: iter(feeds)), mock.patch.object(self.g, "fetch", fetch):
            self.g.main()
        return (self.tmp / "sources" / f"{dt.date.today().isoformat()}.md")

    def test_date_without_timezone_does_not_crash(self):
        naive = self.recent.replace("+0000", "-0000")
        out = self.run_with([("kenya", "u")], lambda u: rss(("Tea prices rise", naive)))
        self.assertIn("Tea prices rise", out.read_text())

    def test_one_dead_feed_does_not_stop_the_rest(self):
        def fetch(u):
            if u == "dead":
                raise OSError("timeout")
            return rss(("KTDA bonus", self.recent))
        out = self.run_with([("kenya", "dead"), ("kenya", "ok")], fetch)
        self.assertIn("KTDA bonus", out.read_text())

    def test_total_outage_keeps_existing_file_and_fails(self):
        path = self.tmp / "sources" / f"{dt.date.today().isoformat()}.md"
        path.parent.mkdir()
        path.write_text("good file")
        with self.assertRaises(SystemExit) as e:
            self.run_with([("kenya", "u")], lambda u: (_ for _ in ()).throw(OSError("blocked")))
        self.assertEqual(e.exception.code, 3)
        self.assertEqual(path.read_text(), "good file")

    def test_total_outage_on_first_run_writes_honest_note_and_fails(self):
        with self.assertRaises(SystemExit) as e:
            out = self.run_with([("kenya", "u")], lambda u: (_ for _ in ()).throw(OSError("blocked")))
        self.assertEqual(e.exception.code, 1)
        text = (self.tmp / "sources" / f"{dt.date.today().isoformat()}.md").read_text()
        self.assertIn("No news could be fetched", text)
        self.assertIn("## Auction reports", text)

    def test_feeds_line_without_bar_is_skipped(self):
        feeds = TOOLS / "feeds.txt"
        with mock.patch.object(self.g, "HERE", self.tmp):
            (self.tmp / "feeds.txt").write_text("# comment\nnot a feed line\nkenya | https://a\n")
            self.assertEqual(list(self.g.read_feeds()), [("kenya", "https://a")])
        self.assertTrue(feeds.exists())


def email_date(d):
    return d.strftime("%a, %d %b %Y %H:%M:%S +0000")


class Weather(unittest.TestCase):
    def test_missing_values_do_not_break_the_table(self):
        w = load("weather")
        days = [f"2026-11-{i:02d}" for i in range(11, 25)]
        d = {"time": days, "precipitation_sum": [1.0] * 13 + [None], "temperature_2m_max": [24.0] * 14,
             "temperature_2m_min": [12.0] * 8 + [None] + [7.5] * 5}
        s = w.summarise(d)
        self.assertEqual(s["min_night"], 7.5)
        self.assertIn("Cold nights", s["flags"])
        self.assertEqual(len(s["days"]), 7)

    def test_all_missing_temperatures(self):
        w = load("weather")
        d = {"time": [str(i) for i in range(14)], "precipitation_sum": [0.0] * 14,
             "temperature_2m_max": [None] * 14, "temperature_2m_min": [None] * 14}
        s = w.summarise(d)
        self.assertIsNone(s["min_night"])
        self.assertIn("Dry week", s["flags"])


class EattaCsv(unittest.TestCase):
    def setUp(self):
        self.e = load("eatta_csv")
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.e.OUT = self.tmp / "sales.csv"

    def sale(self, n, price):
        return {"saleNumber": n, "auctionDate": "2026-11-17", "averagePriceUsd": price, "soldKg": 7000000}

    def run_main(self, year_data, when):
        class FakeDT(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return when
        with mock.patch.object(self.e, "fetch", lambda y: year_data.get(y, {"ok": True, "year": y, "sales": []})), \
             mock.patch.object(self.e, "datetime", FakeDT), mock.patch.object(sys, "argv", ["eatta_csv"]):
            self.e.main()
        return self.e.OUT.read_text().splitlines()

    def test_january_keeps_december_revisions(self):
        jan = dt.datetime(2027, 1, 5, 3, tzinfo=dt.timezone.utc)
        lines = self.run_main({2026: {"ok": True, "year": 2026, "sales": [self.sale(52, 2.4)]}}, jan)
        self.assertTrue(any(l.startswith("2026,52,") for l in lines))

    def test_leading_zero_sale_numbers_do_not_duplicate(self):
        nov = dt.datetime(2026, 11, 18, 3, tzinfo=dt.timezone.utc)
        self.run_main({2026: {"ok": True, "year": 2026, "sales": [self.sale(47, 2.3)]}}, nov)
        lines = self.run_main({2026: {"ok": True, "year": 2026, "sales": [self.sale("047", 2.31)]}}, nov)
        rows = [l for l in lines if l.startswith("2026,47,")]
        self.assertEqual(len(rows), 1)
        self.assertIn("2.31", rows[0])

    def test_no_sales_at_all_fails(self):
        nov = dt.datetime(2026, 11, 18, 3, tzinfo=dt.timezone.utc)
        with self.assertRaises(SystemExit):
            self.run_main({}, nov)


class Buttondown(unittest.TestCase):
    def test_site_links_become_full_addresses(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        post = tmp / "2026-11-18-issue-003.md"
        post.write_text(textwrap.dedent("""\
            ---
            title: "Test issue"
            issue: 3
            deck: "Deck"
            ---
            See the [Auction analysis]({{ '/auctions/' | relative_url }}) and [weather]({{ "/weather/" | relative_url }}).

            {% include ad.html slot="issue" %}
            """))
        out = tmp / "payload.json"
        (tmp / "sitecustomize.py").write_text(textwrap.dedent(f"""\
            import io, json, urllib.request
            def fake(req, timeout=None):
                open({str(out)!r}, "w").write(req.data.decode())
                return io.BytesIO(b'{{"id": "test"}}')
            urllib.request.urlopen = fake
            """))
        env = {**os.environ, "PYTHONPATH": str(tmp), "SITE_URL": "https://example.org/chai-weekly", "BUTTONDOWN_API_KEY": "fake"}
        subprocess.run([sys.executable, str(TOOLS / "to_buttondown.py"), str(post)], cwd=ROOT, env=env, check=True, capture_output=True)
        body = json.loads(out.read_text())["body"]
        self.assertIn("(https://example.org/chai-weekly/auctions/)", body)
        self.assertIn("(https://example.org/chai-weekly/weather/)", body)
        self.assertNotIn("{{", body)
        self.assertNotIn("{%", body)
        self.assertEqual(json.loads(out.read_text())["status"], "draft")


if __name__ == "__main__":
    unittest.main()
