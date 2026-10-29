"""Turn Sales Navigator signal exports into a scored prospect list. The agent exports the people from your
signal searches through the Evaboot MCP; this script merges them per person, scores every signal with the
points in SIGNALS.md, puts each person in an action tier and writes the list. Nothing here touches the network.

    python3 score.py list --signal changed_jobs=data/changed_jobs.json --signal viewed_profile=data/viewed.json \\
        [--signals SIGNALS.md] [--date 2026-10-29] [--csv lists/2026-10-29.csv] > lists/2026-10-29.md
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys

# Fallback points, used when SIGNALS.md has no points table. Edit SIGNALS.md, not these.
DEFAULT_POINTS = {"fit": 5, "changed_jobs": 9, "viewed_profile": 8, "follows_company": 4, "posted": 3,
                  "new_in_role": 3, "fast_growth": 7}
LABELS = {"fit": "fits your buyer search", "changed_jobs": "changed jobs", "viewed_profile": "viewed your profile",
          "follows_company": "follows your company", "posted": "posted on LinkedIn",
          "new_in_role": "under 3 months in role", "fast_growth": "company +{growth}% in a year"}
# (minimum score, tier, respond within). Same three tiers as the article.
TIERS = [(20, "today", dt.timedelta(hours=1)), (10, "24h", dt.timedelta(hours=24)), (0, "nurture", dt.timedelta(days=7))]
CSV_FIELDS = ["tier", "score", "respond_by", "name", "title", "company", "signals", "email", "email_status", "linkedin"]


def num(v):
    try:
        return float(str(v).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def read_points(path):
    """The `| signal | points |` rows of SIGNALS.md. Unknown or missing rows keep their default."""
    points = dict(DEFAULT_POINTS)
    try:
        text = open(path).read()
    except OSError:
        return points
    for key, value in re.findall(r"^\|\s*`([a-z_]+)`\s*\|\s*(\d+)\s*\|", text, re.M):
        points[key] = int(value)
    return points


def merge(sources):
    """sources: [(signal name, export.json)]. One row per person with every signal search that found them."""
    people = {}
    for signal, path in sources:
        data = json.load(open(path))
        for p in data.get("prospects") or data.get("results") or []:
            pid = p.get("Linkedin URL Unique ID") or p.get("Linkedin URL Public") or p.get("Full Name")
            if not pid:
                continue
            people.setdefault(pid, {"raw": p, "signals": {"fit"}})["signals"].add(signal)
    return people


def score(people, points, today):
    rows = []
    for pid, row in people.items():
        p, signals = row["raw"], row["signals"]
        years, months = num(p.get("Years in Position")), num(p.get("Months in Position"))
        in_role = None if years is None and months is None else (years or 0) * 12 + (months or 0)
        growth = num(p.get("Company Employee Growth 1 Year (%)"))
        if in_role is not None and in_role < 3:
            signals.add("new_in_role")
        if growth is not None and growth >= 30:
            signals.add("fast_growth")
        total = sum(points.get(s, 0) for s in signals)
        minimum, tier, within = next(t for t in TIERS if total >= t[0])
        due = dt.datetime.combine(today, dt.time(9)) + within
        rows.append({
            "id": pid, "tier": tier, "score": total, "respond_by": due.strftime("%Y-%m-%d %H:%M"),
            "name": p.get("Full Name") or "", "title": (p.get("Current Job") or "").strip(),
            "company": p.get("Company Name") or "", "growth": growth,
            "signals": sorted(signals, key=lambda s: -points.get(s, 0)),
            "email": p.get("Email") or "", "email_status": p.get("Email Status") or "not found",
            "linkedin": p.get("Linkedin URL Public") or "",
        })
    rows.sort(key=lambda r: (-r["score"], r["name"]))
    return rows


def signal_text(row):
    out = []
    for s in row["signals"]:
        label = LABELS.get(s, s)
        out.append(label.format(growth=int(row["growth"])) if s == "fast_growth" else label)
    return ", ".join(out)


def render(rows, today):
    lines = [f"# Prospect list, {today.isoformat()}", ""]
    for _, tier, within in TIERS:
        group = [r for r in rows if r["tier"] == tier]
        hours = int(within.total_seconds() // 3600)
        when = f"within {hours} h" if hours < 48 else f"within {hours // 24} days"
        lines += [f"## {tier}: respond {when} ({len(group)})", ""]
        if not group:
            lines += ["Nobody today.", ""]
            continue
        lines += ["| Score | Person | Company | Signals | Email |", "|---|---|---|---|---|"]
        for r in group:
            email = r["email"] if r["email_status"].lower() == "safe" else f"{r['email_status']}, use LinkedIn"
            person = f"[{r['name']}]({r['linkedin']})" if r["linkedin"] else r["name"]
            lines.append(f"| {r['score']} | {person}, {r['title']} | {r['company']} | {signal_text(r)} | {email} |")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="merge, score and write the prospect list")
    ls.add_argument("--signal", action="append", required=True, metavar="NAME=EXPORT.json")
    ls.add_argument("--signals", default="SIGNALS.md", help="file with the points table")
    ls.add_argument("--date", default=dt.date.today().isoformat())
    ls.add_argument("--csv", help="also write the list as CSV, for a sheet or a CRM import")
    args = ap.parse_args()

    sources = []
    for item in args.signal:
        name, _, path = item.partition("=")
        if not path:
            sys.exit(f"--signal needs NAME=EXPORT.json, got {item}")
        sources.append((name, path))
    today = dt.date.fromisoformat(args.date)
    rows = score(merge(sources), read_points(args.signals), today)
    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({**r, "signals": signal_text(r)})
    print(render(rows, today))


if __name__ == "__main__":
    main()
