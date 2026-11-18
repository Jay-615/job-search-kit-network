#!/usr/bin/env python3
"""Safe writer for the network add-on's spreadsheets.

  my-search/network/connections.csv          your 1st-degree LinkedIn connections + ratings
  my-search/network/company-connections.csv  warm 2nd-degree people per company

Same rules as the kit's scripts/pipeline.py: refuse to write while a file is
open in Excel/LibreOffice, back up before writing (3 newest kept), keep columns
and values the user added, write atomically, quote every field, no semicolons.
Ratings, last_interaction and notes are the user's and are never overwritten
by a LinkedIn refresh.

Run from the job-search-kit folder:
  python3 .claude/skills/network-check/netcsv.py merge-connections <scraped.json>
  python3 .claude/skills/network-check/netcsv.py set-rating <linkedin_url> <High|Medium|Low|Unrated>
  python3 .claude/skills/network-check/netcsv.py add-connection <row.json>
  python3 .claude/skills/network-check/netcsv.py replace-company <company> <rows.json>
  python3 .claude/skills/network-check/netcsv.py set-area <updates.json>
  python3 .claude/skills/network-check/netcsv.py ratings          # JSON {clean_name: rating}
  python3 .claude/skills/network-check/netcsv.py set-company-id <company> <linkedin id>  # target-companies.csv
  python3 .claude/skills/network-check/netcsv.py clean-name "<name>"
Exit code 2 = a file is open; ask the user to close it.
"""
import csv
import datetime
import glob
import json
import os
import re
import shutil
import sys


def kit_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".claude")) and os.path.isfile(os.path.join(d, "VERSION")):
            return d
        d = os.path.dirname(d)
    return os.getcwd()


KIT = kit_root()
DATA = os.path.join(KIT, "my-search")
NET = os.path.join(DATA, "network")
CONN = os.path.join(NET, "connections.csv")
COCO = os.path.join(NET, "company-connections.csv")
BACKUPS = os.path.join(DATA, ".backups", "network")

CONN_COLS = ["linkedin_url", "name", "headline", "company", "rating",
             "last_interaction", "notes"]
COCO_COLS = ["company", "person_name", "title", "area_of_work", "high_bridges",
             "medium_bridges", "person_linkedin_url", "notes"]
USER_CONN = ("rating", "last_interaction", "notes")
RATINGS = {"high": "High", "medium": "Medium", "low": "Low", "unrated": "Unrated"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def out(obj, code=0):
    print(json.dumps(obj, indent=1, ensure_ascii=False))
    sys.exit(code)


def clean_name(n):
    """'Greta Lindqvist, PHR, SHRM-CP' -> 'Greta Lindqvist'. Keeps Jr./III."""
    s = (n or "").strip()
    if not s:
        return s
    parts = [p.strip() for p in s.split(",")]
    base = parts[0]
    if len(parts) > 1 and parts[1].lower().rstrip(".") in SUFFIXES:
        base = base + ", " + parts[1]
    base = re.sub(r"\s+-\s+[A-Za-z0-9./&®\-]+$", "", base).strip()
    return base


def norm_url(u):
    u = (u or "").strip().split("?")[0].split("#")[0]
    if u and not u.endswith("/"):
        u += "/"
    return u


def cell(v):
    return "" if v is None else str(v).replace(";", " -").replace("\r", " ").replace("\n", " ").strip()


def check_open(path):
    d, f = os.path.split(path)
    for lock in (os.path.join(d, "~$" + f), os.path.join(d, ".~lock." + f + "#")):
        if os.path.exists(lock):
            out({"open": True, "file": path,
                 "message": "Your " + f + " spreadsheet looks open. Please save and close it, then ask me again."}, 2)


def backup(path):
    if not os.path.exists(path):
        return None
    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUPS, os.path.basename(path) + ".bak-" + stamp)
    shutil.copy2(path, dest)
    for old in sorted(glob.glob(os.path.join(BACKUPS, os.path.basename(path) + ".bak-*")), reverse=True)[3:]:
        os.remove(old)
    return dest


def load(path, default_cols):
    if not os.path.exists(path):
        return list(default_cols), []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        r = csv.DictReader(fh)
        header = [h for h in (r.fieldnames or []) if h]   # drop blank trailing headers
        rows = []
        for row in r:
            row.pop(None, None)
            rows.append({h: row.get(h, "") or "" for h in header})
    for c in default_cols:
        if c not in header:
            header.append(c)
    return header, rows


def save(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, quoting=csv.QUOTE_ALL, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in header})
    with open(tmp, newline="", encoding="utf-8") as fh:
        n = sum(1 for _ in csv.DictReader(fh))
    if n != len(rows):
        os.remove(tmp)
        out({"error": "verification failed, nothing written", "expected": len(rows), "got": n}, 1)
    os.replace(tmp, path)


def merge_connections(src):
    check_open(CONN)
    scraped = json.load(open(src, encoding="utf-8"))
    header, rows = load(CONN, CONN_COLS)
    by_url = {norm_url(r.get("linkedin_url")): r for r in rows}
    added = updated = 0
    for s in scraped:
        url = norm_url(s.get("linkedin_url"))
        if not url:
            continue
        name = clean_name(s.get("name"))
        r = by_url.get(url)
        if r is None:
            r = {h: "" for h in header}
            r.update({"linkedin_url": url, "name": cell(name), "headline": cell(s.get("headline")),
                      "company": cell(s.get("company")), "rating": "Unrated"})
            rows.append(r)
            by_url[url] = r
            added += 1
        else:
            r["name"] = cell(name) or r.get("name", "")
            r["headline"] = cell(s.get("headline")) or r.get("headline", "")
            if cell(s.get("company")):
                r["company"] = cell(s.get("company"))
            updated += 1
    for r in rows:   # tidy older names too; user columns untouched
        r["name"] = clean_name(r.get("name"))
    rows.sort(key=lambda r: (r.get("name") or "").lower())
    b = backup(CONN)
    save(CONN, header, rows)
    counts = {}
    for r in rows:
        k = RATINGS.get((r.get("rating") or "").strip().lower(), "Unrated")
        counts[k] = counts.get(k, 0) + 1
    out({"added": added, "refreshed": updated, "total": len(rows), "ratings": counts, "backup": b})


def set_rating(url, rating):
    check_open(CONN)
    rating = RATINGS.get(rating.strip().lower())
    if not rating:
        out({"error": "rating must be High, Medium, Low or Unrated"}, 1)
    header, rows = load(CONN, CONN_COLS)
    hit = [r for r in rows if norm_url(r.get("linkedin_url")) == norm_url(url)]
    if not hit:
        out({"error": "no connection with that linkedin_url"}, 1)
    hit[0]["rating"] = rating
    save(CONN, header, rows)
    out({"ok": True, "name": hit[0].get("name"), "rating": rating})


def add_connection(src):
    check_open(CONN)
    new = json.load(open(src, encoding="utf-8"))
    header, rows = load(CONN, CONN_COLS)
    name = clean_name(new.get("name"))
    url = norm_url(new.get("linkedin_url"))
    for r in rows:
        if (url and norm_url(r.get("linkedin_url")) == url) or \
           (not url and clean_name(r.get("name")).lower() == name.lower()):
            r["rating"] = RATINGS.get((new.get("rating") or "").lower(), r.get("rating") or "Unrated")
            save(CONN, header, rows)
            out({"ok": True, "updated_existing": True, "name": r.get("name")})
    r = {h: "" for h in header}
    r.update({k: cell(v) for k, v in new.items() if k in header})
    r["name"] = name
    r["linkedin_url"] = url
    r["rating"] = RATINGS.get((new.get("rating") or "").lower(), "Unrated")
    rows.append(r)
    rows.sort(key=lambda x: (x.get("name") or "").lower())
    backup(CONN)
    save(CONN, header, rows)
    out({"ok": True, "added": name})


def replace_company(company, src):
    check_open(COCO)
    new = json.load(open(src, encoding="utf-8"))
    header, rows = load(COCO, COCO_COLS)
    key = company.strip().lower()
    kept = [r for r in rows if (r.get("company") or "").strip().lower() != key]
    removed = len(rows) - len(kept)
    for n in new:
        r = {h: "" for h in header}
        for k, v in n.items():
            if k not in header:
                header.append(k)
            r[k] = cell(v)
        r["company"] = company
        r["person_name"] = clean_name(r.get("person_name"))
        kept.append(r)
    b = backup(COCO)
    save(COCO, header, kept)
    out({"company": company, "replaced": removed, "written": len(new), "backup": b})


def set_area(src):
    check_open(COCO)
    ups = json.load(open(src, encoding="utf-8"))
    header, rows = load(COCO, COCO_COLS)
    by = {norm_url(r.get("person_linkedin_url")): r for r in rows}
    done, missing = 0, []
    for u in ups:
        r = by.get(norm_url(u.get("person_linkedin_url")))
        if r is None:
            missing.append(u.get("person_linkedin_url"))
            continue
        r["area_of_work"] = cell(u.get("area_of_work"))
        done += 1
    b = backup(COCO) if done else None
    if done:
        save(COCO, header, rows)
    out({"filled": done, "not_found": missing, "backup": b})


def set_company_id(company, cid):
    path = os.path.join(DATA, "target-companies.csv")
    if not os.path.exists(path):
        out({"skipped": "no target-companies.csv"})
    check_open(path)
    header, rows = load(path, ["company", "priority", "careers_url", "status", "notes",
                               "linkedin_company_id"])
    hit = [r for r in rows if (r.get("company") or "").strip().lower() == company.strip().lower()]
    if not hit:
        out({"skipped": "company not on the target list (not added)"})
    hit[0]["linkedin_company_id"] = cell(cid)
    save(path, header, rows)
    out({"ok": True, "company": hit[0]["company"], "linkedin_company_id": cid})


def ratings():
    _, rows = load(CONN, CONN_COLS)
    res = {}
    for r in rows:
        n = clean_name(r.get("name"))
        if n:
            res[n] = RATINGS.get((r.get("rating") or "").strip().lower(), "Unrated")
    out({"count": len(res), "ratings": res})


def main():
    a = sys.argv[1:]
    if not a:
        out({"error": __doc__}, 1)
    c = a[0]
    if c == "merge-connections":
        merge_connections(a[1])
    elif c == "set-rating":
        set_rating(a[1], a[2])
    elif c == "add-connection":
        add_connection(a[1])
    elif c == "replace-company":
        replace_company(a[1], a[2])
    elif c == "set-area":
        set_area(a[1])
    elif c == "ratings":
        ratings()
    elif c == "set-company-id":
        set_company_id(a[1], a[2])
    elif c == "clean-name":
        out({"name": clean_name(a[1])})
    else:
        out({"error": "unknown command " + c}, 1)


if __name__ == "__main__":
    main()
