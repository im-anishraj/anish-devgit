"""
╔══════════════════════════════════════════════════════════════╗
║           FORGE — Archetype Classification Engine           ║
║                                                              ║
║  Analyzes your GitHub DNA and assigns you one of 16          ║
║  Developer Archetypes. The heart of what makes FORGE unique. ║
╚══════════════════════════════════════════════════════════════╝

Each archetype has:
  - A name and description
  - A unique visual theme override
  - A "power" and "shadow" trait
  - An associated color palette
  - A sigil (SVG icon)
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import math


# ─────────────────────────────────────────────────────────────
# ARCHETYPE DEFINITIONS
# 16 archetypes in a 4x4 matrix:
#   Axis 1: Breadth vs Depth (polyglot vs specialist)
#   Axis 2: Build vs Explore (shipping vs researching)
#   Axis 3: Solo vs Social (lone wolf vs collaborator)
#   Axis 4: Steady vs Intense (consistent vs burst worker)
# ─────────────────────────────────────────────────────────────

ARCHETYPES = {
    "THE_ARCHITECT": {
        "name": "The Architect",
        "sigil": "◈",
        "tagline": "You don't write code. You design systems.",
        "description": "You see the whole board. Your repos show careful structure, thoughtful abstraction, and documentation that actually helps. You think in layers.",
        "power": "Systems thinking",
        "shadow": "Perfectionism that delays shipping",
        "palette": {"primary": "#4FC3F7", "secondary": "#0277BD", "accent": "#E1F5FE"},
        "criteria": {"min_repos": 10, "doc_ratio": 0.3, "avg_repo_size": "large", "language_focus": "high"},
    },
    "THE_CRAFTSMAN": {
        "name": "The Craftsman",
        "sigil": "⚒",
        "tagline": "Every line of code is a choice. You make good ones.",
        "description": "High commit frequency, small PRs, obsessive attention to detail. Your code reviews are legendary. You care deeply about the work itself.",
        "power": "Code quality at velocity",
        "shadow": "Can get lost polishing instead of shipping",
        "palette": {"primary": "#A5D6A7", "secondary": "#2E7D32", "accent": "#F1F8E9"},
        "criteria": {"commit_frequency": "high", "pr_size": "small", "review_activity": "high"},
    },
    "THE_EXPLORER": {
        "name": "The Explorer",
        "sigil": "◎",
        "tagline": "You map territories others haven't reached yet.",
        "description": "Diverse repos, many languages, experiments everywhere. You move fast across the frontier of what's possible. Not everything ships — but everything teaches.",
        "power": "Intellectual range",
        "shadow": "Repository graveyard of unfinished ideas",
        "palette": {"primary": "#FFB74D", "secondary": "#E65100", "accent": "#FFF3E0"},
        "criteria": {"language_diversity": "high", "repo_count": "high", "completion_rate": "low"},
    },
    "THE_OPERATOR": {
        "name": "The Operator",
        "sigil": "▣",
        "tagline": "While others debate, you deploy.",
        "description": "Your GitHub is all green squares and merged PRs. Infrastructure, pipelines, automation — you make things run. Reliability is your religion.",
        "power": "Execution and reliability",
        "shadow": "Sometimes misses the strategic picture",
        "palette": {"primary": "#EF9A9A", "secondary": "#B71C1C", "accent": "#FFEBEE"},
        "criteria": {"consistency": "high", "infra_repos": True, "ci_usage": True},
    },
    "THE_EDUCATOR": {
        "name": "The Educator",
        "sigil": "⊕",
        "tagline": "The best code you write is the code others understand.",
        "description": "READMEs that are actually good. Tutorial repos. Issues answered with patience. You make the ecosystem better by bringing others up with you.",
        "power": "Knowledge multiplication",
        "shadow": "Sometimes teaches when you should be building",
        "palette": {"primary": "#CE93D8", "secondary": "#6A1B9A", "accent": "#F3E5F5"},
        "criteria": {"readme_quality": "high", "issue_responses": "high", "tutorial_repos": True},
    },
    "THE_NIGHT_OWL": {
        "name": "The Night Owl",
        "sigil": "◐",
        "tagline": "Your best commits happen when the world is asleep.",
        "description": "The timestamp doesn't lie. You think clearer in the dark, when the noise stops. Nocturnal creativity is a real thing and you've proved it.",
        "power": "Deep focus in silence",
        "shadow": "Async misalignment with day-shift collaborators",
        "palette": {"primary": "#80DEEA", "secondary": "#00838F", "accent": "#E0F7FA"},
        "criteria": {"peak_hours": "night", "commit_hour_avg": ">22 or <4"},
    },
    "THE_POLYGLOT": {
        "name": "The Polyglot",
        "sigil": "⬡",
        "tagline": "You speak the right language for the right problem.",
        "description": "5+ languages used meaningfully. You don't just know JavaScript and Python — you reason about when each language is the right tool. Linguistic fluency transfers to code.",
        "power": "Cross-paradigm problem solving",
        "shadow": "Context-switching cost",
        "palette": {"primary": "#FFCC02", "secondary": "#F57F17", "accent": "#FFFDE7"},
        "criteria": {"unique_languages": ">5", "language_commits_distributed": True},
    },
    "THE_SPECIALIST": {
        "name": "The Specialist",
        "sigil": "◆",
        "tagline": "You know one thing at a depth most never reach.",
        "description": "One domain, one language, one problem space — pursued with almost unreasonable depth. The go-to person for one thing. Experts know experts.",
        "power": "Unmatched depth in chosen domain",
        "shadow": "Can become a hammer looking for nails",
        "palette": {"primary": "#BCAAA4", "secondary": "#4E342E", "accent": "#EFEBE9"},
        "criteria": {"primary_language_dominance": ">70%", "domain_focus": "high"},
    },
    "THE_MAINTAINER": {
        "name": "The Maintainer",
        "sigil": "⬢",
        "tagline": "You keep the lights on for everyone else.",
        "description": "High issue-close rate, consistent responses, long-lived repositories. Open source runs on maintainers like you. Invisible and essential.",
        "power": "Community trust and longevity",
        "shadow": "Maintainer burnout is real",
        "palette": {"primary": "#80CBC4", "secondary": "#00695C", "accent": "#E0F2F1"},
        "criteria": {"open_issues_ratio": "low", "repo_age": "high", "contributor_count": "high"},
    },
    "THE_SPRINTER": {
        "name": "The Sprinter",
        "sigil": "⟫",
        "tagline": "30-day builds that others take a year to ship.",
        "description": "Your contribution graph is a story of intense bursts. When you're locked in, you're unstoppable. Hackathon champion energy. You ship whole products in weekends.",
        "power": "Burst velocity and shipping instinct",
        "shadow": "Sustainability between sprints",
        "palette": {"primary": "#FF8A65", "secondary": "#BF360C", "accent": "#FBE9E7"},
        "criteria": {"contribution_variance": "high", "burst_patterns": True},
    },
    "THE_OPEN_SOURCERER": {
        "name": "The Open Sourcerer",
        "sigil": "✦",
        "tagline": "You give more than you take. The ecosystem thanks you.",
        "description": "High PRs to external repos, meaningful issue contributions, fork activity. The true spirit of open source — you improve things you didn't create.",
        "power": "Cross-project collaboration",
        "shadow": "Your own projects sometimes lack the same love",
        "palette": {"primary": "#F48FB1", "secondary": "#880E4F", "accent": "#FCE4EC"},
        "criteria": {"external_contributions": "high", "fork_prs": "high"},
    },
    "THE_PIONEER": {
        "name": "The Pioneer",
        "sigil": "▲",
        "tagline": "You were building with this before it was cool.",
        "description": "Early repos in now-trending technologies. Your stars often arrive late — because you were right early. The timestamps are the receipts.",
        "power": "Technical foresight",
        "shadow": "Ahead of your time can mean alone for a while",
        "palette": {"primary": "#90CAF9", "secondary": "#1565C0", "accent": "#E3F2FD"},
        "criteria": {"early_tech_adoption": True, "trending_lang_age": "early"},
    },
    "THE_RESEARCHER": {
        "name": "The Researcher",
        "sigil": "⊗",
        "tagline": "You don't just solve problems. You understand them.",
        "description": "Academic repos, papers linked, experiments with careful writeups. You bring intellectual rigor to engineering. Your commits have citations.",
        "power": "Rigor and depth of understanding",
        "shadow": "Research-to-production gap",
        "palette": {"primary": "#B39DDB", "secondary": "#4527A0", "accent": "#EDE7F6"},
        "criteria": {"paper_links": True, "ml_ai_repos": "high", "readme_depth": "very_high"},
    },
    "THE_BUILDER": {
        "name": "The Builder",
        "sigil": "□",
        "tagline": "Shipped. Shipped. Shipped.",
        "description": "High repo count, live projects, real users. You build full products, not just libraries. Impact is measured in users, not stars.",
        "power": "End-to-end product ownership",
        "shadow": "Technical debt accumulates",
        "palette": {"primary": "#A5D6A7", "secondary": "#1B5E20", "accent": "#F9FBE7"},
        "criteria": {"live_projects": "high", "full_stack": True, "deploy_evidence": True},
    },
    "THE_PHANTOM": {
        "name": "The Phantom",
        "sigil": "◇",
        "tagline": "Your best work lives in private repos. For now.",
        "description": "Sparse public contributions but high quality when visible. You operate with discretion. The iceberg profile — most of it is below the surface.",
        "power": "Focus and intentionality",
        "shadow": "The open source world can't learn from what it can't see",
        "palette": {"primary": "#CFD8DC", "secondary": "#455A64", "accent": "#ECEFF1"},
        "criteria": {"public_repo_ratio": "low", "quality_over_quantity": True},
    },
    "THE_CONNECTOR": {
        "name": "The Connector",
        "sigil": "◉",
        "tagline": "You are the bridge between people and problems.",
        "description": "High follower/following ratio, active in discussions, org memberships, collaborative PRs. You are the social infrastructure of open source.",
        "power": "Network effects and community building",
        "shadow": "Breadth without depth",
        "palette": {"primary": "#FFF176", "secondary": "#F9A825", "accent": "#FFFDE7"},
        "criteria": {"follower_count": "high", "org_memberships": "high", "discussion_activity": "high"},
    },
}


@dataclass
class GitHubProfile:
    """Normalized GitHub profile data for archetype analysis."""
    username: str
    total_repos: int
    total_stars_received: int
    total_commits_last_year: int
    total_prs: int
    total_issues_opened: int
    total_issues_closed: int
    total_pr_reviews: int
    languages: Dict[str, int]          # lang -> bytes
    commit_hours: List[int]            # hour of day (0-23) for last N commits
    contribution_by_week: List[int]    # weekly contribution counts
    external_pr_count: int             # PRs to repos not owned by user
    follower_count: int
    following_count: int
    org_count: int
    avg_repo_age_days: float
    has_website: bool
    top_repo_stars: int


def classify_archetype(profile: GitHubProfile) -> Tuple[str, float, Dict[str, float]]:
    """
    Classify a developer into one of 16 archetypes.
    Returns (archetype_key, confidence_score, all_scores_dict)
    
    The algorithm scores each archetype across multiple dimensions
    and returns the highest scoring one with a confidence level.
    """
    scores: Dict[str, float] = {}
    
    # Derived metrics
    language_count = len(profile.languages)
    total_lang_bytes = sum(profile.languages.values()) or 1
    primary_lang_pct = (max(profile.languages.values()) / total_lang_bytes) if profile.languages else 0
    
    night_commits = sum(1 for h in profile.commit_hours if h >= 22 or h <= 4)
    night_ratio = night_commits / max(len(profile.commit_hours), 1)
    
    # Contribution burst score — variance in weekly activity
    if profile.contribution_by_week:
        avg_weekly = sum(profile.contribution_by_week) / len(profile.contribution_by_week)
        variance = sum((w - avg_weekly)**2 for w in profile.contribution_by_week) / len(profile.contribution_by_week)
        burst_score = min(math.sqrt(variance) / max(avg_weekly, 1), 1.0)
    else:
        burst_score = 0.0
    
    issue_close_ratio = profile.total_issues_closed / max(profile.total_issues_opened, 1)
    external_contribution_ratio = profile.external_pr_count / max(profile.total_prs, 1)
    
    # ── Score each archetype ──────────────────────────────────
    
    scores["THE_ARCHITECT"] = _score(
        (profile.total_repos >= 15, 2.0),
        (primary_lang_pct > 0.5, 1.5),
        (profile.avg_repo_age_days > 180, 1.5),
        (profile.total_pr_reviews > 20, 1.0),
    )
    
    scores["THE_CRAFTSMAN"] = _score(
        (profile.total_commits_last_year > 500, 2.0),
        (profile.total_pr_reviews > 30, 2.0),
        (burst_score < 0.3, 1.0),  # consistent, not bursty
    )
    
    scores["THE_EXPLORER"] = _score(
        (language_count >= 6, 2.5),
        (profile.total_repos >= 20, 1.5),
        (burst_score > 0.5, 1.0),
    )
    
    scores["THE_OPERATOR"] = _score(
        (burst_score < 0.2, 2.0),
        (profile.total_commits_last_year > 400, 1.5),
        (issue_close_ratio > 0.8, 1.5),
    )
    
    scores["THE_EDUCATOR"] = _score(
        (profile.total_issues_closed > 50, 2.0),
        (profile.has_website, 1.0),
        (issue_close_ratio > 0.7, 1.5),
    )
    
    scores["THE_NIGHT_OWL"] = _score(
        (night_ratio > 0.5, 3.0),
        (night_ratio > 0.35, 2.0),
        (night_ratio > 0.2, 1.0),
    )
    
    scores["THE_POLYGLOT"] = _score(
        (language_count >= 7, 3.0),
        (language_count >= 5, 2.0),
        (primary_lang_pct < 0.4, 1.5),
    )
    
    scores["THE_SPECIALIST"] = _score(
        (primary_lang_pct > 0.75, 3.0),
        (primary_lang_pct > 0.6, 2.0),
        (language_count <= 3, 1.5),
    )
    
    scores["THE_MAINTAINER"] = _score(
        (issue_close_ratio > 0.85, 2.5),
        (profile.avg_repo_age_days > 365, 2.0),
        (profile.total_issues_closed > 100, 1.5),
    )
    
    scores["THE_SPRINTER"] = _score(
        (burst_score > 0.7, 3.0),
        (burst_score > 0.5, 2.0),
        (profile.total_commits_last_year > 300, 1.0),
    )
    
    scores["THE_OPEN_SOURCERER"] = _score(
        (external_contribution_ratio > 0.5, 3.0),
        (external_contribution_ratio > 0.3, 2.0),
        (profile.total_prs > 30, 1.5),
    )
    
    scores["THE_PIONEER"] = _score(
        (language_count >= 4, 1.5),
        (profile.total_repos >= 15, 1.0),
        # Pioneer detection requires date-based analysis done elsewhere
    )
    
    scores["THE_RESEARCHER"] = _score(
        (language_count >= 3, 1.0),
        (profile.total_repos >= 10, 1.0),
        (profile.avg_repo_age_days > 200, 1.5),
    )
    
    scores["THE_BUILDER"] = _score(
        (profile.has_website, 2.0),
        (profile.total_repos >= 8, 1.5),
        (profile.top_repo_stars > 50, 2.0),
    )
    
    scores["THE_PHANTOM"] = _score(
        (profile.total_repos <= 10, 2.0),
        (profile.top_repo_stars > 100, 2.0),
        (profile.total_commits_last_year < 200, 1.0),
    )
    
    scores["THE_CONNECTOR"] = _score(
        (profile.follower_count > 100, 2.5),
        (profile.org_count > 3, 2.0),
        (profile.following_count > 50, 1.0),
    )
    
    # Normalize scores
    max_possible = 6.0
    normalized = {k: min(v / max_possible, 1.0) for k, v in scores.items()}
    
    # Find winner
    winner = max(normalized, key=normalized.get)
    confidence = normalized[winner]
    
    return winner, confidence, normalized


def _score(*conditions: Tuple[bool, float]) -> float:
    """Sum weighted boolean conditions."""
    return sum(weight for cond, weight in conditions if cond)


def get_archetype_display(archetype_key: str) -> dict:
    """Return the full display object for an archetype."""
    return ARCHETYPES.get(archetype_key, ARCHETYPES["THE_BUILDER"])


def render_archetype_badge_svg(archetype_key: str, theme: dict) -> str:
    """Generate an animated SVG badge for the archetype."""
    archetype = ARCHETYPES.get(archetype_key, ARCHETYPES["THE_BUILDER"])
    primary = archetype["palette"]["primary"]
    secondary = archetype["palette"]["secondary"]
    sigil = archetype["sigil"]
    name = archetype["name"]
    tagline = archetype["tagline"]
    
    return f"""<svg width="480" height="120" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 120">
  <defs>
    <linearGradient id="archGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{secondary};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{primary};stop-opacity:0.2" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <style>
      .sigil {{ 
        font-size: 42px; 
        fill: {primary}; 
        filter: url(#glow);
        animation: pulse 2s ease-in-out infinite;
      }}
      .archetype-name {{ font-size: 18px; font-weight: 700; fill: #FFFFFF; font-family: 'Courier New', monospace; }}
      .archetype-tagline {{ font-size: 11px; fill: {primary}; font-family: 'Courier New', monospace; }}
      .label {{ font-size: 9px; fill: #888888; font-family: 'Courier New', monospace; letter-spacing: 2px; }}
      @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} }}
    </style>
  </defs>
  
  <!-- Background -->
  <rect width="480" height="120" rx="8" fill="#0D1117"/>
  <rect width="480" height="120" rx="8" fill="url(#archGrad)" opacity="0.15"/>
  
  <!-- Border -->
  <rect width="480" height="120" rx="8" fill="none" stroke="{primary}" stroke-width="1" opacity="0.4"/>
  
  <!-- Corner accents -->
  <line x1="0" y1="20" x2="20" y2="0" stroke="{primary}" stroke-width="1.5" opacity="0.8"/>
  <line x1="460" y1="0" x2="480" y2="20" stroke="{primary}" stroke-width="1.5" opacity="0.8"/>
  <line x1="0" y1="100" x2="20" y2="120" stroke="{primary}" stroke-width="1.5" opacity="0.8"/>
  <line x1="460" y1="120" x2="480" y2="100" stroke="{primary}" stroke-width="1.5" opacity="0.8"/>
  
  <!-- Sigil -->
  <text x="55" y="72" text-anchor="middle" class="sigil">{sigil}</text>
  
  <!-- Divider -->
  <line x1="90" y1="20" x2="90" y2="100" stroke="{primary}" stroke-width="0.5" opacity="0.3"/>
  
  <!-- Text content -->
  <text x="106" y="38" class="label">// DEVELOPER ARCHETYPE</text>
  <text x="106" y="65" class="archetype-name">{name.upper()}</text>
  <text x="106" y="85" class="archetype-tagline">"{tagline}"</text>
  
  <!-- Scan line animation -->
  <rect x="0" y="0" width="480" height="2" fill="{primary}" opacity="0.1">
    <animateTransform attributeName="transform" type="translate" from="0,0" to="0,120" dur="3s" repeatCount="indefinite"/>
  </rect>
</svg>"""


if __name__ == "__main__":
    # Test with a sample profile
    test_profile = GitHubProfile(
        username="testuser",
        total_repos=25,
        total_stars_received=450,
        total_commits_last_year=680,
        total_prs=45,
        total_issues_opened=80,
        total_issues_closed=70,
        total_pr_reviews=35,
        languages={"Python": 50000, "TypeScript": 30000, "Rust": 15000, "Go": 5000},
        commit_hours=[23, 0, 1, 22, 23, 14, 15, 10, 23, 0],
        contribution_by_week=[5, 30, 45, 2, 0, 60, 55, 3, 1, 70],
        external_pr_count=18,
        follower_count=150,
        following_count=80,
        org_count=4,
        avg_repo_age_days=280,
        has_website=True,
        top_repo_stars=210,
    )
    
    archetype_key, confidence, all_scores = classify_archetype(test_profile)
    archetype = get_archetype_display(archetype_key)
    
    print(f"\n{'='*60}")
    print(f"  FORGE ARCHETYPE CLASSIFICATION")
    print(f"{'='*60}")
    print(f"\n  Archetype: {archetype['sigil']} {archetype['name']}")
    print(f"  Tagline:   {archetype['tagline']}")
    print(f"  Confidence: {confidence:.0%}")
    print(f"\n  Power:  {archetype['power']}")
    print(f"  Shadow: {archetype['shadow']}")
    print(f"\n  Top 5 scores:")
    sorted_scores = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    for k, v in sorted_scores[:5]:
        bar = "█" * int(v * 20) + "░" * (20 - int(v * 20))
        print(f"  {k:<25} {bar} {v:.0%}")
