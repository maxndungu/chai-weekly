"""Sign-up for the detailed auction statistics (name, email, company, role), on the VPS.

The site form posts to https://list.chaiweekly.co.ke/data-signup. listmonk's own public form only takes
an email and a name, so this small helper adds the reader to the "Auction data" list through the listmonk
API with their company and role saved on their record (attributes data_company, data_role), then sends them
back to the site. The list is double opt-in: listmonk emails them a confirmation link.
Standard library only. Settings come from the environment (see docker-compose.yml and SETUP.md):
  LISTMONK_URL        http://chai-listmonk:9000 (inside Docker)
  LISTMONK_API_USER   API user with subscribers get+manage (the "drafts" user works)
  LISTMONK_API_TOKEN  its token
  DATA_LIST_ID        number of the "Auction data" list
  NEWS_LIST_ID        number of the weekly newsletter list (for the "also send me the newsletter" box)
  SITE_URL            https://chaiweekly.co.ke (where readers may be sent back to)
"""
import http.server, json, os, re, sys, urllib.error, urllib.parse, urllib.request

ROLES = {"grower", "factory", "broker", "buyer", "warehouse", "researcher", "other"}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def env(name, default=""):
    return os.environ.get(name, default).strip()


def api(method, path, body=None):
    req = urllib.request.Request(env("LISTMONK_URL").rstrip("/") + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"token {env('LISTMONK_API_USER')}:{env('LISTMONK_API_TOKEN')}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read() or b"{}")


def clean(value, limit):
    return re.sub(r"\s+", " ", value or "").strip()[:limit]


def sign_up(form):
    """Adds the reader. Returns "ok", "bad" (form not filled in properly) or "error" (listmonk failed)."""
    if form.get("nonce"):  # hidden spam trap
        return "ok"
    email = clean(form.get("email"), 200).lower()
    name, company = clean(form.get("name"), 120), clean(form.get("company"), 160)
    role = form.get("role", "") if form.get("role", "") in ROLES else "other"
    if not EMAIL.match(email) or not name or not company:
        return "bad"
    lists = [int(env("DATA_LIST_ID"))]
    if form.get("newsletter") and env("NEWS_LIST_ID"):
        lists.append(int(env("NEWS_LIST_ID")))
    attribs = {"data_company": company, "data_role": role, "data_signup": "auction-stats"}
    try:
        try:
            api("POST", "/api/subscribers", {"email": email, "name": name, "status": "enabled", "lists": lists,
                                             "attribs": attribs, "preconfirm_subscriptions": False})
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code != 409:  # 409: already on a list (e.g. the newsletter); add them to this one too
                raise
        q = urllib.parse.quote(f"subscribers.email = '{email.replace(chr(39), '')}'")
        found = api("GET", f"/api/subscribers?per_page=1&query={q}")["data"]["results"]
        if not found:
            return "error"
        s = found[0]
        have = [l["id"] for l in s.get("lists", []) if l.get("subscription_status") != "unsubscribed"]
        api("PUT", f"/api/subscribers/{s['id']}", {
            "email": s["email"], "name": s.get("name") or name, "status": s.get("status", "enabled"),
            "lists": sorted(set(have + lists)), "attribs": {**(s.get("attribs") or {}), **attribs},
            "preconfirm_subscriptions": False})
        new = [l for l in lists if l not in have]
        if new:
            api("POST", f"/api/subscribers/{s['id']}/optin", {})
        return "ok"
    except Exception as e:  # never show the reader a server error page; log and send them back
        print("listmonk failed:", repr(e), file=sys.stderr, flush=True)
        return "error"


def back_to(next_url, result):
    site = env("SITE_URL", "https://chaiweekly.co.ke").rstrip("/") + "/"
    if not next_url.startswith(site):
        next_url = site
    return next_url + ("&" if "?" in next_url else "?") + "signup=" + result


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if urllib.parse.urlparse(self.path).path.rstrip("/") != "/data-signup":
            return self.send_error(404)
        size = min(int(self.headers.get("Content-Length") or 0), 8192)
        form = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(size).decode("utf-8", "replace")).items()}
        result = sign_up(form)
        print("sign-up:", result, flush=True)  # no names or emails in the log
        self.send_response(303)
        self.send_header("Location", back_to(form.get("next", ""), result))
        self.end_headers()

    def do_GET(self):
        self.send_response(303)
        self.send_header("Location", env("SITE_URL", "https://chaiweekly.co.ke"))
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
