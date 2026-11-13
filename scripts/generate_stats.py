#!/usr/bin/env python3
"""Generate assets/stats.svg and assets/languages.svg from the GitHub API.

Stdlib only. Needs GITHUB_TOKEN (provided automatically in GitHub Actions).
Run with --demo to render sample data without any network access.
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("PROFILE_USER", "sajidullahkhan08")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")

# Palette: dark warm brown + antique gold
BG, BORDER = "#14110D", "#3A2F20"
TITLE, TEXT, MUTED, VALUE = "#D4A24C", "#C9BBA0", "#8A7A5C", "#E8D9B5"
LANG_COLORS = ["#D4A24C", "#B8860B", "#8B6B3D", "#6B4A2B", "#C9BBA0", "#A89572", "#5A4630", "#3F3224"]
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliation: OWNER, isFork: false, first: 100) {
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
      contributionCalendar { totalContributions }
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
    return {
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "contribs": cc["contributionCalendar"]["totalContributions"],
        "repos": u["repositories"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "langs": langs,
    }


def demo():
    return {
        "stars": 0, "commits": 280, "prs": 12, "issues": 2, "contribs": 306,
        "repos": 33, "followers": 6,
        "langs": {"JavaScript": 420, "TypeScript": 310, "Python": 240, "HTML": 150,
                  "CSS": 120, "Java": 90, "C++": 60, "Svelte": 30},
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


def main():
    if "--demo" in sys.argv:
        data = demo()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GITHUB_TOKEN is not set")
        data = fetch(token)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(stats_svg(data))
    with open(os.path.join(OUT, "languages.svg"), "w", encoding="utf-8") as f:
        f.write(langs_svg(data))
    print("Wrote assets/stats.svg and assets/languages.svg")


if __name__ == "__main__":
    main()
