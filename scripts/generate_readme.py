"""
FORGE — Main README Generation Engine
======================================
This script is the heart of FORGE. It:
  1. Fetches your GitHub data via the GraphQL API
  2. Runs the archetype classification engine
  3. Generates all dynamic SVG assets
  4. Rebuilds your README.md with fresh data

Runs on GitHub Actions schedule (default: daily at midnight UTC).
Can also be triggered manually via workflow_dispatch.
"""

import os
import sys
import json
import math
import datetime
import pathlib
import textwrap
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Internal FORGE modules
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from archetype_engine import (
    GitHubProfile,
    classify_archetype,
    get_archetype_display,
    render_archetype_badge_svg,
    ARCHETYPES,
)
from generate_pulse import render_pulse_svg


# ─── CONFIGURATION ───────────────────────────────────────────

CONFIG_PATH = pathlib.Path(__file__).parent.parent / "config" / "forge.yml"
ASSETS_DIR = pathlib.Path(__file__).parent.parent / "assets" / "generated"
README_PATH = pathlib.Path(__file__).parent.parent / "README.md"

GITHUB_TOKEN = os.environ.get("FORGE_TOKEN") or os.environ.get("GITHUB_TOKEN")
GITHUB_API_URL = "https://api.github.com/graphql"

THEME_PRESETS = {
    "cyberpunk": {
        "bg": "#0D0D0D", "primary": "#00FF9F", "secondary": "#BD00FF",
        "text": "#E0E0E0", "muted": "#555", "border": "#00FF9F"
    },
    "terminal": {
        "bg": "#0C1014", "primary": "#33FF33", "secondary": "#FF8C00",
        "text": "#CCCCCC", "muted": "#444", "border": "#33FF33"
    },
    "arctic": {
        "bg": "#0E1621", "primary": "#A8D8EA", "secondary": "#F4A261",
        "text": "#E0EAF4", "muted": "#4A5568", "border": "#A8D8EA"
    },
    "solarflare": {
        "bg": "#0F0A00", "primary": "#FF6B35", "secondary": "#FFD700",
        "text": "#FFF0DC", "muted": "#554433", "border": "#FF6B35"
    },
    "obsidian": {
        "bg": "#0A0A0A", "primary": "#C9B8FF", "secondary": "#FF79C6",
        "text": "#E2E2E2", "muted": "#444", "border": "#C9B8FF"
    },
    "aurora": {
        "bg": "#060D1F", "primary": "#00FFDD", "secondary": "#FF00A0",
        "text": "#DDEEFF", "muted": "#334455", "border": "#00FFDD"
    },
}

STATUS_ICONS = {
    "open_to_collaborate": ("🟢", "Open to Collaborate"),
    "deep_work": ("🔴", "Deep Work — DMs Closed"),
    "exploring": ("🟡", "Exploring New Territory"),
    "on_leave": ("⚫", "On Leave"),
}


# ─── GITHUB API ──────────────────────────────────────────────

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    login
    bio
    websiteUrl
    company
    location
    followers { totalCount }
    following { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: UPDATED_AT, direction: DESC}) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        primaryLanguage { name }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
        createdAt
        pushedAt
        isPrivate
        description
        homepageUrl
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { contributionCount date weekday }
        }
      }
    }
    pullRequests(first: 100, states: MERGED) {
      totalCount
      nodes {
        repository { nameWithOwner owner { login } }
        createdAt
      }
    }
    issues(first: 100, states: CLOSED) { totalCount }
    issueComments(first: 1) { totalCount }
    organizations(first: 20) { totalCount }
  }
}
"""


def graphql_request(query: str, variables: Dict) -> Dict:
    """Execute a GitHub GraphQL query."""
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "FORGE_TOKEN or GITHUB_TOKEN environment variable not set. "
            "Add a GitHub personal access token with 'read:user' and 'repo' scopes."
        )
    
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        GITHUB_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "FORGE-README-Generator/1.0",
        },
        method="POST",
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read())
            if "errors" in data:
                raise RuntimeError(f"GitHub API errors: {data['errors']}")
            return data["data"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub API HTTP error {e.code}: {e.read().decode()}")


def fetch_profile_data(username: str) -> Dict:
    """Fetch all needed profile data from GitHub GraphQL API."""
    print(f"  ◈ Fetching GitHub data for @{username}...")
    data = graphql_request(GRAPHQL_QUERY, {"login": username})
    return data["user"]


# ─── DATA PROCESSING ─────────────────────────────────────────

def process_profile(raw: Dict, username: str) -> GitHubProfile:
    """Convert raw GitHub API data into a normalized GitHubProfile."""
    repos = [r for r in raw["repositories"]["nodes"] if not r["isPrivate"]]
    
    # Aggregate language usage
    languages: Dict[str, int] = {}
    repo_ages = []
    
    for repo in repos:
        for lang_edge in repo["languages"]["edges"]:
            lang = lang_edge["node"]["name"]
            size = lang_edge["size"]
            languages[lang] = languages.get(lang, 0) + size
        
        created = datetime.datetime.fromisoformat(repo["createdAt"].replace("Z", "+00:00"))
        age_days = (datetime.datetime.now(datetime.timezone.utc) - created).days
        repo_ages.append(age_days)
    
    # Weekly contributions
    weeks = raw["contributionsCollection"]["contributionCalendar"]["weeks"]
    weekly_totals = []
    all_hours = []  # we can't get exact hours from GraphQL easily, approximate
    
    for week in weeks:
        week_total = sum(d["contributionCount"] for d in week["contributionDays"])
        weekly_totals.append(week_total)
    
    # External PRs (PRs to repos not owned by user)
    prs = raw["pullRequests"]["nodes"]
    external_prs = sum(
        1 for pr in prs
        if pr["repository"]["owner"]["login"].lower() != username.lower()
    )
    
    top_stars = max((r["stargazerCount"] for r in repos), default=0)
    avg_age = sum(repo_ages) / len(repo_ages) if repo_ages else 0
    
    return GitHubProfile(
        username=username,
        total_repos=raw["repositories"]["totalCount"],
        total_stars_received=sum(r["stargazerCount"] for r in repos),
        total_commits_last_year=raw["contributionsCollection"]["totalCommitContributions"],
        total_prs=raw["pullRequests"]["totalCount"],
        total_issues_opened=raw["contributionsCollection"]["totalIssueContributions"],
        total_issues_closed=raw["issues"]["totalCount"],
        total_pr_reviews=raw["contributionsCollection"]["totalPullRequestReviewContributions"],
        languages=languages,
        commit_hours=all_hours,
        contribution_by_week=weekly_totals,
        external_pr_count=external_prs,
        follower_count=raw["followers"]["totalCount"],
        following_count=raw["following"]["totalCount"],
        org_count=raw["organizations"]["totalCount"],
        avg_repo_age_days=avg_age,
        has_website=bool(raw.get("websiteUrl")),
        top_repo_stars=top_stars,
    )


# ─── README GENERATION ───────────────────────────────────────

def build_tech_badges(tech_config: Dict, primary: str) -> str:
    """Build the technology stack section."""
    all_tech = []
    for category, items in tech_config.items():
        if category == "currently_learning":
            continue
        all_tech.extend(items)
    
    learning = tech_config.get("currently_learning", [])
    
    # Use shields.io badges
    def badge(name: str, color: str = "0D1117") -> str:
        encoded = name.replace(" ", "%20").replace("+", "%2B").replace("#", "%23")
        return f"![{name}](https://img.shields.io/badge/{encoded}-{color}?style=for-the-badge&logo={encoded.lower()}&logoColor=white)"
    
    badges = " ".join(badge(t) for t in all_tech[:12])
    learning_badges = " ".join(badge(t, "111111") for t in learning[:4])
    
    return f"""
### `> TECH_STACK.load()`

{badges}

**Currently Loading:** {learning_badges}
"""


def build_skill_radar_svg(languages: Dict[str, int], primary: str, secondary: str) -> str:
    """Generate a simple bar chart SVG for top languages."""
    if not languages:
        return ""
    
    total = sum(languages.values()) or 1
    top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:6]
    
    width, height = 400, 30 * len(top_langs) + 40
    bars = []
    
    for i, (lang, size) in enumerate(top_langs):
        pct = size / total
        bar_width = int(pct * 280)
        y = 30 + i * 30
        
        # Gradient color based on rank
        opacity = 1.0 - (i * 0.12)
        
        bars.append(f"""
  <text x="10" y="{y + 4}" font-size="11" fill="#CCC" font-family="Courier New">{lang}</text>
  <rect x="110" y="{y - 10}" width="{bar_width}" height="16" rx="3" fill="{primary}" opacity="{opacity:.2f}"/>
  <text x="{115 + bar_width}" y="{y + 4}" font-size="10" fill="{primary}" font-family="Courier New" opacity="{opacity:.2f}"> {pct:.0%}</text>""")
    
    return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="6" fill="#0D1117"/>
  <text x="10" y="18" font-size="10" fill="#555" font-family="Courier New" letter-spacing="2">// LANGUAGE MATRIX</text>
  {"".join(bars)}
  <rect width="{width}" height="{height}" rx="6" fill="none" stroke="{primary}" stroke-width="0.5" opacity="0.3"/>
</svg>"""


def build_mission_log(repos: List[Dict], primary: str) -> str:
    """Build the recent activity / mission log section."""
    active_repos = [
        r for r in repos 
        if not r["isPrivate"] and r.get("pushedAt") and r.get("description")
    ]
    active_repos.sort(key=lambda r: r.get("pushedAt", ""), reverse=True)
    recent = active_repos[:4]
    
    if not recent:
        return ""
    
    lines = []
    for repo in recent:
        name = repo["name"]
        desc = (repo.get("description") or "")[:65]
        stars = repo["stargazerCount"]
        forks = repo["forkCount"]
        lang = repo.get("primaryLanguage", {})
        lang_name = lang["name"] if lang else "—"
        
        pushed = repo.get("pushedAt", "")
        if pushed:
            pushed_dt = datetime.datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            days_ago = (datetime.datetime.now(datetime.timezone.utc) - pushed_dt).days
            recency = f"{days_ago}d ago" if days_ago > 0 else "today"
        else:
            recency = "—"
        
        lines.append(
            f"| `{name}` | {desc} | `{lang_name}` | ⭐ {stars} | 🍴 {forks} | {recency} |"
        )
    
    return f"""
### `> MISSION_LOG.tail(4)`

| Repository | Description | Lang | Stars | Forks | Updated |
|:-----------|:------------|:-----|:------|:------|:--------|
{chr(10).join(lines)}

> *Auto-updated by FORGE every 24h*
"""


def build_os_karma(profile: GitHubProfile) -> str:
    """Build the Open Source Karma score display."""
    # Karma algorithm: weights different contribution types
    karma = (
        profile.total_commits_last_year * 1.0
        + profile.total_prs * 4.0
        + profile.total_pr_reviews * 3.0
        + profile.total_issues_closed * 2.0
        + profile.external_pr_count * 8.0  # External contributions weighted heavily
        + profile.total_stars_received * 0.5
    )
    
    level = "NOVICE"
    if karma > 5000: level = "LEGENDARY"
    elif karma > 2000: level = "ELITE"
    elif karma > 800: level = "VETERAN"
    elif karma > 300: level = "CONTRIBUTOR"
    elif karma > 100: level = "ACTIVE"
    
    return f"**FORGE Karma:** `{int(karma):,}` — `{level}`"


def render_status_badge_svg(status_key: str, current_mission: str, primary: str) -> str:
    """Render the operative status indicator."""
    icon, label = STATUS_ICONS.get(status_key, ("⚫", "Unknown"))
    mission_short = current_mission[:55] + "..." if len(current_mission) > 55 else current_mission
    
    color_map = {
        "open_to_collaborate": "#00FF9F",
        "deep_work": "#FF4444",
        "exploring": "#FFD700",
        "on_leave": "#888888",
    }
    status_color = color_map.get(status_key, primary)
    
    return f"""<svg width="480" height="72" xmlns="http://www.w3.org/2000/svg">
  <rect width="480" height="72" rx="6" fill="#0D1117"/>
  <rect width="480" height="72" rx="6" fill="none" stroke="{status_color}" stroke-width="0.8" opacity="0.4"/>
  <circle cx="28" cy="36" r="8" fill="{status_color}">
    <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>
  </circle>
  <text x="46" y="28" font-size="9" fill="#666" font-family="Courier New" letter-spacing="2">// STATUS</text>
  <text x="46" y="46" font-size="14" font-weight="700" fill="{status_color}" font-family="Courier New">{label.upper()}</text>
  <text x="260" y="28" font-size="9" fill="#666" font-family="Courier New" letter-spacing="2">// CURRENT MISSION</text>
  <text x="260" y="46" font-size="11" fill="#CCC" font-family="Courier New">{mission_short}</text>
</svg>"""


# ─── MAIN README TEMPLATE ────────────────────────────────────

def build_readme(
    config: Dict,
    raw_data: Dict,
    profile: GitHubProfile,
    archetype_key: str,
    archetype: Dict,
    theme: Dict,
) -> str:
    """Assemble the full README.md content."""
    username = config["identity"]["github_username"]
    name = config["identity"]["name"]
    tagline = config["identity"]["tagline"]
    status_key = config["status"]["availability"]
    current_mission = config["status"]["current_mission"]
    looking_for = config["status"].get("looking_for", "")
    
    primary = theme["primary"]
    secondary = theme["secondary"]
    
    updated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    # Build top languages for display
    top_langs = sorted(profile.languages.items(), key=lambda x: x[1], reverse=True)[:5]
    lang_str = " · ".join(f"`{lang}`" for lang, _ in top_langs)
    
    # Stats summary
    total_stars = profile.total_stars_received
    total_commits = profile.total_commits_last_year
    
    os_karma = build_os_karma(profile)
    mission_log = build_mission_log(raw_data["repositories"]["nodes"], primary)
    total_contributions = raw_data["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    
    # Links
    links = config.get("links", {})
    link_parts = []
    if links.get("website"): link_parts.append(f"[🌐 Website]({links['website']})")
    if links.get("blog"): link_parts.append(f"[📝 Blog]({links['blog']})")
    if links.get("twitter"): link_parts.append(f"[🐦 Twitter](https://twitter.com/{links['twitter'].lstrip('@')})")
    if links.get("linkedin"): link_parts.append(f"[💼 LinkedIn](https://linkedin.com/in/{links['linkedin']})")
    links_str = " · ".join(link_parts) if link_parts else ""
    
    # Build README sections
    readme = f"""<!--
  ██████████████████████████████████████████████████████████
  ██                                                      ██
  ██   FORGE — Developer Identity Engine                  ██
  ██   Auto-generated by github.com/your-username/FORGE   ██
  ██   Last updated: {updated}              ██
  ██                                                      ██
  ██████████████████████████████████████████████████████████
-->

<div align="center">

![FORGE Header](assets/generated/header.svg)

</div>

---

<div align="center">

![Status](assets/generated/status.svg)

</div>

<br/>

## `> IDENTITY`

```
NAME     : {name}
HANDLE   : @{username}
MISSION  : {tagline}
ARCHETYPE: {archetype['sigil']} {archetype['name']}
```

<div align="center">

![Archetype](assets/generated/archetype.svg)

**Power:** {archetype['power']} · **Shadow:** {archetype['shadow']}

</div>

---

## `> DEVELOPER PULSE`

*Your {datetime.datetime.utcnow().year} contribution signal — {total_contributions:,} total events recorded*

<div align="center">

![Developer Pulse](assets/generated/pulse.svg)

</div>

---

## `> STATS`

<div align="center">

![GitHub Stats](https://github-readme-stats.vercel.app/api?username={username}&show_icons=true&theme=dark&hide_border=true&bg_color=0D1117&title_color={primary.lstrip('#')}&icon_color={secondary.lstrip('#')}&text_color=CCCCCC&count_private=true)
&nbsp;&nbsp;
![Top Languages](https://github-readme-stats.vercel.app/api/top-langs/?username={username}&layout=compact&theme=dark&hide_border=true&bg_color=0D1117&title_color={primary.lstrip('#')}&text_color=CCCCCC)

</div>

---

## `> TECH_MATRIX`

<div align="center">

![Language Matrix](assets/generated/lang_matrix.svg)

</div>

**Primary Languages:** {lang_str}

---
{mission_log}
---

## `> OPEN SOURCE KARMA`

{os_karma}

| Metric | Count |
|:-------|------:|
| Commits (last year) | `{total_commits:,}` |
| Pull Requests | `{profile.total_prs:,}` |
| External Contributions | `{profile.external_pr_count:,}` |
| PR Reviews | `{profile.total_pr_reviews:,}` |
| Stars Earned | `{total_stars:,}` |
| Issues Closed | `{profile.total_issues_closed:,}` |

---

## `> CONNECT`

{"" if not links_str else links_str}

> *"The best developers I know are students first."*

---

<div align="center">

**Built with [FORGE](https://github.com/{username}/FORGE)** — *The Developer Identity Engine*

![Visitor Count](https://visitcount.itsvg.in/api?id={username}&label=Profile%20Views&color=0&icon=6&pretty=true)

*README auto-regenerated daily · Last update: `{updated}`*

</div>
"""
    return readme


# ─── MAIN ORCHESTRATION ──────────────────────────────────────

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║            FORGE — Developer Identity Engine            ║
║                     Igniting...                         ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Load config
    print("  ◈ Loading forge.yml config...")
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    
    username = config["identity"]["github_username"]
    theme_name = config.get("theme", {}).get("preset", "cyberpunk")
    theme = THEME_PRESETS.get(theme_name, THEME_PRESETS["cyberpunk"])
    
    # Apply color overrides
    for key in ["accent_primary", "accent_secondary", "background"]:
        val = config.get("theme", {}).get(key)
        if val:
            mapping = {"accent_primary": "primary", "accent_secondary": "secondary", "background": "bg"}
            theme[mapping[key]] = val
    
    # Ensure assets directory exists
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Fetch GitHub data
    raw_data = fetch_profile_data(username)
    
    # Process into normalized profile
    print("  ◈ Processing profile data...")
    profile = process_profile(raw_data, username)
    
    # Run archetype engine
    print("  ◈ Running archetype classification...")
    archetype_key, confidence, all_scores = classify_archetype(profile)
    archetype = get_archetype_display(archetype_key)
    
    print(f"\n  ┌─ CLASSIFICATION RESULT ─────────────────────")
    print(f"  │  Archetype : {archetype['sigil']} {archetype['name']}")
    print(f"  │  Confidence: {confidence:.0%}")
    print(f"  │  Tagline   : {archetype['tagline']}")
    print(f"  └─────────────────────────────────────────────\n")
    
    # Use archetype's palette colors (blended with theme)
    arch_primary = archetype["palette"]["primary"]
    arch_secondary = archetype["palette"]["secondary"]
    
    # Generate SVG assets
    print("  ◈ Generating SVG assets...")
    
    # 1. Header SVG
    header_svg = _generate_header_svg(
        config["identity"]["name"],
        username,
        config["identity"].get("tagline", ""),
        arch_primary,
        arch_secondary,
    )
    (ASSETS_DIR / "header.svg").write_text(header_svg)
    print("    ✓ header.svg")
    
    # 2. Status badge
    status_svg = render_status_badge_svg(
        config["status"]["availability"],
        config["status"]["current_mission"],
        arch_primary,
    )
    (ASSETS_DIR / "status.svg").write_text(status_svg)
    print("    ✓ status.svg")
    
    # 3. Archetype badge
    arch_svg = render_archetype_badge_svg(archetype_key, theme)
    (ASSETS_DIR / "archetype.svg").write_text(arch_svg)
    print("    ✓ archetype.svg")
    
    # 4. Developer Pulse
    contributions = raw_data["contributionsCollection"]["contributionCalendar"]
    weekly = [
        sum(d["contributionCount"] for d in week["contributionDays"])
        for week in contributions["weeks"]
    ]
    pulse_svg = render_pulse_svg(
        contributions=weekly,
        username=username,
        primary_color=arch_primary,
        secondary_color=arch_secondary,
        total_contributions=contributions["totalContributions"],
        year=datetime.datetime.utcnow().year,
    )
    (ASSETS_DIR / "pulse.svg").write_text(pulse_svg)
    print("    ✓ pulse.svg")
    
    # 5. Language matrix
    lang_svg = build_skill_radar_svg(profile.languages, arch_primary, arch_secondary)
    (ASSETS_DIR / "lang_matrix.svg").write_text(lang_svg)
    print("    ✓ lang_matrix.svg")
    
    # Build README
    print("  ◈ Building README.md...")
    readme_content = build_readme(config, raw_data, profile, archetype_key, archetype, theme)
    README_PATH.write_text(readme_content)
    print("    ✓ README.md")
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║                  FORGE COMPLETE  ✓                      ║
║                                                          ║
║  Archetype : {archetype['sigil']} {archetype['name']:<39}║
║  Theme     : {theme_name:<43}║
║  Assets    : 5 SVG files generated                      ║
╚══════════════════════════════════════════════════════════╝
    """)


def _generate_header_svg(name: str, username: str, tagline: str, primary: str, secondary: str) -> str:
    """Generate the profile header SVG with animated elements."""
    # Truncate tagline
    tagline_short = tagline[:60] + "..." if len(tagline) > 60 else tagline
    
    return f"""<svg width="860" height="160" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 860 160">
  <defs>
    <linearGradient id="hdrGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0D0D0D;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#111111;stop-opacity:1"/>
    </linearGradient>
    <linearGradient id="nameGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{primary}"/>
      <stop offset="100%" style="stop-color:{secondary}"/>
    </linearGradient>
    <filter id="nameGlow">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      .forge-label {{ font: 10px 'Courier New', monospace; fill: #444; letter-spacing: 3px; }}
      .forge-name {{ font: 800 42px 'Courier New', monospace; fill: url(#nameGrad); filter: url(#nameGlow); }}
      .forge-handle {{ font: 13px 'Courier New', monospace; fill: #666; }}
      .forge-tagline {{ font: 400 14px 'Courier New', monospace; fill: #999; }}
      .forge-brand {{ font: 700 11px 'Courier New', monospace; fill: {primary}; letter-spacing: 2px; opacity: 0.5; }}
    </style>
  </defs>
  
  <rect width="860" height="160" fill="url(#hdrGrad)"/>
  
  <!-- Decorative circuit lines -->
  <line x1="0" y1="1" x2="860" y2="1" stroke="{primary}" stroke-width="1" opacity="0.3"/>
  <line x1="0" y1="159" x2="860" y2="159" stroke="{primary}" stroke-width="1" opacity="0.3"/>
  
  <!-- Left accent bar -->
  <rect x="0" y="0" width="4" height="160" fill="{primary}" opacity="0.8"/>
  
  <!-- Corner brackets -->
  <polyline points="20,20 8,20 8,8 20,8" fill="none" stroke="{primary}" stroke-width="1.5" opacity="0.6"/>
  <polyline points="840,8 852,8 852,20 840,20" fill="none" stroke="{primary}" stroke-width="1.5" opacity="0.6"/>
  <polyline points="20,152 8,152 8,140 20,140" fill="none" stroke="{primary}" stroke-width="1.5" opacity="0.6"/>
  <polyline points="840,140 852,140 852,152 840,152" fill="none" stroke="{primary}" stroke-width="1.5" opacity="0.6"/>
  
  <!-- Content -->
  <text x="32" y="46" class="forge-label">// DEVELOPER IDENTITY</text>
  <text x="30" y="98" class="forge-name">{name}</text>
  <text x="32" y="122" class="forge-handle">@{username}</text>
  <text x="32" y="146" class="forge-tagline">{tagline_short}</text>
  
  <!-- FORGE brand -->
  <text x="825" y="150" text-anchor="end" class="forge-brand">FORGE ◈</text>
  
  <!-- Animated scan line -->
  <rect x="4" y="0" width="856" height="1.5" fill="{primary}" opacity="0.06">
    <animateTransform attributeName="transform" type="translate" from="0,-5" to="0,165" dur="4s" repeatCount="indefinite"/>
  </rect>
</svg>"""


if __name__ == "__main__":
    main()
