#!/usr/bin/env python3
"""
Generate assets/live_stats.svg (light) and assets/live_stats_dark.svg (dark)
from REAL public GitHub data for a given username — no third-party widget,
no stored secrets beyond the repo's own default GITHUB_TOKEN.

Run by .github/workflows/update-stats.yml on a schedule. Safe to run
locally too: if the network/API is unreachable it falls back to "—"
placeholders instead of crashing, so the file layout can still be checked.
"""
import json
import os
import sys
import urllib.request
import urllib.error

USERNAME = os.environ.get("STATS_USERNAME", "HeloisaPeGarcia")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

API = "https://api.github.com"


def _get(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "live-stats-script",
        "Accept": "application/vnd.github+json",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8")), resp.headers


def fetch_stats(username):
    """Returns dict with public_repos, followers, total_stars, joined_year."""
    user, _ = _get(f"{API}/users/{username}")

    total_stars = 0
    page = 1
    while True:
        repos, _ = _get(
            f"{API}/users/{username}/repos?per_page=100&page={page}&type=owner"
        )
        if not repos:
            break
        total_stars += sum(r.get("stargazers_count", 0) for r in repos)
        if len(repos) < 100:
            break
        page += 1

    joined_year = user.get("created_at", "")[:4] or "—"

    return {
        "public_repos": user.get("public_repos", "—"),
        "followers": user.get("followers", "—"),
        "total_stars": total_stars,
        "joined_year": joined_year,
    }


def fallback_stats():
    return {
        "public_repos": "—",
        "followers": "—",
        "total_stars": "—",
        "joined_year": "—",
    }


def render_svg(stats, dark=False):
    if dark:
        bg_tile = "rgba(255,255,255,0.04)"
        border = "#263241"
        label_color = "#94a3b8"
        value_color = "#f1f5f9"
        accents = ["#1b7389", "#ffc24b", "#ff7a59", "#7fb8c9"]
    else:
        bg_tile = "rgba(255,255,255,0.55)"
        border = "#e2e8f0"
        label_color = "#64748b"
        value_color = "#0b2b36"
        accents = ["#1b7389", "#ffc24b", "#ff7a59", "#124a5c"]

    tiles = [
        ("Public Repos", stats["public_repos"]),
        ("Followers", stats["followers"]),
        ("Total Stars", stats["total_stars"]),
        ("On GitHub Since", stats["joined_year"]),
    ]

    tile_w = 280
    gap = 20
    pad = 20
    width = pad * 2 + tile_w * 4 + gap * 3
    height = 110

    tile_svgs = []
    for i, (label, value) in enumerate(tiles):
        x = pad + i * (tile_w + gap)
        accent = accents[i % len(accents)]
        tile_svgs.append(f'''
    <g transform="translate({x},10)">
      <rect width="{tile_w}" height="{height-20}" rx="16" fill="{bg_tile}" stroke="{border}" stroke-width="1"/>
      <rect x="0" y="0" width="5" height="{height-20}" rx="2.5" fill="{accent}"/>
      <text x="26" y="36" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
            font-size="26" font-weight="800" fill="{value_color}">{value}</text>
      <text x="26" y="58" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif"
            font-size="12" fill="{label_color}">{label}</text>
    </g>''')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <style>
    .tile {{ animation: fadeIn 0.8s ease both; }}
  </style>
{"".join(tile_svgs)}
</svg>
'''
    return svg


def main():
    try:
        stats = fetch_stats(USERNAME)
        source = "live"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        print(f"warning: could not fetch live stats ({e}); writing placeholders", file=sys.stderr)
        stats = fallback_stats()
        source = "fallback"

    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "live_stats.svg"), "w") as f:
        f.write(render_svg(stats, dark=False))
    with open(os.path.join(out_dir, "live_stats_dark.svg"), "w") as f:
        f.write(render_svg(stats, dark=True))

    print(f"wrote live_stats.svg / live_stats_dark.svg ({source}): {stats}")


if __name__ == "__main__":
    main()
