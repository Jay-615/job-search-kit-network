---
name: build-connections
description: Read the user's 1st-degree LinkedIn connections into my-search/network/connections.csv (network add-on). Re-runnable. Keeps existing ratings and notes, only adds new people and refreshes headlines. Use when the user says "read my connections", "build my connections", "update my LinkedIn connections", or right after the network add-on is installed.
---

# Read my LinkedIn connections

You copy the user's 1st-degree LinkedIn connections (name, headline, profile link, current company) into `my-search/network/connections.csv`, with every new person marked `Unrated`. The user then rates the people they know (High, Medium or Low). Those ratings are what make network scores useful.

Re-running later (monthly, say) is safe. Existing ratings, last-contact dates and notes are never touched. New connections are added, and headlines and companies are refreshed because people change jobs.

All writes go through the helper: `python3 .claude/skills/network-check/netcsv.py`. It backs up first, refuses to write while the file is open, and keeps the user's columns.

## Step 0: Set expectations

Say:

> I'll read your LinkedIn connections list in Chrome, at a normal browsing pace. For about 500 connections that takes 3–5 minutes and uses a fair bit of your Claude plan. Anything you've already rated stays as it is.

Ask: "Go ahead (Recommended)" / "Cancel".

## Step 1: Browser check

Use the Claude in Chrome tools available in this session (load them if deferred). If no browser is connected: "Chrome isn't connected. Open Chrome and check the Claude extension is signed in, then ask me again." Then stop. Open `https://www.linkedin.com/feed/`. If it redirects to a login page: "Please log into LinkedIn in Chrome, then ask me again." Never log in for them.

## Step 2: Open the connections list and read the total

Go to `https://www.linkedin.com/mynetwork/invite-connect/connections/` and wait about 3 seconds. Read the total:

```javascript
(function(){
  for (const l of (document.body.innerText || '').split('\n').map(s => s.trim())) {
    const m = l.match(/^([\d,]+)\s+[Cc]onnections?$/);
    if (m) return parseInt(m[1].replace(/,/g, ''), 10);
  }
  return null;
})()
```

Tell the user the number. If it's over 1,000, ask whether to read all of them or stop at 500. Either way, you'll check in every 250.

## Step 3: Load the whole list

The list loads more people only on **real mouse-wheel scrolling** inside the main column. Setting `scrollTop` or calling `scrollIntoView` does nothing.

Loop, using the browser's batch tool where available so several steps go in one round trip:

1. Scroll down over the list (the computer tool's `scroll` action, roughly the middle of the page, amount 10).
2. Wait about 2 seconds.
3. Count loaded cards: `document.querySelectorAll('button[aria-label^="More actions for"]').length` (one per person, which is more reliable than counting profile links).

Stop when the count reaches the total (an off-by-one or two is normal), or stops growing across two rounds. Every 250 people, ask: "Keep going (Recommended)" / "Stop here and save what I have".

If a security check, CAPTCHA or "temporary limit" page appears, stop, save what's loaded so far (Steps 4–5), and tell the user to wait an hour before trying again.

## Step 4: Extract the people

Run this once the list is loaded. It stores the results on the page. It doesn't return them, because tool returns are cut off at about 1,000 characters.

```javascript
(function(){
  const seen = new Map();
  for (const a of document.querySelectorAll('a[href*="/in/"]')) {
    let href = a.href.split('?')[0].split('#')[0];
    if (!/\/in\/[^/]+\/?$/.test(href)) continue;
    if (!href.endsWith('/')) href += '/';
    if (seen.has(href)) continue;
    let card = a.parentElement;
    for (let i = 0; i < 6 && card; i++) { const n = (card.innerText || '').length; if (n > 50 && n < 500) break; card = card.parentElement; }
    if (!card) continue;
    const L = (card.innerText || '').split('\n').map(s => s.trim()).filter(Boolean)
      .filter(l => !/^(message|connected on|view profile|remove connection|more options)/i.test(l));
    if (!L[0]) continue;
    seen.set(href, { linkedin_url: href, name: L[0], headline: L.slice(1).join(' ').replace(/\s*Message\s*$/, '').slice(0, 400) });
  }
  window.__conn = Array.from(seen.values());
  return window.__conn.length;
})()
```

To get the data out reliably, render it into the page and read it with the page-text tool:

```javascript
const d = JSON.stringify(window.__conn); document.body.innerHTML = ''; const p = document.createElement('pre'); p.textContent = d; document.body.appendChild(p); 'ok';
```

Save the page text **exactly and completely** to `my-search/.cache/tmp/connections-scraped.json`. Never shorten, summarize or invent entries. If the page text is too long to come back in one read, render and read it in slices (for example 200 people at a time).

## Step 5: Work out each person's current company

For each scraped person, fill a `company` field from the headline only when it's clear:

- Patterns: "… at Company", "… @ Company", "Title - Company". Cut at the first `|`, `•`, `·` or `(`.
- **Past jobs aren't current.** Skip a match preceded by "Former", "ex-", "previously" or "retired".
- Prefer the company over a team name: "Principal PM - Acme Digital Product" → `Acme`.
- "at scale", "at the intersection of…" aren't companies.
- Keep brand names that start lowercase but have an inner capital (eBay, iRobot).
- **When unsure, leave it blank.** A wrong company is worse than none, because it decides whether network scoring thinks you already know someone there.

Then write everything in one call:

```bash
python3 .claude/skills/network-check/netcsv.py merge-connections my-search/.cache/tmp/connections-scraped.json
```

Delete `my-search/.cache/tmp/connections-scraped.json` afterwards.

## Step 6: Report and explain rating

Use the helper's output:

```
Done. Read 487 LinkedIn connections.
  New: 75 · Already there: 412 (your ratings kept)
  High 31 · Medium 22 · Low 14 · Not rated yet 420
```

Then explain, in one friendly paragraph:

> Next, rate the people you'd actually ask for an introduction. **High** means you could ask them for help today. **Medium** means you know them but would want to reconnect first. You don't need to rate everyone. Skip the rest, as only High and Medium count. You can say **rate my connections** and I'll go through them with you, or open `my-search/network/connections.csv` in Excel or Numbers, sort by headline or company, and type High or Medium in the `rating` column. Close the file afterwards.

## LinkedIn page details this depends on (checked mid-2026)

- Connections page: `/mynetwork/invite-connect/connections/`, with a header line "N connections".
- The list scrolls inside `<main>` and loads only on real wheel events. There's no "Show more" button.
- Each card has two `/in/` links and exactly one `More actions for <Name>` button. Class names change often, so don't rely on them.
- Card text order: name, headline (may wrap), "Connected on <date>".
