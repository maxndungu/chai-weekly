"""Tests for deploy/datasignup/signup.py (the auction statistics sign-up), with listmonk faked."""
import importlib.util, io, os, pathlib, unittest, urllib.error

spec = importlib.util.spec_from_file_location("signup", pathlib.Path(__file__).parent.parent / "deploy/datasignup/signup.py")
signup = importlib.util.module_from_spec(spec); spec.loader.exec_module(signup)


class FakeListmonk:
    def __init__(self, existing=None):
        self.calls, self.existing = [], existing

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        if method == "POST" and path == "/api/subscribers" and self.existing:
            raise urllib.error.HTTPError(path, 409, "exists", {}, io.BytesIO(b""))
        if method == "GET":
            return {"data": {"results": [self.existing]}}
        return {}


class SignUp(unittest.TestCase):
    def setUp(self):
        os.environ.update(DATA_LIST_ID="7", NEWS_LIST_ID="3", SITE_URL="https://chaiweekly.co.ke")
        self.form = {"name": " Jane  Wanjiru ", "email": "Jane@Example.com", "company": "Kiambu Tea Ltd",
                     "role": "factory", "next": "https://chaiweekly.co.ke/preview2/auctions/"}

    def run_with(self, fake, form):
        signup.api = fake
        return signup.sign_up(form)

    def test_new_reader_joins_data_list_unconfirmed_with_company(self):
        fake = FakeListmonk()
        self.assertEqual(self.run_with(fake, self.form), "ok")
        (method, path, body), = fake.calls
        self.assertEqual((body["email"], body["name"], body["lists"]), ("jane@example.com", "Jane Wanjiru", [7]))
        self.assertEqual(body["attribs"]["data_company"], "Kiambu Tea Ltd")
        self.assertFalse(body["preconfirm_subscriptions"])

    def test_newsletter_box_adds_the_weekly_list(self):
        fake = FakeListmonk()
        self.run_with(fake, {**self.form, "newsletter": "1"})
        self.assertEqual(fake.calls[0][2]["lists"], [7, 3])

    def test_existing_reader_keeps_lists_and_gets_confirmation(self):
        fake = FakeListmonk({"id": 12, "email": "jane@example.com", "name": "Jane", "status": "enabled",
                             "attribs": {"chai_welcomed": "2026-11-27"},
                             "lists": [{"id": 3, "subscription_status": "confirmed"}]})
        self.assertEqual(self.run_with(fake, self.form), "ok")
        put = [c for c in fake.calls if c[0] == "PUT"][0][2]
        self.assertEqual(put["lists"], [3, 7])
        self.assertEqual(put["attribs"]["chai_welcomed"], "2026-11-27")
        self.assertIn(("POST", "/api/subscribers/12/optin", {}), fake.calls)

    def test_missing_company_or_bad_email_is_refused(self):
        fake = FakeListmonk()
        self.assertEqual(self.run_with(fake, {**self.form, "company": ""}), "bad")
        self.assertEqual(self.run_with(fake, {**self.form, "email": "not-an-email"}), "bad")
        self.assertEqual(fake.calls, [])

    def test_spam_trap_adds_nobody(self):
        fake = FakeListmonk()
        self.assertEqual(self.run_with(fake, {**self.form, "nonce": "x"}), "ok")
        self.assertEqual(fake.calls, [])

    def test_only_sends_readers_back_to_our_site(self):
        self.assertEqual(signup.back_to("https://evil.example/", "ok"), "https://chaiweekly.co.ke/?signup=ok")
        self.assertEqual(signup.back_to("https://chaiweekly.co.ke/preview2/auctions/", "bad"),
                         "https://chaiweekly.co.ke/preview2/auctions/?signup=bad")


if __name__ == "__main__":
    unittest.main()
