#!/usr/bin/env python3
import os, sys, requests
from collections import defaultdict
from datetime import datetime

USERNAME = "sanon8268"
TOKEN    = os.environ.get("GITHUB_TOKEN", "")
HEADERS  = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    followers { totalCount }
    repositories(first:100 after:$cursor ownerAffiliations:OWNER isFork:false) {
      pageInfo { hasNextPage endCursor }
      totalCount
      nodes {
        stargazerCount forkCount
        languages(first:10 orderBy:{field:SIZE direction:DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
    }
  }
}"""

def gql(q, v):
    r = requests.post("https://api.github.com/graphql",
        json={"query":q,"variables":v}, headers=HEADERS, timeout=20)
    r.raise_for_status()
    d = r.json()
    if "errors" in d: sys.exit(str(d["errors"]))
    return d["data"]

def fetch_all():
    repos, cursor, meta = [], None, None
    while True:
        d = gql(QUERY, {"login": USERNAME, "cursor": cursor})
        u = d["user"]
        if meta is None:
            meta = {
                "followers": u["followers"]["totalCount"],
                "repoCount": u["repositories"]["totalCount"],
                "cc":        u["contributionsCollection"],
            }
        repos.extend(u["repositories"]["nodes"])
        pi = u["repositories"]["pageInfo"]
        if not pi["hasNextPage"]: break
        cursor = pi["endCursor"]
    return meta, repos

def stats_svg(meta, repos):
    cc      = meta["cc"]
    stars   = sum(r["stargazerCount"] for r in repos)
    forks   = sum(r["forkCount"]      for r in repos)
    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    items = [
        ("⭐", "STARS",       stars),
        ("↯",  "COMMITS",     cc["totalCommitContributions"]),
        ("⌥",  "PULL REQUESTS",cc["totalPullRequestContributions"]),
        ("⚡", "ISSUES",      cc["totalIssueContributions"]),
        ("⬡",  "REPOS",       meta["repoCount"]),
        ("♦",  "FOLLOWERS",   meta["followers"]),
    ]

    W, H   = 500, 300
    cards  = ""
    col_w  = (W - 48 - 16) // 2   # two columns
    row_h  = 70

    for i, (icon, label, val) in enumerate(items):
        col = i % 2
        row = i // 2
        x   = 24 + col * (col_w + 16)
        y   = 80 + row * (row_h + 12)
        cards += f"""
  <rect x="{x}" y="{y}" width="{col_w}" height="{row_h}"
        fill="#ff000010" rx="8" stroke="#ff000030" stroke-width="1"/>
  <text x="{x+14}" y="{y+22}" fill="#ff444488"
        font-size="13" font-family="monospace">{icon}  {label}</text>
  <text x="{x+14}" y="{y+56}" fill="#ff4444"
        font-size="30" font-weight="bold" font-family="monospace">{val:,}</text>"""

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)" rx="12"/>
  <rect width="{W}" height="{H}" fill="none" stroke="#ff0000"
        stroke-width="1.5" rx="12" opacity="0.4"/>
  <rect width="{W}" height="4" fill="#ff0000" rx="2" opacity="0.8"/>

  <text x="24" y="38" fill="#ff4444" font-size="14" font-weight="bold"
        font-family="monospace" letter-spacing="2">📊  SANON8268 · GITHUB STATS</text>
  <line x1="24" y1="50" x2="{W-24}" y2="50" stroke="#ff000040" stroke-width="1"/>

  {cards}

  <text x="{W//2}" y="{H-10}" fill="#333" font-size="9" font-family="monospace"
        text-anchor="middle">auto-generated · {updated}</text>
</svg>"""

def langs_svg(repos):
    sizes, colors = defaultdict(int), {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            l = edge["node"]["name"]
            sizes[l]  += edge["size"]
            colors[l]  = edge["node"]["color"] or "#555"

    total = sum(sizes.values()) or 1
    top   = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:7]
    W, H  = 500, 220
    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Progress bars
    bars = ""
    by = 90
    for lang, size in top:
        pct    = size / total
        bar_w  = int((W - 48) * pct)
        col    = colors[lang]
        label_pct = f"{pct*100:.1f}%"
        bars += f"""
  <text x="24" y="{by-4}" fill="#888" font-size="11"
        font-family="monospace">{lang}</text>
  <text x="{W-24}" y="{by-4}" fill="#555" font-size="10"
        font-family="monospace" text-anchor="end">{label_pct}</text>
  <rect x="24" y="{by}" width="{W-48}" height="8"
        fill="#ffffff0d" rx="4"/>
  <rect x="24" y="{by}" width="{bar_w}" height="8"
        fill="{col}" rx="4" opacity="0.9"/>"""
        by += 26

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)" rx="12"/>
  <rect width="{W}" height="{H}" fill="none" stroke="#ff0000"
        stroke-width="1.5" rx="12" opacity="0.4"/>
  <rect width="{W}" height="4" fill="#ff0000" rx="2" opacity="0.8"/>

  <text x="24" y="38" fill="#ff4444" font-size="14" font-weight="bold"
        font-family="monospace" letter-spacing="2">💻  MOST USED LANGUAGES</text>
  <text x="24" y="56" fill="#444" font-size="10"
        font-family="monospace">by bytes of code across public repos</text>
  <line x1="24" y1="66" x2="{W-24}" y2="66" stroke="#ff000040" stroke-width="1"/>

  {bars}

  <text x="{W//2}" y="{H-8}" fill="#333" font-size="9"
        font-family="monospace" text-anchor="middle">auto-generated · {updated}</text>
</svg>"""

def main():
    os.makedirs("assets", exist_ok=True)
    meta, repos = fetch_all()
    with open("assets/stats.svg", "w") as f: f.write(stats_svg(meta, repos))
    with open("assets/langs.svg",  "w") as f: f.write(langs_svg(repos))
    print("✅ assets/stats.svg")
    print("✅ assets/langs.svg")

if __name__ == "__main__":
    main()
