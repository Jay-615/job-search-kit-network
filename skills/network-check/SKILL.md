---
name: network-check
description: Network score for one company (network add-on). Counts the user's 1st- and 2nd-degree LinkedIn connections there, finds which High- and Medium-rated connections could introduce them, and returns a 0–100 score plus the names of those warm contacts. Cached per company. Called by score-jobs for each company, and usable directly when the user asks "who do I know at <company>?" or "check my network at <company>".
argument-hint: "<company name>"
---

# Network check for one company

You produce a network score for one company: how well-connected the user is there, based on their LinkedIn network and the ratings in `my-search/network/connections.csv`.

**Called by `score-jobs`:** return the JSON block in Step 6 as the last thing in your reply, with no human summary. `score-jobs` reads `final_score`, `high_bridge_names` and `medium_bridge_names`. Don't rename them.

**Called directly by the user:** show the short summary in Step 7.

This depends on LinkedIn's page layout, which changes. If something looks wrong, say so and return a failure. Don't guess. A missing score is fine (score-jobs leaves the cell empty). A wrong one isn't.

Company: `$ARGUMENTS`. If empty, ask for it.

## Step 1: Cache

Read `network_cache_days` from `my-search/profile.md` → `## Add-ons` (default 30). In `my-search/.cache/network-cache.json`, look for this company (ignoring case). If it was checked within that many days, return the cached result with `data_source: "cache"`, and **don't open Chrome**. Repeat companies in one scoring run are free this way.

## Step 2: Already mapped, or a High contact who works there?

Both checks are local, with no browser.

1. **Warm-intro table.** If `my-search/network/company-connections.csv` has rows for this company (made by `map-company-connections`), it's the complete source. Use its `high_bridges` and `medium_bridges` columns (comma-separated names) to build the bridge lists, and count its rows as `warm_second_degree_count`. Note "from your warm-intro map" in `reasoning`.
2. **High 1st-degree at the company.** Look in `connections.csv` for a **High**-rated person whose `company` matches (ignoring case, allowing "Inc."-style variants). If `company` is blank, match the company name against their headline **as a whole word**, so a company called "Arc" doesn't match "Architect". If found, they're the warmest path. **Skip the 2nd-degree scrape (Step 4)**, put them in `high_bridge_names`, and note in `reasoning` that a full map is available via "map my connections at <company>".

You still need the 1st-degree count (Step 3), unless Step 2.2 found a High contact and you can set the count from `connections.csv`.

## Step 3: Company ID and 1st-degree count (browser)

Use the Claude in Chrome tools (load them if deferred). If Chrome isn't connected or LinkedIn isn't logged in, return a failure result (Step 6 with `final_score: null` and the reason). Never log in for the user. Wait 2–3 seconds after each page load.

1. **Company ID.** If `my-search/target-companies.csv` has a `linkedin_company_id` for this company, use it. Otherwise open `https://www.linkedin.com/company/<slug>/people/` (slug = lowercase, hyphens) and take the most frequent id:

   ```javascript
   (function(){ const h = document.documentElement.outerHTML, c = {}; let m; const re = /fsd_company:(\d{3,12})/g;
     while ((m = re.exec(h))) c[m[1]] = (c[m[1]] || 0) + 1;
     return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, 3); })()
   ```

   If the page 404s or there's no clear winner, search `https://www.linkedin.com/search/results/companies/?keywords=<name>`. If it's still ambiguous, **ask the user** which company it is. Don't guess. Save a found id with:

   ```bash
   python3 .claude/skills/network-check/netcsv.py set-company-id "<company>" <id>
   ```

   (It only updates companies already on their list. It never adds new ones.)
2. **1st-degree count**, on the same `/company/<slug>/people/` page:

   ```javascript
   (function(){ const L = (document.body.innerText || '').split('\n').map(s => s.trim());
     const m = L.map(l => l.match(/^(.+?)\s+&\s+(\d+)\s+other connections? work here$/)).find(Boolean);
     if (m) return parseInt(m[2], 10) + 1;
     return L.some(l => /^.+ works here$/.test(l)) ? 1 : 0; })()
   ```

   No such line means 0.

## Step 4: 2nd-degree people and their mutual connections (browser)

Skip this if Step 2 found a High 1st-degree or a warm-intro table.

Open `https://www.linkedin.com/search/results/people/?currentCompany=%5B%22<id>%22%5D&network=%5B%22S%22%5D` (first page only, to keep cost down) and read the cards:

```javascript
(function(){
  const L = document.querySelector('main').innerText.split('\n').map(s => s.trim()).filter(Boolean);
  const cards = [];
  for (let i = 0; i < L.length; i++) {
    const d = L[i].match(/•\s*(1st|2nd|3rd)\b/i); if (!d) continue;
    let mutual = ''; for (let j = i + 1; j < Math.min(i + 8, L.length); j++) if (/mutual connection/i.test(L[j])) { mutual = L[j]; break; }
    cards.push(mutual);
  }
  const pages = L.filter(l => /^\d{1,3}$/.test(l)).map(Number);
  window.__nc = { mutuals: cards, maxPage: pages.length ? Math.max(...pages) : 1, next: L.includes('Next') };
  return cards.length + ' cards, max page ' + window.__nc.maxPage;
})()
```

Read `window.__nc` back in small pieces (returns are cut off at about 1,000 characters).

- `second_degree_count` is about `maxPage × 10`. If page 10 is visible and there's a "Next", record 100 and say "100+".
- Mutual-line shapes: "A is a mutual connection" / "A and B are mutual connections" / "A, B, and C are mutual connections" / "A, B and N other mutual connections". Take only the **named** people. Match names against `connections.csv` **before** splitting on commas, longest name first, so "Priya Natarajan, MBA" isn't split into two people. Get the ratings with `python3 .claude/skills/network-check/netcsv.py ratings`, and clean each scraped name the same way (`clean-name`).
- Count how many cards each named connection appears on.

## Step 5: Score

**Base** (highest that applies):

| Signal | Base |
|---|---|
| 1 or more 1st-degree connections | 70 |
| 5 or more 2nd-degree | 50 |
| 1–4 2nd-degree | 30 |
| None, but on the target list | 20 |
| None, not on the list | 10 |

**Bonus**: +25 per **distinct** High-rated bridge, +10 per distinct Medium-rated bridge. Low and Unrated add nothing. Bridges are the mutuals from Step 4, the High 1st-degree from Step 2.2, or the names in the warm-intro table.

**Final**: `min(100, base + bonus)`.

If `connections.csv` doesn't exist or nobody is rated, there's no bonus. Say so in `reasoning`: "Rate your connections to make this score more useful."

## Step 6: Result (cache it, return it)

```json
{
  "company_name": "<as given>",
  "linkedin_company_id": "<id or empty>",
  "first_degree_count": 3,
  "second_degree_count": 40,
  "high_bridge_names": ["Mira Sato"],
  "medium_bridge_names": ["Alicia Tang"],
  "bridge_counts": {"Mira Sato": 6, "Alicia Tang": 2},
  "base_score": 70,
  "bonus_score": 35,
  "final_score": 100,
  "reasoning": "<2–3 plain sentences>",
  "data_source": "fresh | cache | warm-intro map | high 1st-degree",
  "scanned_date": "YYYY-MM-DD"
}
```

On failure: `"final_score": null` and the reason in `reasoning`. **Don't cache failures.**

Write successful results to `my-search/.cache/network-cache.json` keyed by company, keeping other companies' entries. Back the file up first with `python3 scripts/pipeline.py backup my-search/.cache/network-cache.json` (once per session).

## Step 7: Summary (when the user asked directly)

```
Halcyon Marketplace: network score 100
  3 people you know work there · about 40 friends-of-friends
  Warm introductions: Mira Sato (High, knows 6 of them), Alicia Tang (Medium)
  For the full picture, say "map my connections at Halcyon Marketplace".
```

## Stop and report honestly when…

- There's a security check or CAPTCHA. Never solve it. Ask the user to clear it in Chrome.
- "You're searching too fast". Stop and suggest waiting an hour.
- The page text has changed shape (no `• 2nd` markers on a page that clearly lists people). Say which page.

## Known LinkedIn quirks (mid-2026)

- Filtered people searches show no total count, which is why the 1st-degree count comes from the company's People page and the 2nd-degree count is estimated from pagination.
- Result cards have no stable class names. Find them by the "• 1st / 2nd / 3rd" marker line.
- The company's numeric id is the most frequent `fsd_company:<id>` in its People page HTML.
