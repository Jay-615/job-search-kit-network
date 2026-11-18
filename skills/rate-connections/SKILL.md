---
name: rate-connections
description: Walk the user through rating their unrated LinkedIn connections as High, Medium or Low, one at a time, saving each answer immediately (network add-on). Use when the user says "rate my connections", "help me rate people", or "go through my connections".
---

# Rate my connections

You help the user mark how well they know each **unrated** person in `my-search/network/connections.csv`. Only High and Medium matter for scoring. The user can skip anyone, and stop any time.

## Start

1. If `my-search/network/connections.csv` doesn't exist: "I don't have your connections yet. Say **read my connections** first." Then stop.
2. Count rows whose `rating` is blank or `Unrated`. Treat odd values (like `high ` with a space, or a typo) as unrated, but leave the original text until the user gives a new rating. If there are none: "Everyone's already rated." Show the High/Medium/Low counts, then stop.
3. Say:

   > There are <N> people to rate. I'll show them one at a time.
   > **High**: you could ask them for help today. **Medium**: you know them, but you'd reconnect first. **Low**: you don't really know them.
   > Skip anyone you're unsure about. Only High and Medium count. You can stop whenever you like, and everything you've rated is saved. (Or rate in a spreadsheet: open `my-search/network/connections.csv`, sort by headline, and fill in the `rating` column.)

4. Ask how to order them: "Grouped by company (Recommended)", meaning sorted by `company`, then headline, so colleagues come together / "Alphabetically" / "As listed".

## The loop

For each unrated person:

1. Show:

   ```
   [12 / 487]  Daniel Ortiz
               Director of Product at Cascade Goods
               Notes: (none)
   ```

2. Ask "How well do you know Daniel?" with: **High** · **Medium** · **Low** · **Skip** · **Stop for now**.
3. **Save immediately** after each answer (not in batches):

   ```bash
   python3 .claude/skills/network-check/netcsv.py set-rating "<linkedin_url>" High
   ```

   If it reports the file is open, ask the user to close it, then retry.
4. Every 25 ratings, give a one-line encouragement and a reminder that they can stop.

To speed things up, if several people in a row share a company, you can offer "Rate all <N> remaining people at <Company> as Low" as an extra option.

## Finish

```
Rated 47 this time (High 8 · Medium 14 · Low 25). Skipped 3.
Overall: High 39 · Medium 36 · Low 39 · Not rated 373
```

Then: "Say **rate my connections** any time to continue. Network scores use your new ratings next time you say **rescore**."
