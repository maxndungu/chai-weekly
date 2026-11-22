# Chai Weekly

A free, independent weekly digital magazine about the global tea industry, published from East Africa. It is a static Jekyll site that GitHub Pages builds for free.

```
_posts/            one markdown file per issue (YYYY-MM-DD-issue-NNN.md)
_layouts/, _includes/, assets/   site design (signup box is _includes/signup.html)
_config.yml        site name + your Buttondown/Substack setting
tools/feeds.txt    RSS feeds to watch (add or remove lines freely)
tools/reports.txt  weekly auction report pages per market (Mombasa, Colombo, India, Chittagong, ...)
tools/gather.py    collects the last 8 days of headlines into sources/
tools/DRAFT_PROMPT.md   the prompt for Claude to draft each issue
.github/workflows/gather-sources.yml   runs gather.py every Wednesday
```

## One-time setup (about 15 minutes)

1. **GitHub repo**: create a public repo (e.g. `chai-weekly`) and push this folder to it.
2. **Pages**: repo Settings → Pages → Source: *Deploy from a branch*, branch `main`, folder `/ (root)`. Your site appears at `https://<you>.github.io/chai-weekly/` within a couple of minutes. Then set `baseurl: "/chai-weekly"` and `url: "https://<you>.github.io"` in `_config.yml`.
3. **Email list**: make a free [Buttondown](https://buttondown.com) account (free up to 100 subscribers, markdown-native) and put your username in `_config.yml` as `buttondown_username`. Or use Substack and set `substack_url` (e.g. `https://chaiweekly.substack.com`). The signup box switches over automatically.
4. **Actions**: the "Gather sources" workflow runs on its own every Wednesday. You can also run it by hand from the Actions tab.

## Weekly routine (about 15 minutes of your time)

**Automatic (current setup):** at 06:00 Nairobi every Wednesday the "Gather sources" job collects the news. At about 07:15 a scheduled Claude session drafts the issue by following `tools/AUTODRAFT.md` and opens a pull request titled "Issue #N draft". Review it (read the reviewer notes, check the figures, edit on GitHub if needed) and **merge** to publish. Close the pull request instead to skip a week.

**By hand (fallback):**

1. **Wednesday**: open `sources/<date>.md` in the repo (the bot added it).
2. **Draft**: paste `tools/DRAFT_PROMPT.md` + the sources file + last week's issue into Claude. Claude returns the full issue.
3. **Review (10 min)**: check every price against its link, read the reviewer notes Claude lists at the end, fix the tone.
4. **Publish**: save it as `_posts/YYYY-MM-DD-issue-NNN.md` (GitHub's "Add file" button works) and commit. The site updates itself.
5. **Send**: paste the same markdown into a new Buttondown email (or Substack post) and send.

## How the magazine is put together

| What | Where it comes from |
|---|---|
| Header, footer, menu | `_includes/header.html`, `_includes/footer.html`, `_data/nav.yml` (the six menu items) |
| Look | `assets/style.css` (colours and fonts at the top), fonts in `assets/fonts/` (Fraunces and Instrument Sans, both free under the SIL Open Font License) |
| Homepage | `index.html`: edition number and date, the three auction prices, the cover story, six story cards, the green market feature, "Inside this edition", events, previous editions, subscribe |
| Cover story | the issue's `title`, `deck` and `cover:` (which story the title is about) |
| Story cards and section pages | each issue's `stories:` list; categories (Markets, Industry, Origins, People, Culture) come from `_data/categories.yml` |
| Pictures | `_data/photos.yml` (see below); until a photo fits, each category shows its drawn illustration from `assets/art/` |
| Market prices | Mombasa: `_data/mombasa_eatta_sales.csv`. Colombo and Chittagong: `_data/colombo_sales.csv`, `_data/chittagong_sales.csv`, one line per sale from the brokers' reports, added by the Wednesday draft. A market with no sourced line shows "No verified figure yet". Market descriptions: `_data/markets.yml` |
| Subscribe box | `_includes/subscribe.html`; set `buttondown_username`, `substack_url` or `newsletter_action` in `_config.yml` |
| Contact details and social links | `contact_email`, `contact_whatsapp` and `social:` in `_config.yml`; blank ones are hidden |

Pages: `/` home, each issue (the article page), `/archive/` (search and filters), `/markets/` (Mombasa, Colombo, Chittagong), `/auctions/` (Mombasa in depth), `/industry/`, `/origins/`, `/people/`, `/culture/`, `/weather/`, `/events/`, `/about/`, `/submit/` (contact and story form; `/contact/` forwards there).

### Adding photos

Put a landscape JPG (about 2000 px wide, under 500 KB) in `assets/photos/`, and add it to `_data/photos.yml` with what it shows (`alt`), where and when (`caption`, only if you know), the credit, and the categories it suits. Use only your own photos or ones whose licence allows it. To put one on an issue, add `image: <id>` to the issue's front matter. Photos tagged with a category are used on that category's story cards automatically.

## Auction analysis page and price history (_data/)

The site's **Auctions** page (`auctions.html`, at /auctions/) combines two files:

- `_data/mombasa_eatta_sales.csv`: every Mombasa sale from EATTA's statistics page. EATTA only shows the current year, so this file is the long-run weekly history. The Wednesday collector adds each new sale, updates any figure EATTA revises (and prints what changed), and never deletes rows. EATTA adds late sales until Friday noon, so the collector also refreshes this file every Friday at 13:00 Nairobi time; Wednesday figures for the newest sale are provisional, Friday figures are final. To update it on another day: Actions, "Gather sources", Run workflow, tick "Only update the EATTA sales CSV".
- `_data/worldbank_tea_mombasa_monthly.csv`: the World Bank Pink Sheet "Tea, Mombasa" monthly price since January 1992 (CC BY 4.0). It is not updated automatically yet: add a line `YYYY-MM,price` early each month when the World Bank publishes.

The page draws its charts and tables from these files, and offers the World Bank series as a CSV download (`downloads/`). The EATTA file is not offered for download.

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
| `home` | Homepage, beside "Inside this edition" (replaces the "Coming up in tea" list while it runs) | Poster, 600 x 900 px portrait |
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

## Mirroring to a paid host (optional)

GitHub stays the source of truth. Every push to `main` also triggers `.github/workflows/mirror-to-host.yml`, which builds the site and uploads it to your host.

1. Add repo secrets (Settings → Secrets and variables → Actions), either:
   - **SSH/rsync** (VPS such as DigitalOcean or Hetzner, or any host with SSH): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_PATH` (e.g. `/var/www/chaiweekly`), `DEPLOY_SSH_KEY` (a private key whose public half is in the server's `authorized_keys`), or
   - **FTP** (cPanel shared hosting such as Truehost, HostPinnacle or Namecheap): `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`, `FTP_PATH` (usually `public_html`).
2. Set `canonical_url` in `_config.yml` to your domain so Google treats it as the main copy and not the GitHub Pages one.
3. Point your domain's DNS at the host as the host instructs.

## Email list, unsubscribe and tracking

- **Subscribe box + sending:** [Buttondown](https://buttondown.com) (free up to 100 subscribers). Put your username in `buttondown_username` in `_config.yml`. Import your own list under Subscribers > Import (only people who agreed to receive it). Buttondown puts an unsubscribe link in every email automatically.
- **Email drafts:** add repo secret `BUTTONDOWN_API_KEY`. Each time an issue is merged, `.github/workflows/email-draft.yml` creates a Buttondown *draft* (never sends). Open Buttondown, check it, press Send.
- **Opens:** Buttondown's Analytics add-on (about $9/month) shows who opened each email.
- **Site visits (free):** sign up at [GoatCounter](https://www.goatcounter.com) and set `goatcounter_code`. Links in the email carry `utm_source=newsletter`, so visits from the email show as campaign "newsletter"; shared links show by referring site (WhatsApp, Facebook, X...).

## Tea weather page

`/weather/` shows rain for the past 7 days and the 7-day forecast for each place in `_data/tea_areas.json` (add or move an area there). Readers' browsers fetch the live forecast from Open-Meteo (free, no key). Each Wednesday the collector also runs `tools/weather.py`, which saves `_data/weather_snapshot.json` (used if the live forecast can't load) and adds a weather table to the sources file for the draft. Open-Meteo's free service is for non-commercial use; if Chai Weekly starts earning, move to their paid API plan or re-check the terms.
