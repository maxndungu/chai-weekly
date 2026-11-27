# Automatic weekly draft: instructions for Claude

A scheduled Claude session follows this file every Wednesday at about 07:15 Nairobi time, after
the early-morning "Gather sources" job (00:41 Nairobi, retried at 05:17) has committed `sources/YYYY-MM-DD.md`. The goal is a finished
draft waiting as a pull request. Publishing is on Wednesdays because the Mombasa auction runs on Monday (sometimes into Tuesday): use that sale's final figures and the reporting published on Monday-Tuesday to build the week's narrative. The draft is for Maxwell's ~15 minute review. Merging the pull request
publishes the issue to the site; nothing goes live without that merge.

## Steps

1. Work in the `maxndungu/chai-weekly` repo, on an up-to-date `main`.
2. Find today's `sources/<today>.md` on `main`. GitHub sometimes starts scheduled jobs hours late, so if it is
   missing, start a news-only run of "Gather sources" (it leaves the auction data files alone):
   `gh api -X POST repos/maxndungu/chai-weekly/actions/workflows/gather-sources.yml/dispatches -f ref=main -f 'inputs[news_only]=true'`
   It takes about 5 minutes; wait for the file to appear on `main`, then pull. Never start it without `news_only`
   (that would also rewrite the auction data files, which update on Tuesdays and Fridays only). If the run fails
   or can't be started, run `python3 tools/gather.py` yourself; if that cannot reach the feeds either, use
   `_data/mombasa_eatta_sales.csv` for the Mombasa figures and web search for the news sections, and say so in
   the reviewer notes.
3. If any post in `_posts/` has `preview: true` (a test edition), delete it in your branch first and ignore it when numbering. Work out the next issue number (highest `issue:` in `_posts/` + 1) and read the last issue so
   figures can be compared week on week.
4. Read `tools/DRAFT_PROMPT.md` and follow it exactly. Note: the `news.google.com` links in the sources
   file can't be fetched (robots.txt). For each story you want, search the web for its headline to get the
   publisher's own URL, read that, and cite the publisher URL. Nation (nation.africa) also refuses fetching;
   use another outlet's report of the same story. Open the actual articles and auction
   reports (the "Auction reports" section of the sources file) before using any figure. Pick
   the week's real lead story; check `tools/reports.txt` links marked "check by hand" too.
4b. Read `tools/MUST_INCLUDE.md`. Every item under "Open" must be in this issue, written as that file says; then move it to "Done" (with the issue number) in the same pull request, and list it in the PR notes under "Must-include items".
5. Save the issue as `_posts/<today>-issue-<NNN>.md` (NNN zero-padded, today = the Wednesday).
   Then update `_data/events.yml` (the homepage "Coming up in tea" box): read the `## events` section
   of the sources file, and add any tea-specific event in the next 12 months (fair, expo, convention,
   festival, tea day) or fix a changed date. Open the organiser's page or a news report first and put
   its link in `url`; use `month:` when only the month is known. Delete events that have ended. List
   every change under "Events" in the pull-request notes.
6. Sanity checks before committing:
   - Front matter has title, issue, deck, description, snapshot (4-5 items), stories (8: Markets, Industry, East Africa, World, Weather, Farming, Spotlight, Culture, with
     anchors that match the `##` headings as kramdown slugs).
   - Tenders and jobs: every item still open on the issue date, each with its official link; no fee-charging jobs.
   - Leadership and court stories (appointments, removals, elections): search for follow-ups from at least two outlets dated after the first report (court orders often reverse an appointment within days) and report the latest position. If only one outlet reports it, or you could not open the article yourself (e.g. Nation), leave it out of the issue and put it in the reviewer notes.
   - From the shamba: only a real reader submission (never invented); otherwise the one-line invitation.
   - Every section with a fact or figure (One number and Shamba tip included) ends with an italic Sources line of real links you opened (exceptions are listed in DRAFT_PROMPT.md).
   - The week ahead: every date confirmed by a source from this year, inside the next 10 days, with a link; drop anything older (see the Assam note in MUST_INCLUDE.md).
   - Prices: auction prices in US dollars only, no Ksh equivalents in brackets.
   - Mombasa figures: The auction this week has no "according to EATTA", no "provisional figures" note and no "could not find a broker's report" line (Maxwell, 25 Nov 2026); say in the reviewer notes that this week's sale is provisional. Last week's sale is quoted with its final figures from `_data/mombasa_eatta_sales.csv` (updated Tuesday 16:00 and Friday 14:00 Nairobi time, so last week's sale is final by then) if they changed, and the change is listed in the reviewer notes.
   - No figure without a source; anything unconfirmed goes in the reviewer notes, not the issue.
   - Combrok cross-check: copy every line of the "Cross-check: Combrok figures" block of the sources file into the reviewer notes (a difference on a final sale is marked **check**: look at EATTA again before quoting it). Prices and kg sold in the issue are EATTA's. Kg offered and the share sold (absorption) may be quoted from `_data/mombasa_combrok_sales.csv`, credited "according to Combrok's auction report".
   - Titles and salutations: search the whole file (title, deck, snapshot, stories, body) for
     every person's name. Each one needs a correct title ("President Ruto", never bare "Ruto");
     see the "Names and titles" rule in DRAFT_PROMPT.md. Fix any bare surname before committing.
7. Create branch `draft/issue-<NNN>` (if that branch already exists from an earlier closed draft, use `draft/issue-<NNN>-<today>`), commit, push, and open a pull request to `main`:
   - Title: `Issue #N draft: <headline>`
   - Body: a 3-line summary of the issue, then **Reviewer notes**: figures you could not
     confirm, contradictions between sources, and anything that needs Maxwell's judgement.
   - Assign and request review from `maxndungu`.
8. Make the week's social clip from the draft: `tools/weekly_clip/make.sh _posts/<today>-issue-<NNN>.md /mnt/project-files/chai-weekly-social/weekly/issue-<NNN> /mnt/project-files/chai-weekly-social/music`
   (about 5 minutes; square and story MP4s, with the music tracks taking turns by issue number). Attach both files
   in your reply to Maxwell with one line saying which track it uses. They show the draft's figures, so if Maxwell's
   review changes the headline, snapshot or stories, make the clip again after his changes. If it fails, say so in
   one line and carry on: the clip never holds up the issue.
9. Do not merge. Do not push to `main`. If something blocks the draft, open the pull request
   anyway with what you have and explain the gap in the reviewer notes.
