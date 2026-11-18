---
name: map-company-connections
description: For one company, find the user's 2nd-degree LinkedIn connections who work there and which of their own contacts could introduce them, keeping only people reachable through someone they rated High or Medium. Writes the result to my-search/network/company-connections.csv (network add-on). Use when the user says "map my connections at <company>", "who could introduce me at <company>", or "find warm intros at <company>".
argument-hint: "<company name>"
---

# Map warm introductions at a company

You find the people at one company that the user could reach through someone they actually know, and record who those go-betweens ("bridges") are. The result is a short table in `my-search/network/company-connections.csv`. **The table is the whole result.** You never suggest who to contact or draft messages. That's the user's call.

**Why this is thorough.** A LinkedIn search card names only 2–3 mutual connections, then says "…and 21 other mutual connections." The user's best contact is often hidden in that "21 others". So for every card that hides some, you open the full mutual-connections list. It's one extra page per card, and it's the point of this command.

**Cost.** One search (up to about 10 pages) plus one page per truncated card. It never opens individual profiles (that's `add-work-context`).

Company: `$ARGUMENTS`. If empty, list the High-priority companies in `my-search/target-companies.csv` that aren't mapped yet (no rows in `company-connections.csv`) and ask which one.

## Step 0: Before starting

1. **Connections and ratings.** If `my-search/network/connections.csv` doesn't exist: "I need your connections first. Say **read my connections**." Then stop. Count unrated people. If there are many, explain once that only High and Medium contacts count as bridges, so anyone unrated is ignored. Ask: "Rate some first" / "Go ahead anyway (Recommended if you've rated the people you'd ask)" / "Cancel".
2. **Someone High already works there?** Check `connections.csv` for a **High**-rated person whose `company` matches (or whose headline names the company **as a whole word**, so a company called "Arc" doesn't match "Architect"). If found, name them and ask: "<Name> already works there, which is probably your best way in. Map everyone else anyway?" Options: "No, that's enough for now (Recommended)" / "Yes, map the whole company". If they say no, stop. Always ask in this case, even if the user said "full" or "deep".
3. **Chrome.** Use the Claude in Chrome tools (load if deferred). If it isn't connected or LinkedIn isn't logged in, say so and stop. Never log in for the user. Pace at 2–3 seconds between page loads. On a CAPTCHA, security check or "too fast" page: stop, save what you have (Steps 4–5), and report.

## Step 1: Company ID

Use `linkedin_company_id` from `target-companies.csv` if present. Otherwise use the method in `.claude/skills/network-check/SKILL.md` Step 3.1 (the most frequent `fsd_company:` id on `/company/<slug>/people/`, and ask if ambiguous), and save it with `netcsv.py set-company-id`.

## Step 2: Crawl the 2nd-degree search

URL (page `n` = 1…10, LinkedIn stops at about 100 people):

```
https://www.linkedin.com/search/results/people/?currentCompany=%5B%22<id>%22%5D&network=%5B%22S%22%5D&page=<n>
```

Install the scraper once. Page loads wipe `window`, so it's kept in `localStorage` and replayed on each page:

```javascript
localStorage.removeItem('mcc');
localStorage.setItem('mccrun', '(' + (function(){
  const main = document.querySelector('main'); if (!main) return {err: 'no main'};
  const L = main.innerText.split('\n').map(s => s.trim()).filter(Boolean);
  const noise = /mutual connection|followers|^view |^connect$|^message$|^follow$|results$/i;
  const store = JSON.parse(localStorage.getItem('mcc') || '[]'), seen = new Set(store.map(e => e.u));
  const anchors = Array.from(main.querySelectorAll('a[href*="/in/"]'));
  let added = 0;
  for (let i = 0; i < L.length; i++) {
    const d = L[i].match(/•\s*(1st|2nd|3rd)\b/i); if (!d) continue;
    const before = L[i].slice(0, d.index).trim(), name = before || L[i - 1];
    if (!name || noise.test(name)) continue;
    let m = ''; for (let j = i + 1; j < Math.min(i + 8, L.length); j++) if (/mutual connection/i.test(L[j])) { m = L[j]; break; }
    const om = m.match(/and\s+(\d+)\s+other\s+mutual connections?/i);
    let u = null, urn = null;
    for (const a of anchors) { const t = (a.innerText || '').trim();
      if (t === name || t.startsWith(name + '\n') || t.startsWith(name + ' ')) { const mm = a.href.match(/\/in\/([^\/?]+)/);
        if (mm) { u = mm[1]; let c = a; for (let k = 0; k < 6 && c; k++) { const n = (c.innerText || '').length; if (n > 60 && n < 600) break; c = c.parentElement; }
          const um = c && (c.outerHTML || '').match(/ACoAA[A-Za-z0-9_-]{10,}/); urn = um ? um[0] : null; break; } } }
    if (!u || seen.has(u)) continue; seen.add(u);
    store.push({ n: name, h: (L[i + 1] || '').slice(0, 180), u, urn, m, other: om ? +om[1] : 0, bridges: null }); added++;
  }
  localStorage.setItem('mcc', JSON.stringify(store));
  return { added, total: store.length, hasNext: L.indexOf('Next') > -1 };
}).toString() + ')()');
'ready';
```

Then for each page, ideally 5 per batch call: navigate → wait 3 seconds → run `eval(localStorage.getItem('mccrun'))`. No scrolling needed. Stop when `hasNext` is false or a page adds 0.

**Hit the ~100 limit?** Mention it in the report and offer a deeper pass: re-run the search split by **location** (add `&geoUrn=%5B%22<region id>%22%5D`, reading region ids from LinkedIn's own location filter, never guessed) or by **keyword** (`&keywords=product`, `engineering`, …). Run the scraper per slice **without** reinstalling it (it skips people already found). Only do this if the user says yes. It costs a full crawl per slice.

## Step 3: Open every truncated card's full mutual list

For each stored person with `other > 0` (even if their visible mutuals already include someone rated High), open:

```
https://www.linkedin.com/search/results/people/?network=%5B%22F%22%5D&connectionOf=%5B%22<urn>%22%5D
```

That's the people who are both the user's connections and this person's, which is every possible bridge. Tool returns hide `ACoAA…` ids, so to get the URLs, render them into the page and read with the page-text tool:

```javascript
const t = JSON.parse(localStorage.getItem('mcc') || '[]').filter(e => e.other > 0);
document.body.innerHTML = ''; const p = document.createElement('pre');
p.textContent = t.map(e => e.u + ' ||| https://www.linkedin.com/search/results/people/?network=%5B%22F%22%5D&connectionOf=%5B%22' + e.urn + '%22%5D').join('\n');
document.body.appendChild(p); 'ok';
```

On each mutual-list page, collect the 1st-degree names and save them back into that person's `bridges` in `localStorage['mcc']` (match on `u`):

```javascript
(function(){ const L = document.querySelector('main').innerText.split('\n').map(s => s.trim()).filter(Boolean), names = [];
  for (let i = 0; i < L.length; i++) { const b = L[i].indexOf('•'); if (b < 0) continue;
    if (L[i].slice(b + 1).trim().indexOf('1st') !== 0) continue;
    const n = L[i].slice(0, b).trim() || L[i - 1]; if (n && !/mutual/i.test(n)) names.push(n); }
  return names; })()
```

If a list comes back empty, the person hides their connections. Keep the card's named mutuals and note "connections hidden".

## Step 4: Get the data out of the browser

Render all of `localStorage['mcc']` into a `<pre>` (as above) and read it with the page-text tool. Save it **exactly and completely** to `my-search/.cache/tmp/mcc-raw.json`. Never shorten, summarize or invent records.

## Step 5: Keep the warm ones and write the table

In Python:

1. Ratings: `python3 .claude/skills/network-check/netcsv.py ratings` gives `{clean name: rating}`.
2. Each person's bridges are the drilled list if present, otherwise the card's mutual line, parsed by **matching known connection names first** (longest first) so "Priya Natarajan, MBA" stays one person, then splitting what's left on commas and "and". Clean every name (`clean-name`).
3. **Unknown bridges** (a name that isn't in `connections.csv` at all): don't silently drop them. Show the user who they are and who they'd introduce, and ask High / Medium / Low. Record each answer with `netcsv.py add-connection` (a JSON file with `name` and `rating`). Ask in one batch if there are several.
4. For each person: `high_bridges` = their High-rated bridges, comma-separated. `medium_bridges` = the same for Medium. **Keep the person only if either is non-empty.**
5. Rows: `person_name`, `title` (their headline, as is), `area_of_work` (**leave blank**, because `add-work-context` fills it when asked), `high_bridges`, `medium_bridges`, `person_linkedin_url` (`https://www.linkedin.com/in/<u>/`), `notes` ("full list via drill-in (card hid +N)", "connections hidden", or blank). Sort: people with High bridges first, then by name.
6. Write, replacing only this company's rows:

   ```bash
   python3 .claude/skills/network-check/netcsv.py replace-company "<Company>" my-search/.cache/tmp/mcc-rows.json
   ```

7. Delete the temporary files, and clear the cache entry for this company in `my-search/.cache/network-cache.json`, so the next scoring run uses the new map.

## Step 6: Report (plain language)

```
Halcyon Marketplace: 64 friends-of-friends found, 9 reachable through someone you know well.

  Jordan Reeves: Senior PM, Seller Tools · via Mira Sato (High)
  Priya Natarajan: Director, Marketplace Ops · via Mira Sato (High), Alicia Tang (Medium)
  …

  Your best bridges here: Mira Sato (7 people), Alicia Tang (3)
  Left out: 55 people whose only links are people you rated Low or haven't rated.
```

Also mention: whether the ~100 limit was hit (and offer the deeper pass), anyone with hidden connections, and the next step: "To see what specific people work on, open `my-search/network/company-connections.csv`, type `Claude - please fill in` in their **area_of_work** cell, save, close, and say **add work context**."

## Known LinkedIn quirks (mid-2026)

- 2nd-degree search: about 10 per page, about 100 maximum per search. The limit is per search, so splitting by location or keyword gets past it.
- A card's name line is either "Name • 2nd" or "Name" then "• 2nd". Handle both.
- Each card has exactly one `ACoAA…` member id (the person's). Mutual-connection avatars have none.
- Tool returns are cut at about 1,000 characters and hide id-like strings. Use `localStorage` plus a rendered `<pre>` plus the page-text tool. Automatic downloads only work once per page load.
