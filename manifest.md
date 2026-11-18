# Manifest

Files the job-search-kit installer (`add-addon`) copies into a job-search-kit folder. Sources are relative to this add-on; destinations are relative to the job-search-kit folder. Destinations are only ever under `.claude/skills/` or `.claude/agents/`. Update, reinstall and removal all use this list, and nothing else is touched.

| source | destination |
|---|---|
| skills/build-connections/SKILL.md | .claude/skills/build-connections/SKILL.md |
| skills/rate-connections/SKILL.md | .claude/skills/rate-connections/SKILL.md |
| skills/network-check/SKILL.md | .claude/skills/network-check/SKILL.md |
| skills/network-check/netcsv.py | .claude/skills/network-check/netcsv.py |
| skills/map-company-connections/SKILL.md | .claude/skills/map-company-connections/SKILL.md |
| skills/add-work-context/SKILL.md | .claude/skills/add-work-context/SKILL.md |
| agents/profile-researcher.md | .claude/agents/profile-researcher.md |

## Data this add-on creates (in the user's private folder, never removed by uninstall)

- `my-search/network/connections.csv`: 1st-degree connections and ratings
- `my-search/network/company-connections.csv`: warm 2nd-degree contacts per company
- `my-search/.cache/network-cache.json`: per-company network scores
- `linkedin_company_id` column in `my-search/target-companies.csv`

## Settings it reads from `my-search/profile.md` → `## Add-ons`

- `network: installed`, set by the installer
- `network_version: <x.y.z>`, set by the installer
- `network_cache_days: 30` (optional; the default is 30)
