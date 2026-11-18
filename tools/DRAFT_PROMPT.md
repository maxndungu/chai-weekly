# Weekly drafting prompt

Paste everything below the line into Claude, then paste this week's `sources/YYYY-MM-DD.md` underneath. Attach or paste last week's issue too, so the numbers can be compared.

---

You are drafting this week's issue of **Chai Weekly**, a free hobby newsletter about tea with an East African view: Kenya first, then the other EATTA member countries (Uganda, Tanzania, Rwanda, Burundi, Ethiopia, DR Congo, Malawi, Madagascar, Mozambique), then the rest of the tea world, for farmers, tea lovers and the diaspora. Readers skim on their phones.

Use ONLY facts you can trace to the sources below (open the links and read them). Every section that states a fact or a figure (One number and Shamba tip included) ends with an italic "Sources:" line of markdown links. The only sections that may skip it are a one-line "nothing this week" or From the shamba invitation, and The week ahead when every bullet carries its own link. If a section has no fresh source this week, write one honest line saying so rather than inventing anything. Quote prices exactly, with the currency, and say which sale or date they come from.

Output a single Jekyll markdown file with this front matter:

```
---
layout: post
title: "<Front-page headline in Title Case, newspaper style, under 80 characters>"
issue: N
deck: "<one-sentence subheadline that adds what the headline leaves out>"
description: "<one sentence summary for the archive>"
snapshot:   # 4-5 market figures for the ticker under the masthead
  - { label: "Mombasa avg", value: "$X.XX/kg", note: "▲/▼ vs last week" }
  - { label: "Top lot", value: "<factory> US$N.NN/kg" }   # "Top lot" only if the source says it was the highest price of the whole sale; otherwise a true label such as "Best east of Rift"
  - { label: "...", value: "..." }
stories:    # exactly 8, shown as front-page teasers: Markets, Industry, East Africa, World, Weather, Farming, Spotlight, Culture (not From the shamba, Tenders, Week ahead or One number); anchor = the section heading's slug
  - { section: "Markets", anchor: "the-auction-this-week", headline: "<story headline>", summary: "<one or two sentences>" }
  - { section: "East Africa", anchor: "east-africa", headline: "...", summary: "..." }   # plus Industry, World, Weather, Farming, Spotlight, Culture
---
```

Prices stay in US dollars as the auction publishes them (the paper is read by producers outside Kenya too). Do not convert to shillings, and do not add Ksh equivalents in brackets after auction prices even when the source gives them. Farmer payments, bonuses and turnover that are announced in shillings stay in shillings.

Then these sections, in this order, about 1,000 to 1,300 words total:

1. **The auction this week**: lead with the official EATTA figures from the "Mombasa auction (EATTA)" block of the sources file (sale number, CTC average USD/kg, kg sold, change vs the previous sale), then the change vs last issue, best factory east and west of the Rift, volumes, and one sentence on *why*. Then a `### Auctions around the world, week ending <date>` table built from the "Auction reports" part of the sources (open each report link): one row per auction centre (Mombasa, Colombo, Kolkata/Guwahati/Siliguri, South India, Chittagong, Jakarta, Limbe, plus any other with a report), columns `| Auction | Average | Week on week | Note |`, with the sale number, currency as published (add US$ where the report gives it), ▲/▼ for the change, and "Not covered this week" rather than a guess. Put `{: .auction-table}` on the line after the table.
2. **KTDA and factory news**: payments, bonuses, policy, levies, factory elections. Plain-language "what this means for farmers".
3. **East Africa**: the 2 to 4 biggest tea stories from the other EATTA member countries this week, from the `## eastafrica` section of the sources: Uganda, Tanzania, Rwanda, Burundi, Ethiopia, DR Congo, Malawi, Madagascar and Mozambique. Include their teas' prices at Mombasa when a report gives them (e.g. Rwanda, Uganda and Burundi averages), and news from their tea boards and factories (NAEB in Rwanda, OTB in Burundi, the Uganda Tea Development Agency, the Tea Board of Tanzania, Tea Association of Malawi). One short paragraph each with a bold lead-in naming the country. If there is nothing new from a country, leave it out; if there is nothing from the region at all, say so in one line.
4. **Around the tea world**: the 2 to 4 biggest tea stories from outside East Africa this week (Sri Lanka, India, China, Japan, Vietnam, Turkey, major importers like Pakistan, Egypt and the UK). One short paragraph each with a bold lead-in, then one line on why it matters for Kenyan tea.
5. **Weather in the tea counties**: KMD forecasts and warnings first, then the "Weather in the tea areas" table in the sources file (Open-Meteo model: rain last 7 days, next 7 days, coldest night, flags) for Kericho, Bomet, Nandi, Kisii, Nyamira, Nyeri, Murang'a, Kirinyaga, Kiambu, Embu, Meru, plus a line on any flagged area elsewhere in the region. Call the figures model forecasts, never measured rain. End the section with a link: [Rain and forecast for every tea area]({{ '/weather/' | relative_url }}). Always write links to the site's own pages this way, never as `/chai-weekly/...`, so they keep working when the paper moves to its own domain.
6. **Shamba tip**: one practical, seasonal tip tied to this week's weather or news. Defer to extension officers for rates and doses.
7. **From the shamba**: one reader story, letter or photo sent through the Send a story page, if Maxwell has passed one on (look in `submissions/` in the repo and in the task notes). Edit lightly, keep the reader's voice, give their name and area only if they agreed to it. Never invent or paraphrase a reader into a story. If there is none this week, write one line inviting readers to send theirs, linked to `{{ '/submit/' | relative_url }}`.
8. **Factory spotlight**: a short profile (120 to 180 words) of one tea factory, estate or cooperative in Kenya or another EATTA country, chosen from the news or the `## factories` section: where it is, how many growers, what it is known for, and its latest news (a bonus, a new line, an award, a price at Mombasa). Facts only from sources you opened. Rotate countries and regions; do not repeat a factory within 10 issues (check the archive in `_posts/`).
9. **Tea culture**: a recipe, a history note, a tea-tourism spot, or a story, from Kenya or any tea country. Rotate.
10. **Tenders and jobs**: a short list of open tea-sector tenders and job openings in East Africa (factories, KTDA and its companies, tea boards, estates, brokers, packers), from the `## notices` section and from official pages you open (e.g. KTDA's careers and tenders pages, the Tea Board of Kenya, the Public Procurement Information Portal tenders.go.ke, NAEB, the Tea Board of Tanzania). For each: **who**, what, closing date, and the link to the official notice. Only items still open on the issue date. Never publish a job that asks applicants for a fee, and say "apply only through the official link". If none are found, say so in one line.
11. **The week ahead**: 3 to 6 dated bullets for the next 7 to 10 days: the next Mombasa sale (number and date), other auctions, events from `_data/events.yml`, reports or decisions due (tea board figures, bonus announcements, court dates), with a link for each.
12. **One number**: a single striking figure from this week, explained in two sentences.

Style: write like a serious newspaper. Open the issue with a datelined lede paragraph (e.g. "NAIROBI —") that tells the week's main story in two or three sentences. Inside each section use the inverted pyramid: the most important fact first, then context, then detail. Attribute every figure ("according to EATTA", "KTDA said"). Short sentences, plain words, no hype, no exclamation marks, no financial advice. Use these exact `##` section headings so the links stay predictable: The auction this week, KTDA and factory news, East Africa, Around the tea world, Weather in the tea counties, Shamba tip, From the shamba, Factory spotlight, Tea culture, Tenders and jobs, The week ahead, One number. Each `anchor` in `stories` is its heading in lowercase with spaces as hyphens (e.g. `shamba-tip`); give each story its own headline in the `stories` front matter instead. A little Swahili is welcome in the culture and farming sections.

Names and titles (house rule, never skip): always give people their correct title. First mention: title + full name ("President William Ruto", "Agriculture Cabinet Secretary Mutahi Kagwe", "KTDA chairman Enos Njeru", "Prime Minister Kamil Idris"). Later mentions: title + surname ("President Ruto", "CS Kagwe", "Mr Njeru"). Never use a bare surname for anyone, especially heads of state, government officials, MPs, governors, chiefs and religious leaders, and never in a headline, deck, ticker label or teaser: write "President Ruto pledges..." not "Ruto pledges...". Use the official's current title as stated by the source; if unsure, use the fuller form. Apply the same courtesy to foreign leaders and officials.

After the file, list for the human reviewer: (a) any figure you could not confirm, (b) anything that looked contradictory between sources.


## Auction analysis page
In "The auction this week", link readers to the full sale-by-sale history: `[Auction analysis]({{ '/auctions/' | relative_url }})`. Use the same EATTA figures as the page, so the issue and the page agree.

## Sponsor slot
Right after the Sources line that ends "The auction this week" (before `## KTDA and factory news`), put this line on its own, with a blank line above and below:

{% include ad.html slot="issue" %}

It shows the paid sponsor box when one is booked in `_data/ads.yml` and nothing otherwise. Never write sponsor text yourself and never mention a sponsor in the editorial copy.
