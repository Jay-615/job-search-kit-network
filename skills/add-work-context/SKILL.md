---
name: add-work-context
description: For people the user has marked in my-search/network/company-connections.csv (by typing "Claude - please fill in" in their area_of_work cell), look up their LinkedIn profiles and fill in what they work on and where they're based (network add-on). Only marked people are looked up. Use when the user says "add work context", "fill in the people I marked", or "what do these people work on".
argument-hint: "[company]"
---

# Add work context for marked people

`map-company-connections` gives each warm contact's headline. This fills in a short **area of work and location** ("Marketplace operations · Seattle, WA") for the specific people the user wants to know more about before deciding whom to approach.

Reading profiles is the expensive part, so:

- **Only marked rows**, meaning rows whose `area_of_work` says `Claude - please fill in` (ignoring case and spaces). Optionally only for the company in `$ARGUMENTS`.
- **The profile reading is done by the `profile-researcher` helper agent**, so the raw profile text stays out of this conversation.
- It **only writes the `area_of_work` cell.** No outreach suggestions, no messages, no separate documents.

## Step 1: Find marked rows

Read `my-search/network/company-connections.csv`. If it doesn't exist: "Map a company first. Say **map my connections at <company>**." Then stop.

If no rows are marked, explain how to mark them and stop without writing anything:

> Open `my-search/network/company-connections.csv`, type **Claude - please fill in** in the `area_of_work` cell for anyone you'd like me to look up, save and close it, then ask me again.

## Step 2: Confirm

"I'll look up <N> profiles (<companies>). It takes about <N × 20 seconds> and uses a moderate amount of your Claude plan. Go ahead?" Options: "Yes (Recommended)" / "Cancel".

## Step 3: Hand the list to the helper agent

Start the `profile-researcher` agent **once** for the whole list. If it isn't available, it was just installed and needs a fresh conversation, so tell the user: "Start a new conversation in this folder and ask again." Don't read profiles here instead.

Give it:

- The company name, for context.
- The user's home city, from `my-search/profile.md` → `## Contact` → Location.
- One line per person: `<person_name> | <person_linkedin_url>`.
- The required return format, one line each and nothing else bulky: `<person_linkedin_url> | <area of work> · <City, Region> | <Near you | Elsewhere>`.

## Step 4: Write the results

Build a JSON list of `{"person_linkedin_url": ..., "area_of_work": "<area> · <location>"}` (drop the Near/Elsewhere part). Then:

```bash
python3 .claude/skills/network-check/netcsv.py set-area my-search/.cache/tmp/areas.json
```

If the agent couldn't load a profile at all, **leave that row marked**, so asking again retries it. "Unclear from profile" is fine to write.

## Step 5: Report

```
Filled in 6 of 7.
  Near you: Priya Natarajan (Marketplace operations), Jordan Reeves (Seller tools)
  Elsewhere: …
  Couldn't read: Sam Lee (still marked, so ask again later to retry)
```

If the agent stopped early (CAPTCHA, rate limit, logged out), say so and say who is still marked.
