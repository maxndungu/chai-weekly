# Chai Weekly

A free weekly newsletter about tea (Kenya first, plus world tea news), published as a static Jekyll site that GitHub Pages builds for free.

```
_posts/            one markdown file per issue (YYYY-MM-DD-issue-NNN.md)
_layouts/, _includes/, assets/   site design (signup box is _includes/signup.html)
_config.yml        site name + mailing list settings (listmonk)
tools/feeds.txt    RSS feeds to watch (add or remove lines freely)
tools/reports.txt  weekly auction report pages per market (Mombasa, Colombo, India, Chittagong, ...)
tools/gather.py    collects the last 8 days of headlines into sources/
tools/DRAFT_PROMPT.md   the prompt for Claude to draft each issue
.github/workflows/gather-sources.yml   runs gather.py every Wednesday
```

## One-time setup (about 15 minutes)

1. **GitHub repo**: create a public repo (e.g. `chai-weekly`) and push this folder to it.
2. **Pages**: repo Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/ (root)`. Your site appears at `https://<you>.github.io/chai-weekly/` within a couple of minutes. Then set `baseurl: "/chai-weekly"` and `url: "https://<you>.github.io"` in `_config.yml`.
3. **Email list**: our own list (listmonk) on the VPS. Follow `deploy/listmonk/SETUP.md`, then put the list's UUID and number in `_config.yml` (`listmonk_list_uuid`, `listmonk_list_id`). The signup box switches on automatically.
4. **Actions**: the "Gather sources" workflow runs on its own every Wednesday. You can also run it by hand from the Actions tab.

## Weekly routine (about 15 minutes of your time)

**Automatic (current setup):** early every Wednesday (00:41 Nairobi, with a second try at 05:17 if GitHub has not started the first) the "Gather sources" job collects the news. GitHub can start scheduled jobs hours late, so the draft session starts a news-only run itself if the file is still missing. At about 07:15 a scheduled Claude session drafts the issue by following `tools/AUTODRAFT.md` and opens a pull request titled "Issue #N draft". Review it (read the reviewer notes, check the figures, edit on GitHub if needed) and **merge** to publish. Close the pull request instead to skip a week.

**By hand (fallback):**

1. **Wednesday**: open `sources/<date>.md` in the repo (the bot added it).
2. **Draft**: paste `tools/DRAFT_PROMPT.md` + the sources file + last week's issue into Claude. Claude returns the full issue.
3. **Review (10 min)**: check every price against its link, read the reviewer notes Claude lists at the end, fix the tone.
4. **Publish**: save it as `_posts/YYYY-MM-DD-issue-NNN.md` (GitHub's "Add file" button works) and commit. The site updates itself.
5. **Send**: the merged issue appears as a draft under Campaigns in listmonk. Send yourself a test, then press Start.

## Auction analysis page and price history (_data/)

The site's **Auctions** page (`auctions.html`, at /auctions/) combines two files:

- `_data/mombasa_eatta_sales.csv`: every Mombasa sale from EATTA's statistics page. EATTA only shows the current year, so this file is the long-run weekly history. The auction data (this file and `_data/mombasa_combrok_sales.csv`) updates on the schedule in `.github/workflows/gather-sources.yml` (keep it off the site): the collector adds each new sale, updates any figure EATTA revises (and prints what changed), and never deletes rows. EATTA adds late sales until Friday noon, so the newest sale's figures are provisional until Friday's run saves the final ones. The Wednesday news run does not touch these files. To update them on another day: Actions, "Gather sources", Run workflow, tick "Only update the auction data".
- `_data/worldbank_tea_mombasa_monthly.csv`: monthly Mombasa prices for 1992 to 2008 only (World Bank Pink Sheet "Tea, Mombasa", CC BY 4.0). Frozen: from 2009 on, every chart and table uses our own sale records and EATTA instead (Maxwell's decision, 2026-11-25). Do not add later months.

The page draws its charts and tables from these files and offers no CSV downloads. Prices from 2009 are sale averages from our own records (2009 to 2025) and EATTA (2026 on); 1992 to 2008 are monthly averages, marked "monthly", with one fine-print credit line because that data is CC BY 4.0.

## Reader story submissions (/submit/)

The "Send a story" page has a form (name, contact, location, role, headline, story, link or photo, consent). Submissions are emailed to you through FormSubmit (free, no account):

1. In `_config.yml`, set `story_form_action: "https://formsubmit.co/YOUR-EMAIL"` and push.
2. Send one test story from the site. FormSubmit emails you an activation link; click it.
3. FormSubmit then gives you a random address like `https://formsubmit.co/abc123…`. Put that in `story_form_action` instead, so your email isn't visible in the page.

Until it's set, the form shows "opens very soon" and asks readers to reply to an issue instead. Stories are never published automatically: you decide, and the Wednesday draft can use a story you forward.

## Paid adverts (_data/ads.yml)

Three sponsor slots, all hidden until you switch an ad on, all labelled "Sponsored":

| Slot | Where | Image |
|---|---|---|
| `home` | Front page side column, under the subscribe box (replaces the events list while it runs) | Poster, 600 x 900 px portrait |
| `issue` | Each issue, after the auction prices, and in the email | Banner, 1200 x 400 px, plus one line of text and a link (email apps that block images still show the text) |
| `auctions` | "Prices brought to you by …" line at the top of the Auctions page | None |

To run an ad: put the image in `assets/ads/`, copy the example in `_data/ads.yml`, fill in sponsor, image, link (website or `https://wa.me/254…`), text, start and end dates, and commit. It appears on the start date and disappears after the end date by itself. The email box uses the ad that is live on the issue's date.

## Checks before you merge

Every pull request (including the Wednesday draft) runs the "Checks" job: the collector and email scripts are tested with fake data, the site is built, and every page is checked for broken links and anchors, missing share previews, and private folders (submissions/, sources/, tools/) being published. A green tick means it passed; a red cross means don't merge yet. The Wednesday collector also turns red (and GitHub emails you) if a step fails, but it still saves whatever it collected.

## Link previews on WhatsApp and Facebook

Each page has share tags, so a shared link shows the headline and summary. To add a picture to the preview, put a 1200 x 630 px image in `assets/` and set `share_image: "assets/<file>"` in `_config.yml`.

## Running locally (optional)

```
python3 tools/gather.py        # needs only Python 3
python3 -m unittest discover -s tests   # the script tests (no internet needed)
bundle install && bundle exec jekyll serve   # preview the site, needs Ruby
```

## Own domain (chaiweekly.co.ke)

The site is served at https://chaiweekly.co.ke by GitHub Pages. The `CNAME` file holds the domain, and
`_config.yml` has `url: "https://chaiweekly.co.ke"`, `baseurl: ""` and the same address as `canonical_url`.
DNS (at HostDeal): four A records for `@` to 185.199.108.153, 185.199.109.153, 185.199.110.153 and
185.199.111.153, and a CNAME record for `www` to `maxndungu.github.io`. In the repo's Settings > Pages the
custom domain is `chaiweekly.co.ke` with Enforce HTTPS ticked. Old `maxndungu.github.io/chai-weekly/` links
redirect to the domain automatically. Always link the site's own pages with `relative_url`, never a fixed path.

## Mirroring to a paid host (optional)

GitHub stays the source of truth. Every push to `main` also triggers `.github/workflows/mirror-to-host.yml`, which builds the site and uploads it to your host.

1. Add repo secrets (Settings → Secrets and variables → Actions), either:
   - **SSH/rsync** (VPS such as DigitalOcean or Hetzner, or any host with SSH): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH` (e.g. `/var/www/chaiweekly`), `DEPLOY_SSH_KEY` (a private key whose public half is in the server's `authorized_keys`), or
   - **FTP** (cPanel shared hosting such as Truehost, HostPinnacle or Namecheap): `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`, `FTP_PATH` (usually `public_html`).
2. Set `canonical_url` in `_config.yml` to your domain so Google treats it as the main copy and not the GitHub Pages one.
3. Point your domain's DNS at the host as the host instructs.

## Email list, unsubscribe and tracking

- **Subscribe box + sending:** our own [listmonk](https://listmonk.app) at https://list.chaiweekly.co.ke (free, on the VPS; set-up in `deploy/listmonk/SETUP.md`). Readers confirm by email (double opt-in), then land on `/subscribe/thanks/`. Emails go out through the newsletter@chaiweekly.co.ke StackMail mailbox (about 2,000 recipients a day). Import your own list under Subscribers > Import (only people who agreed to receive it). listmonk puts an unsubscribe link in every email.
- **Email drafts:** add repo secrets `LISTMONK_API_USER` and `LISTMONK_API_TOKEN`. Each time an issue is merged, `.github/workflows/email-draft.yml` runs `tools/to_listmonk.py`, which creates a listmonk campaign *draft* (never sends) styled like the newspaper site (design: `tools/email/listmonk-template.html` plus the masthead and styles in `tools/to_listmonk.py`). Open listmonk > Campaigns, check it, press Start.
- **Opens and clicks:** listmonk counts these for free (Campaigns > Analytics).
- **Site visits (free):** sign up at [GoatCounter](https://www.goatcounter.com) and set `goatcounter_code`. Links in the email carry `utm_source=newsletter`, so visits from the email show as campaign "newsletter"; shared links show by referring site (WhatsApp, Facebook, X...).

## Tea weather page

`/weather/` shows rain for the past 7 days and the 7-day forecast for each place in `_data/tea_areas.json` (add or move an area there). Readers' browsers fetch the live forecast from Open-Meteo (free, no key). Each Wednesday the collector also runs `tools/weather.py`, which saves `_data/weather_snapshot.json` (used if the live forecast can't load) and adds a weather table to the sources file for the draft. Open-Meteo's free service is for non-commercial use; if Chai Weekly starts earning, move to their paid API plan or re-check the terms.

## Redesign preview

A built copy of the magazine redesign lives in `preview/` and is served at
https://chaiweekly.co.ke/preview/. It is not linked from the live site, is hidden from
search engines and shows a "preview" bar. Rebuild it from the redesign's commit or branch with
`tools/build_preview.sh <commit-or-branch>` (currently built from 2761d7d plus tools/preview-patches/). Delete `preview/` once the redesign goes live.

## Test copy for new features

`preview2/` is a built copy of the live site, served at https://chaiweekly.co.ke/preview2/, where new
features are tried before they go live (first: detailed auction statistics behind a free sign-up). Like
`preview/` it is hidden from search engines, not linked from the live site, shows a "test copy" bar and
is not counted in the reader stats. Its own changes live in `tools/preview2-patches/*.patch`. Rebuild it
from main with `tools/build_preview2.sh` after a patch changes or when it should catch up with the live site.
