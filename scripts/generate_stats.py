#!/usr/bin/env python3
"""
Self-hosted GitHub stats card generator.
Writes assets/stats.svg and assets/langs.svg.
Run daily via GitHub Actions.
"""

import os, sys, json, requests
from collections import defaultdict
from datetime import datetime

USERNAME = "sanon8268"
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

QUERY = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    followers { totalCount }
    repositories(
      first: 100
      after: $cursor
      ownerAffiliations: OWNER
      isFork: false
    ) {
      pageInfo { hasNextPage endCursor }
      totalCount
      nodes {
        stargazerCount
        forkCount
        languages(first: 10, orderBy: { field: SIZE, direction: DESC }) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
    }
  }
}
"""

def gql(query, variables):
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers=HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]


def fetch_all():
    all_repos = []
    cursor    = None
    user_meta = None

    while True:
        data = gql(QUERY, {"login": USERNAME, "cursor": cursor})
        u = data["user"]
        if user_meta is None:
            user_meta = {
                "followers": u["followers"]["totalCount"],
                "repoCount": u["repositories"]["totalCount"],
                "cc":        u["contributionsCollection"],
            }
        all_repos.extend(u["repositories"]["nodes"])
        pi = u["repositories"]["pageInfo"]
        if not pi["hasNextPage"]:
            break
        cursor = pi["endCursor"]

    return user_meta, all_repos


def build_stats_svg(meta, repos):
    cc        = meta["cc"]
    commits   = cc["totalCommitContributions"]
    prs       = cc["totalPullRequestContributions"]
    issues    = cc["totalIssueContributions"]
    followers = meta["followers"]
    repo_cnt  = meta["repoCount"]
    stars     = sum(r["stargazerCount"] for r in repos)

    W, H  = 480, 210
    items = [
        ("★ Stars",     stars,     24,  88),
        ("↯ Commits",   commits,  250,  88),
        ("⌥ Pull Reqs", prs,       24, 142),
        ("⚡ Issues",   issues,   250, 142),
        ("⬡ Repos",     repo_cnt,  24, 196),
        ("♦ Followers", followers,250, 196),
    ]

    rows = ""
    for label, val, x, y in items:
        rows += f"""
  <text x="{x}" y="{y - 14}" fill="#666" font-size="11" font-family="monospace">{label}</text>
  <text x="{x}" y="{y}" fill="#ff4444" font-size="22" font-weight="bold" font-family="monospace">{val:,}</text>"""

    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)" rx="10"/>
  <rect width="{W}" height="{H}" fill="none" stroke="#ff0000" stroke-width="1" rx="10" opacity="0.35"/>

  <text x="24" y="44" fill="#ff4444" font-size="15" font-weight="bold" font-family="monospace">📊  sanon8268 · GitHub Stats</text>
  <line x1="24" y1="52" x2="{W-24}" y2="52" stroke="#ff000033" stroke-width="1"/>

  {rows}

  <text x="{W-16}" y="{H-8}" fill="#333" font-size="9" font-family="monospace"
        text-anchor="end">auto-generated · {updated}</text>
</svg>"""


def build_langs_svg(repos):
    sizes  = defaultdict(int)
    colors = {}

    for repo in repos:
        for edge in repo["languages"]["edges"]:
            lang          = edge["node"]["name"]
            sizes[lang]  += edge["size"]
            colors[lang]  = edge["node"]["color"] or "#555555"

    total     = sum(sizes.values()) or 1
    top       = sorted(sizes.items(), key=lambda x: x[1], reverse=True)[:6]
    W, H      = 480, 175
    bar_x     = 24
    bar_w     = W - 48
    bar_top   = 70

    # Coloured bar
    seg = ""
    off = 0
    for lang, size in top:
        w   = int(bar_w * size / total)
        col = colors[lang]
        seg += f'<rect x="{bar_x+off}" y="{bar_top}" width="{w}" height="10" fill="{col}" rx="2"/>'
        off += w

    # Legend
    legend = ""
    lx, ly = 24, bar_top + 32
    for lang, size in top:
        pct = size / total * 100
        col = colors[lang]
        legend += f"""
  <circle cx="{lx+5}" cy="{ly}" r="5" fill="{col}"/>
  <text x="{lx+14}" y="{ly+4}" fill="#cccccc" font-size="11" font-family="monospace">{lang}</text>
  <text x="{lx+14}" y="{ly+16}" fill="#666" font-size="10" font-family="monospace">{pct:.1f}%</text>"""
        lx += max(len(lang)*7 + 46, 72)
        if lx > W - 60:
            lx  = 24
            ly += 44

    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#bg)" rx="10"/>
  <rect width="{W}" height="{H}" fill="none" stroke="#ff0000" stroke-width="1" rx="10" opacity="0.35"/>

  <text x="24" y="38" fill="#ff4444" font-size="15" font-weight="bold" font-family="monospace">💻  Most Used Languages</text>
  <line x1="24" y1="48" x2="{W-24}" y2="48" stroke="#ff000033" stroke-width="1"/>
  <text x="24" y="64" fill="#444" font-size="10" font-family="monospace">across public repos  ·  by bytes of code</text>

  {seg}
  {legend}

  <text x="{W-16}" y="{H-8}" fill="#333" font-size="9" font-family="monospace"
        text-anchor="end">auto-generated · {updated}</text>
</svg>"""


def main():
    os.makedirs("assets", exist_ok=True)
    meta, repos = fetch_all()

    svg_stats = build_stats_svg(meta, repos)
    svg_langs = build_langs_svg(repos)

    with open("assets/stats.svg", "w") as f: f.write(svg_stats)
    with open("assets/langs.svg",  "w") as f: f.write(svg_langs)

    print("✅  assets/stats.svg")
    print("✅  assets/langs.svg")


if __name__ == "__main__":
    main()
