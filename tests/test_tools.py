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


class Listmonk(unittest.TestCase):
    POST = textwrap.dedent("""\
        ---
        title: "Test issue"
        issue: 3
        deck: "Deck"
        snapshot:
          - { label: "Mombasa (Sale 47)", value: "$2.39/kg", note: "up 5c" }
        stories:
          - { section: "Markets", anchor: "the-auction", headline: "Best price" }
        ---
        See the [Auction analysis]({{ '/auctions/' | relative_url }}) and [weather]({{ "/weather/" | relative_url }}). Stray {{ braces }}.

        ## The auction

        | Auction | Average |
        |---|---|
        | Mombasa | US$2.39/kg |
        {: .auction-table}

        *Sources: [EATTA](https://eatta.co.ke/statistics)*

        {% include ad.html slot="issue" %}
        """)

    def run_tool(self, extra_env=None, templates=b'{"data": []}', template_status=200):
        tmp = pathlib.Path(tempfile.mkdtemp())
        post = tmp / "2026-11-18-issue-003.md"
        post.write_text(self.POST)
        out = tmp / "calls.json"
        (tmp / "sitecustomize.py").write_text(textwrap.dedent(f"""\
            import io, json, urllib.request, urllib.error
            calls = []
            def fake(req, timeout=None):
                calls.append({{"method": req.get_method(), "url": req.full_url, "auth": req.get_header("Authorization"),
                              "payload": json.loads(req.data) if req.data else None}})
                open({str(out)!r}, "w").write(json.dumps(calls))
                if "/api/templates" in req.full_url:
                    if {template_status} != 200:
                        raise urllib.error.HTTPError(req.full_url, {template_status}, "no", {{}}, io.BytesIO(b""))
                    if req.get_method() == "GET":
                        return io.BytesIO({templates!r})
                    return io.BytesIO(b'{{"data": {{"id": 9}}}}')
                return io.BytesIO(b'{{"data": {{"id": 7, "status": "draft"}}}}')
            urllib.request.urlopen = fake
            """))
        env = {**os.environ, "PYTHONPATH": str(tmp), "SITE_URL": "https://example.org/chai-weekly", "LISTMONK_URL": "https://list.example.org/",
               "LISTMONK_LIST_ID": "3", "LISTMONK_API_USER": "drafts", "LISTMONK_API_TOKEN": "fake", **(extra_env or {})}
        r = subprocess.run([sys.executable, str(TOOLS / "to_listmonk.py"), str(post)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        return json.loads(out.read_text()), r.stdout

    def test_draft_is_styled_html_with_full_links(self):
        calls, stdout = self.run_tool()
        camp = calls[-1]
        self.assertEqual((camp["method"], camp["url"]), ("POST", "https://list.example.org/api/campaigns"))
        self.assertEqual(camp["auth"], "token drafts:fake")
        sent = camp["payload"]
        body = sent["body"]
        self.assertEqual(sent["content_type"], "html")
        self.assertEqual(sent["lists"], [3])
        self.assertEqual(sent["template_id"], 9)
        self.assertEqual(sent["from_email"], "Chai Weekly <newsletter@chaiweekly.co.ke>")
        self.assertNotIn("status", sent)  # listmonk creates campaigns as drafts; we never ask it to send
        self.assertIn("https://example.org/chai-weekly/auctions/?utm_source=newsletter", body)
        self.assertIn("https://example.org/chai-weekly/weather/?utm_source=newsletter", body)
        self.assertIn("issues/2026/11/18/issue-003/?utm_source=newsletter&amp;utm_medium=email&amp;utm_campaign=issue-3#the-auction", body)
        self.assertIn("Chai Weekly</a>", body)            # nameplate
        self.assertIn("In this edition", body)            # contents box
        self.assertIn("Mombasa (Sale 47)", body)          # ticker
        # Short email: the stories stay on the web, the email links to them.
        self.assertIn("Read the full edition", body)
        self.assertNotIn("border-collapse", body)
        self.assertNotIn("<h2", body)
        self.assertIn("Markets: Best price", sent["altbody"])
        self.assertIn("Read the full edition: https://example.org/chai-weekly/issues/2026/11/18/issue-003/", sent["altbody"])
        self.assertNotIn("{{", body + sent["altbody"])
        self.assertNotIn("{%", body + sent["altbody"])
        self.assertIn("/admin/campaigns/7", stdout)

    def test_template_is_kept_in_step_with_the_repo(self):
        calls, _ = self.run_tool()
        self.assertEqual([c["method"] for c in calls if "/api/templates" in c["url"]], ["GET", "POST"])
        tpl = calls[1]["payload"]
        self.assertIn('{{ template "content" . }}', tpl["body"])
        self.assertIn("{{ UnsubscribeURL }}", tpl["body"])
        calls, _ = self.run_tool(templates=b'{"data": [{"id": 4, "name": "Chai Weekly newspaper"}]}')
        self.assertEqual(calls[1]["method"] + " " + calls[1]["url"], "PUT https://list.example.org/api/templates/4")
        self.assertEqual(calls[-1]["payload"]["template_id"], 4)

    def test_no_template_permission_still_makes_draft(self):
        calls, _ = self.run_tool(template_status=403)
        self.assertNotIn("template_id", calls[-1]["payload"])
        self.assertEqual(calls[-1]["method"], "POST")

    def test_redo_updates_existing_draft(self):
        calls, stdout = self.run_tool({"LISTMONK_CAMPAIGN_ID": "2"})
        self.assertEqual((calls[-1]["method"], calls[-1]["url"]), ("PUT", "https://list.example.org/api/campaigns/2"))
        self.assertIn("updated", stdout)

    def test_merge_schedules_the_send(self):
        calls, stdout = self.run_tool({"LISTMONK_AUTOSEND_MINUTES": "15"})
        sched = [c for c in calls if "/api/campaigns/7" in c["url"]]
        self.assertEqual([(c["method"], c["url"].rsplit("/api", 1)[1]) for c in sched],
                         [("PUT", "/campaigns/7"), ("PUT", "/campaigns/7/status")])
        self.assertRegex(sched[0]["payload"]["send_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(sched[1]["payload"], {"status": "scheduled"})
        self.assertIn("Scheduled to send", stdout)

    def test_redo_by_hand_never_sends(self):
        calls, _ = self.run_tool({"LISTMONK_CAMPAIGN_ID": "2", "LISTMONK_AUTOSEND_MINUTES": "15"})
        self.assertFalse([c for c in calls if c["url"].endswith("/status")])
        calls, _ = self.run_tool({"LISTMONK_AUTOSEND_MINUTES": ""})
        self.assertFalse([c for c in calls if c["url"].endswith("/status")])

    def test_welcome_email_carries_the_issue(self):
        calls, stdout = self.run_tool({"LISTMONK_WELCOME": "1"})
        tx = [c for c in calls if "/api/templates" in c["url"] and c["payload"] and c["payload"].get("type") == "tx"]
        self.assertEqual(len(tx), 1)
        body = tx[0]["payload"]["body"]
        self.assertEqual(tx[0]["payload"]["name"], "Chai Weekly welcome")
        self.assertIn("Welcome to Chai Weekly.", body)
        self.assertIn("In this edition", body)
        self.assertNotIn("UnsubscribeURL", body)   # listmonk refuses it in one-off emails
        self.assertNotIn('template "content"', body)
        self.assertIn("Welcome email now carries issue No. 3", stdout)


class Welcome(unittest.TestCase):
    """New readers get the latest issue once; they are marked before the send so a failure never sends twice."""

    def run_welcome(self, people, tx_status=200, extra_env=None):
        tmp = pathlib.Path(tempfile.mkdtemp())
        out = tmp / "calls.json"
        (tmp / "sitecustomize.py").write_text(textwrap.dedent(f"""\
            import io, json, urllib.request, urllib.error
            calls = []
            def fake(req, timeout=None):
                calls.append({{"method": req.get_method(), "url": req.full_url, "payload": json.loads(req.data) if req.data else None}})
                open({str(out)!r}, "w").write(json.dumps(calls))
                if "/api/templates" in req.full_url:
                    return io.BytesIO(b'{{"data": [{{"id": 5, "name": "Chai Weekly welcome", "type": "tx"}}]}}')
                if "/api/subscribers?" in req.full_url:
                    return io.BytesIO(json.dumps({{"data": {{"results": {people!r}}}}}).encode())
                if "/api/tx" in req.full_url and {tx_status} != 200:
                    raise urllib.error.HTTPError(req.full_url, {tx_status}, "no", {{}}, io.BytesIO(b"denied"))
                return io.BytesIO(b'{{"data": true}}')
            urllib.request.urlopen = fake
            """))
        env = {**os.environ, "PYTHONPATH": str(tmp), "LISTMONK_URL": "https://list.example.org", "LISTMONK_LIST_ID": "3",
               "LISTMONK_API_USER": "drafts", "LISTMONK_API_TOKEN": "fake", "WELCOME_SINCE": "2026-11-26", **(extra_env or {})}
        r = subprocess.run([sys.executable, str(TOOLS / "welcome.py")], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        return (json.loads(out.read_text()) if out.exists() else []), r.stdout

    @staticmethod
    def person(i, joined="2026-11-27T08:00:00Z", **kw):
        return {"id": i, "email": f"r{i}@example.org", "name": f"R{i}", "status": "enabled", "attribs": {"city": "Kericho"},
                "created_at": joined, "lists": [{"id": 3, "subscription_status": "confirmed", "created_at": "2026-11-25T10:00:00Z", "subscription_created_at": joined}], **kw}

    def test_new_reader_is_marked_then_sent(self):
        calls, stdout = self.run_welcome([self.person(1)])
        writes = [(c["method"], c["url"].split("/api")[1]) for c in calls if c["method"] != "GET"]
        self.assertEqual(writes, [("PUT", "/subscribers/1"), ("POST", "/tx")])
        mark = calls[[c["method"] for c in calls].index("PUT")]["payload"]
        self.assertEqual(mark["attribs"]["city"], "Kericho")          # keeps what was there
        self.assertIn("chai_welcomed", mark["attribs"])
        self.assertEqual((mark["lists"], mark["preserve_subscription_status"]), ([3], True))
        tx = [c for c in calls if c["url"].endswith("/api/tx")][0]["payload"]
        self.assertEqual((tx["subscriber_id"], tx["template_id"]), (1, 5))
        self.assertIn("sent to 1", stdout)

    def test_old_welcomed_and_disabled_readers_are_skipped(self):
        people = [self.person(1, joined="2026-11-20T08:00:00Z"),
                  self.person(2, attribs={"chai_welcomed": "2026-11-27"}),
                  self.person(3, status="blocklisted")]
        calls, _ = self.run_welcome(people)
        self.assertFalse([c for c in calls if c["method"] != "GET"])

    def test_failed_send_is_unmarked_for_next_run(self):
        calls, _ = self.run_welcome([self.person(1), self.person(2)], tx_status=403)
        writes = [(c["method"], c["url"].split("/api")[1]) for c in calls if c["method"] != "GET"]
        self.assertEqual(writes, [("PUT", "/subscribers/1"), ("POST", "/tx"), ("PUT", "/subscribers/1")])
        self.assertNotIn("chai_welcomed", calls[-1]["payload"]["attribs"])

    def test_off_when_no_start_date(self):
        calls, stdout = self.run_welcome([self.person(1)], extra_env={"WELCOME_SINCE": ""})
        self.assertEqual(calls, [])
        self.assertIn("off", stdout)


if __name__ == "__main__":
    unittest.main()


class CombrokCheck(unittest.TestCase):
    """The cross-check flags real gaps, calls a gap on a provisional sale expected, and never fails the run."""
    ROWS = [
        {"year": "2026", "sale": "44", "auction_date": "2026-11-02", "avg_usd_kg": "2.33", "sold_kg": "6656373",
         "orthodox_avg_usd_kg": "3.58", "orthodox_sold_kg": "50620"},
        {"year": "2026", "sale": "45", "auction_date": "2026-11-09", "avg_usd_kg": "2.36", "sold_kg": "6843760",
         "orthodox_avg_usd_kg": "", "orthodox_sold_kg": ""},
        {"year": "2026", "sale": "46", "auction_date": "2026-11-16", "avg_usd_kg": "2.34", "sold_kg": "7579307",
         "orthodox_avg_usd_kg": "3.43", "orthodox_sold_kg": "51829"},
    ]
    CTC = [{"year": 2026, "sale": 44, "qty_sold": 6618629, "avg_prc": 2.32},
           {"year": 2026, "sale": 45, "qty_sold": 6658368, "avg_prc": 2.36},
           {"year": 2026, "sale": 46, "qty_sold": 7338014, "avg_prc": 2.34},
           {"year": 2025, "sale": 46, "qty_sold": 1, "avg_prc": 9.99}]
    ORTH = [{"year": 2026, "sale": 44, "qty_sold": 50620, "avg_prc": 3.58}]

    def setUp(self):
        self.c = load("combrok_check")

    def test_flags_gaps_and_marks_provisional(self):
        wed = dt.datetime(2026, 11, 18, 7, 0, tzinfo=self.c.NAIROBI)
        lines, flagged = self.c.compare(self.ROWS, {"ctc": self.CTC, "orthodox": self.ORTH}, now=wed)
        text = "\n".join(lines)
        self.assertEqual(flagged, 2)  # sale 45 and 46 kg; sale 44 is within a cent and 2%
        self.assertNotIn("Sale 44 (all teas)", text)
        self.assertIn("Sale 45 (all teas): sold EATTA 6,843,760 kg vs Combrok 6,658,368 kg", text)
        self.assertIn("**check**", [l for l in lines if l.startswith("- Sale 45")][0])
        self.assertIn("provisional", [l for l in lines if l.startswith("- Sale 46 (all")][0])
        self.assertIn("Sale 46 (orthodox): not in Combrok's figures yet.", text)
        self.assertNotIn("9.99", text)  # other years are ignored

    def test_final_after_friday_noon(self):
        self.assertFalse(self.c.final("2026-11-16", dt.datetime(2026, 11, 20, 11, 59, tzinfo=self.c.NAIROBI)))
        self.assertTrue(self.c.final("2026-11-16", dt.datetime(2026, 11, 20, 12, 0, tzinfo=self.c.NAIROBI)))
        self.assertTrue(self.c.final("2026-11-17", dt.datetime(2026, 11, 20, 12, 0, tzinfo=self.c.NAIROBI)))  # Tuesday sale

    def test_fetch_failure_does_not_fail(self):
        with mock.patch.object(self.c, "fetch", side_effect=OSError("blocked")), \
             mock.patch("sys.stdout", new_callable=__import__("io").StringIO) as out:
            self.c.main()
        self.assertIn("Could not read Combrok's figures", out.getvalue())


class CombrokCsv(unittest.TestCase):
    """Combrok's per-sale figures are added, revised in place and never deleted."""

    def test_merge_adds_revises_and_keeps(self):
        c = load("combrok_csv")
        existing = {("2019", "5"): {"year": "2019", "sale": "5", "ctc_sold_kg": "1", "first_saved": "2026-01-01"}}
        feeds = {"ctc": [{"year": 2026, "sale": 46, "offered_lots": 3365, "sold_lots": 3052, "qty_offered": 8109761,
                          "qty_sold": 7338014, "avg_prc": 2.34}, {"sale": 1}],
                 "orthodox": [{"year": 2026, "sale": 46, "qty_offered": 110239, "qty_sold": 42249, "avg_prc": 3.45}]}
        self.assertEqual(c.merge(existing, feeds, "2026-11-24"), (1, 0))
        row = existing[("2026", "46")]
        self.assertEqual((row["ctc_offered_kg"], row["ctc_sold_kg"], row["ctc_avg_usd_kg"]), ("8109761", "7338014", "2.34"))
        self.assertEqual((row["orthodox_offered_kg"], row["orthodox_offered_lots"]), ("110239", ""))
        feeds["ctc"][0]["qty_sold"] = 7400000
        self.assertEqual(c.merge(existing, feeds, "2026-11-28"), (0, 1))
        self.assertEqual(existing[("2026", "46")]["ctc_sold_kg"], "7400000")
        self.assertEqual(existing[("2026", "46")]["first_saved"], "2026-11-24")
        self.assertIn(("2019", "5"), existing)
