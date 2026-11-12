# Automatic weekly draft: instructions for Claude

A scheduled Claude session follows this file every Monday at about 07:15 Nairobi time, after
the 06:00 "Gather sources" job has committed `sources/YYYY-MM-DD.md`. The goal is a finished
draft waiting as a pull request for Maxwell's ~15 minute review. Merging the pull request
publishes the issue to the site; nothing goes live without that merge.

## Steps

1. Work in the `maxndungu/chai-weekly` repo, on an up-to-date `main`.
2. Find the newest `sources/*.md`. If none is from the last 2 days, run `python3 tools/gather.py`
   yourself; if that cannot reach the feeds, use web search for the same sections.
3. Work out the next issue number (highest `issue:` in `_posts/` + 1) and read the last issue so
   figures can be compared week on week.
4. Read `tools/DRAFT_PROMPT.md` and follow it exactly. Open the actual articles and auction
   reports (the "Auction reports" section of the sources file) before using any figure. Pick
   the week's real lead story; check `tools/reports.txt` links marked "check by hand" too.
5. Save the issue as `_posts/<today>-issue-<NNN>.md` (NNN zero-padded, today = the Monday).
6. Sanity checks before committing:
   - Front matter has title, issue, deck, description, snapshot (4-5 items), stories (6, with
     anchors that match the `##` headings as kramdown slugs).
   - Every section ends with an italic Sources line of real links you opened.
   - No figure without a source; anything unconfirmed goes in the reviewer notes, not the issue.
   - Titles and salutations: search the whole file (title, deck, snapshot, stories, body) for
     every person's name. Each one needs a correct title ("President Ruto", never bare "Ruto");
     see the "Names and titles" rule in DRAFT_PROMPT.md. Fix any bare surname before committing.
7. Create branch `draft/issue-<NNN>` (if that branch already exists from an earlier closed draft, use `draft/issue-<NNN>-<today>`), commit, push, and open a pull request to `main`:
   - Title: `Issue #N draft: <headline>`
   - Body: a 3-line summary of the issue, then **Reviewer notes**: figures you could not
     confirm, contradictions between sources, and anything that needs Maxwell's judgement.
   - Assign and request review from `maxndungu`.
8. Do not merge. Do not push to `main`. If something blocks the draft, open the pull request
   anyway with what you have and explain the gap in the reviewer notes.
