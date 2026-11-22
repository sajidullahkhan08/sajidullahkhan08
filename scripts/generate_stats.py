#!/usr/bin/env python3
"""Generate assets/stats.svg, assets/languages.svg, and assets/contributions.svg from the GitHub API.

Stdlib only. Needs GITHUB_TOKEN (provided automatically in GitHub Actions).
Run with --demo to render sample data without any network access.
Use --only contributions to generate only assets/contributions.svg.
"""
import datetime
import json
import math
import os
import random
import sys
import urllib.request
from html import escape

USER = os.environ.get("PROFILE_USER", "sajidullahkhan08")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

# Palette: dark warm brown + antique gold (strict design system)
BG, BORDER = "#14110D", "#3A2F20"
TITLE, TEXT, MUTED, VALUE = "#D4A24C", "#C9BBA0", "#8A7A5C", "#E8D9B5"
LANG_COLORS = ["#D4A24C", "#B8860B", "#8B6B3D", "#6B4A2B", "#C9BBA0", "#A89572", "#5A4630", "#3F3224"]
HEATMAP_LEVELS = ["#1C1710", "#3A2F20", "#6B4A2B", "#8B6B3D", "#D4A24C"]
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(isFork: false, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
  }
}
"""


def fetch(token):
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    u = payload["data"]["user"]
    repos = u["repositories"]["nodes"]
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    return {
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "contribs": cal["totalContributions"],
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "langs": langs,
        "calendar": cal,
    }


def demo_calendar():
    rng = random.Random(42)
    base_end = datetime.date(2026, 11, 21)
    days_until_sat = (5 - base_end.weekday()) % 7
    end_date = base_end + datetime.timedelta(days=days_until_sat)
    start_date = end_date - datetime.timedelta(days=53 * 7 - 1)

    weeks = []
    curr = start_date
    total = 0
    for _ in range(53):
        days = []
        for _ in range(7):
            weekday = (curr.weekday() + 1) % 7
            roll = rng.random()
            if roll < 0.73:
                count = 0
            elif roll < 0.88:
                count = rng.randint(1, 2)
            elif roll < 0.96:
                count = rng.randint(3, 5)
            else:
                count = rng.randint(6, 10)
            total += count
            days.append({
                "contributionCount": count,
                "date": curr.isoformat(),
                "weekday": weekday,
            })
            curr += datetime.timedelta(days=1)
        weeks.append({"contributionDays": days})
    return {"totalContributions": total, "weeks": weeks}


def demo():
    return {
        "stars": 0, "commits": 280, "prs": 12, "issues": 2, "contribs": 306,
        "repos": 33, "followers": 6,
        "langs": {"JavaScript": 420, "TypeScript": 310, "Python": 240, "HTML": 150,
                   "CSS": 120, "Java": 90, "C++": 60, "Svelte": 30},
        "calendar": demo_calendar(),
    }


def stats_svg(d):
    rows = [
        ("Total Stars", d["stars"]), ("Repositories", d["repos"]),
        ("Contributions (1y)", d["contribs"]), ("Followers", d["followers"]),
        ("Commits (1y)", d["commits"]), ("Pull Requests (1y)", d["prs"]),
        ("Issues (1y)", d["issues"]),
    ]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-label="GitHub stats for {escape(USER)}">',
           f'<rect x="0.5" y="0.5" width="494" height="194" rx="6" fill="{BG}" stroke="{BORDER}"/>',
           f'<text x="25" y="38" font-family="{FONT}" font-size="18" font-weight="600" fill="{TITLE}">GitHub Stats</text>',
           f'<line x1="25" y1="50" x2="470" y2="50" stroke="{BORDER}"/>']
    for i, (label, val) in enumerate(rows):
        col, row = divmod(i, 4) if i < 4 else (1, i - 4)
        x = 25 + col * 225
        y = 78 + row * 28
        out.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="13" fill="{MUTED}">{escape(label)}</text>')
        out.append(f'<text x="{x + 195}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="14" font-weight="600" fill="{VALUE}">{val:,}</text>')
    out.append("</svg>")
    return "\n".join(out)


def langs_svg(d, top=6):
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:top]
    total = sum(v for _, v in items) or 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="195" viewBox="0 0 300 195" role="img" aria-label="Top languages">',
           f'<rect x="0.5" y="0.5" width="299" height="194" rx="6" fill="{BG}" stroke="{BORDER}"/>',
           f'<text x="25" y="38" font-family="{FONT}" font-size="18" font-weight="600" fill="{TITLE}">Top Languages</text>',
           f'<line x1="25" y1="50" x2="275" y2="50" stroke="{BORDER}"/>']
    x = 25.0
    bar_w = 250.0
    out.append('<clipPath id="bar"><rect x="25" y="62" width="250" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    for i, (name, v) in enumerate(items):
        w = bar_w * v / total
        out.append(f'<rect x="{x:.2f}" y="62" width="{w:.2f}" height="8" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>')
        x += w
    out.append("</g>")
    for i, (name, v) in enumerate(items):
        col, row = divmod(i, 3)
        lx = 25 + col * 130
        ly = 98 + row * 28
        out.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{LANG_COLORS[i % len(LANG_COLORS)]}"/>')
        out.append(f'<text x="{lx + 16}" y="{ly}" font-family="{FONT}" font-size="12" fill="{TEXT}">{escape(name)} <tspan fill="{MUTED}">{100 * v / total:.1f}%</tspan></text>')
    out.append("</svg>")
    return "\n".join(out)


def contributions_svg(d):
    cal = d.get("calendar", {})
    weeks = cal.get("weeks", [])
    total = cal.get("totalContributions", d.get("contribs", 0))

    # Collect non-zero counts to determine quartiles
    non_zero = []
    for w in weeks:
        for day in w.get("contributionDays", []):
            c = day.get("contributionCount", 0)
            if c > 0:
                non_zero.append(c)
    non_zero.sort()

    def get_level(c):
        if c <= 0:
            return 0
        if not non_zero:
            return 1
        n = len(non_zero)
        q1 = non_zero[int(n * 0.25)]
        q2 = non_zero[int(n * 0.50)]
        q3 = non_zero[int(n * 0.75)]
        t1 = max(1, q1)
        t2 = max(t1 + 1, q2)
        t3 = max(t2 + 1, q3)
        if t3 <= non_zero[-1]:
            if c <= t1:
                return 1
            if c <= t2:
                return 2
            if c <= t3:
                return 3
            return 4
        return min(4, max(1, math.ceil(4 * c / non_zero[-1])))

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="860" height="195" viewBox="0 0 860 195" role="img" aria-label="Contribution activity for {escape(USER)}">',
        f'<rect x="0.5" y="0.5" width="859" height="194" rx="6" fill="{BG}" stroke="{BORDER}"/>',
        f'<text x="25" y="32" font-family="{FONT}" font-size="18" font-weight="600" fill="{TITLE}">Contribution Activity</text>',
        f'<text x="25" y="50" font-family="{FONT}" font-size="12" fill="{MUTED}">{total:,} contributions in the last year</text>',
    ]

    # Day labels on the left (Sun=0, Mon=1, Tue=2, Wed=3, Thu=4, Fri=5, Sat=6)
    out.append(f'<text x="50" y="97" text-anchor="end" font-family="{FONT}" font-size="9" fill="{MUTED}">Mon</text>')
    out.append(f'<text x="50" y="125" text-anchor="end" font-family="{FONT}" font-size="9" fill="{MUTED}">Wed</text>')
    out.append(f'<text x="50" y="153" text-anchor="end" font-family="{FONT}" font-size="9" fill="{MUTED}">Fri</text>')

    # Month labels above columns
    last_month_col = -5
    for col_idx, w in enumerate(weeks):
        days = w.get("contributionDays", [])
        for day in days:
            date_str = day.get("date", "")
            if date_str.endswith("-01"):
                try:
                    dt = datetime.date.fromisoformat(date_str)
                    month_name = dt.strftime("%b")
                    if col_idx - last_month_col >= 2:
                        mx = 58 + col_idx * 14
                        out.append(f'<text x="{mx}" y="66" font-family="{FONT}" font-size="10" fill="{MUTED}">{month_name}</text>')
                        last_month_col = col_idx
                except ValueError:
                    pass
                break

    # Contribution grid (up to 53 columns x 7 rows)
    for col_idx, w in enumerate(weeks[:53]):
        gx = 58 + col_idx * 14
        for day in w.get("contributionDays", []):
            weekday = day.get("weekday", 0)
            gy = 74 + weekday * 14
            count = day.get("contributionCount", 0)
            date_str = day.get("date", "")
            lvl = get_level(count)
            color = HEATMAP_LEVELS[lvl]
            tip = f"{count} contributions on {date_str}"
            out.append(
                f'<rect x="{gx}" y="{gy}" width="11" height="11" rx="2" fill="{color}">'
                f'<title>{escape(tip)}</title>'
                f'</rect>'
            )

    # Legend at bottom right: "Less" + 5 small squares + "More"
    out.append(f'<text x="696" y="181" text-anchor="end" font-family="{FONT}" font-size="10" fill="{MUTED}">Less</text>')
    for i, color in enumerate(HEATMAP_LEVELS):
        sx = 702 + i * 13
        out.append(f'<rect x="{sx}" y="172" width="10" height="10" rx="2" fill="{color}"/>')
    out.append(f'<text x="771" y="181" text-anchor="start" font-family="{FONT}" font-size="10" fill="{MUTED}">More</text>')

    out.append("</svg>")
    return "\n".join(out)


def main():
    only_contribs = "--only" in sys.argv and "contributions" in sys.argv
    if "--demo" in sys.argv:
        data = demo()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is not set")
        data = fetch(token)

    os.makedirs(OUT, exist_ok=True)
    if not only_contribs:
        with open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8") as f:
            f.write(stats_svg(data))
        with open(os.path.join(OUT, "languages.svg"), "w", encoding="utf-8") as f:
            f.write(langs_svg(data))
    with open(os.path.join(OUT, "contributions.svg"), "w", encoding="utf-8") as f:
        f.write(contributions_svg(data))

    if only_contribs:
        print("Wrote assets/contributions.svg (preserved stats.svg and languages.svg)")
    else:
        print("Wrote assets/stats.svg, assets/languages.svg, and assets/contributions.svg")


if __name__ == "__main__":
    main()
