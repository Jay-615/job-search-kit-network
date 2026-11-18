# job-search-kit-network

**This is an add-on for [job-search-kit](https://github.com/Jay-615/job-search-kit). To install it, open your job-search-kit folder in the Claude app and say "add the network add-on."** There's nothing to download from this page yourself.

## What it adds

- **Network scores.** Each job gets a score for how well-connected you are at that company, based on who you know on LinkedIn and how well you know them.
- **Warm introductions.** Say "map my connections at Acme" to see the people at Acme you could reach through someone you know well, and who those go-betweens are.
- **A closer look on request.** Mark specific people and say "add work context", and Claude reads their profiles and notes what they work on and where they're based.

It never contacts anyone or suggests messages. Who to ask, and how, stays your decision.

## Getting started after installing

1. Say **read my connections**. Claude reads your LinkedIn connections list in Chrome (3–5 minutes for about 500 people).
2. Rate the people you'd actually ask for help: **High** (you could ask today) or **Medium** (you'd reconnect first). Say **rate my connections**, or edit `my-search/network/connections.csv` in Excel or Numbers. You don't need to rate everyone.
3. Say **rescore**. Your jobs now include network scores.

## Plan usage

This is the heaviest part of the kit. Reading your connections, and mapping a large company, each use a noticeable share of a Pro plan. Network scores are cached for 30 days per company, so weekly scoring stays cheap once a company has been checked.

## Privacy

Your connections and everything this add-on learns stay in the `my-search` folder on your Mac. LinkedIn is read through your own Chrome, as you, at a normal browsing pace.

## What gets installed

See [manifest.md](manifest.md). To remove it, say **remove the network add-on**. Your connections spreadsheet stays.

<sub>MIT licensed.</sub>
