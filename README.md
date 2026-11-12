# Chai Weekly

A free weekly newsletter about tea (Kenya first, plus world tea news), published as a static Jekyll site that GitHub Pages builds for free.

```
_posts/            one markdown file per issue (YYYY-MM-DD-issue-NNN.md)
_layouts/, _includes/, assets/   site design (signup box is _includes/signup.html)
_config.yml        site name + your Buttondown/Substack setting
tools/feeds.txt    RSS feeds to watch (add or remove lines freely)
tools/reports.txt  weekly auction report pages per market (Mombasa, Colombo, India, Chittagong, ...)
tools/gather.py    collects the last 8 days of headlines into sources/
tools/DRAFT_PROMPT.md   the prompt for Claude to draft each issue
.github/workflows/gather-sources.yml   runs gather.py every Monday
```

## One-time setup (about 15 minutes)

1. **GitHub repo**: create a public repo (e.g. `chai-weekly`) and push this folder to it.
2. **Pages**: repo Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/ (root)`. Your site appears at `https://<you>.github.io/chai-weekly/` within a couple of minutes. Then set `baseurl: "/chai-weekly"` and `url: "https://<you>.github.io"` in `_config.yml`.
3. **Email list**: make a free [Buttondown](https://buttondown.com) account (free up to 100 subscribers, markdown-native) and put your username in `_config.yml` as `buttondown_username`. Or use Substack and set `substack_url` (e.g. `https://chaiweekly.substack.com`). The signup box switches over automatically.
4. **Actions**: the "Gather sources" workflow runs on its own every Monday. You can also run it by hand from the Actions tab.

## Weekly routine (about 15 minutes of your time)

**Automatic (current setup):** at 06:00 Nairobi every Monday the "Gather sources" job collects the news. At about 07:15 a scheduled Claude session drafts the issue by following `tools/AUTODRAFT.md` and opens a pull request titled "Issue #N draft". Review it (read the reviewer notes, check the figures, edit on GitHub if needed) and **merge** to publish. Close the pull request instead to skip a week.

**By hand (fallback):**

1. **Monday**: open `sources/<date>.md` in the repo (the bot added it).
2. **Draft**: paste `tools/DRAFT_PROMPT.md` + the sources file + last week's issue into Claude. Claude returns the full issue.
3. **Review (10 min)**: check every price against its link, read the reviewer notes Claude lists at the end, fix the tone.
4. **Publish**: save it as `_posts/YYYY-MM-DD-issue-NNN.md` (GitHub's "Add file" button works) and commit. The site updates itself.
5. **Send**: paste the same markdown into a new Buttondown email (or Substack post) and send.

## Running locally (optional)

```
python3 tools/gather.py        # needs only Python 3
bundle install && bundle exec jekyll serve   # preview the site, needs Ruby
```

## Mirroring to a paid host (optional)

GitHub stays the source of truth. Every push to `main` also triggers `.github/workflows/mirror-to-host.yml`, which builds the site and uploads it to your host.

1. Add repo secrets (Settings → Secrets and variables → Actions), either:
   - **SSH/rsync** (VPS such as DigitalOcean or Hetzner, or any host with SSH): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH` (e.g. `/var/www/chaiweekly`), `DEPLOY_SSH_KEY` (a private key whose public half is in the server's `authorized_keys`), or
   - **FTP** (cPanel shared hosting such as Truehost, HostPinnacle or Namecheap): `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`, `FTP_PATH` (usually `public_html`).
2. Set `canonical_url` in `_config.yml` to your domain so Google treats it as the main copy and not the GitHub Pages one.
3. Point your domain's DNS at the host as the host instructs.
