"""
FORGE — Developer Pulse Generator
===================================
Generates a unique, animated SVG "Developer Pulse" — a waveform
visualization of your contribution history that looks like a heartbeat
monitor or audio oscilloscope. No two pulses look the same.

Unlike static contribution graphs, this:
  - Animates like a live signal
  - Has a unique "signature" shape based on your actual data
  - Encodes contribution intensity in the waveform amplitude
  - Uses your archetype's color palette
"""

import math
import random
from typing import List, Optional


def generate_pulse_path(contributions: List[int], width: int = 800, height: int = 100) -> str:
    """
    Convert weekly contribution counts into an SVG path for the pulse visualization.
    
    The waveform uses a combination of your actual data (amplitude) with 
    a smooth interpolation to create an organic, unique-looking signal.
    """
    if not contributions:
        contributions = [0] * 52
    
    # Normalize to 0-1 range
    max_contrib = max(contributions) or 1
    normalized = [c / max_contrib for c in contributions]
    
    # Generate path points
    n = len(normalized)
    step = width / n
    center_y = height / 2
    amplitude = height * 0.42
    
    points = []
    for i, value in enumerate(normalized):
        x = i * step
        # Combine actual contribution data with a sine wave for organic feel
        y_offset = value * amplitude
        # Add slight harmonic for visual interest
        harmonic = math.sin(i * 0.5) * amplitude * 0.08 * value
        y = center_y - y_offset - harmonic
        points.append((x, y))
    
    # Build smooth SVG path using cubic bezier curves
    if len(points) < 2:
        return ""
    
    path = f"M {points[0][0]:.1f},{points[0][1]:.1f}"
    
    for i in range(1, len(points)):
        # Control points for smooth curve
        cp1x = points[i-1][0] + step * 0.4
        cp1y = points[i-1][1]
        cp2x = points[i][0] - step * 0.4
        cp2y = points[i][1]
        path += f" C {cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {points[i][0]:.1f},{points[i][1]:.1f}"
    
    # Close path to bottom for fill
    path += f" L {points[-1][0]:.1f},{height} L {points[0][0]:.1f},{height} Z"
    
    return path


def generate_pulse_line_path(contributions: List[int], width: int = 800, height: int = 100) -> str:
    """Generate just the line (not filled) for the top stroke."""
    if not contributions:
        contributions = [0] * 52
    
    max_contrib = max(contributions) or 1
    normalized = [c / max_contrib for c in contributions]
    
    n = len(normalized)
    step = width / n
    center_y = height / 2
    amplitude = height * 0.42
    
    points = []
    for i, value in enumerate(normalized):
        x = i * step
        y_offset = value * amplitude
        harmonic = math.sin(i * 0.5) * amplitude * 0.08 * value
        y = center_y - y_offset - harmonic
        points.append((x, y))
    
    if len(points) < 2:
        return ""
    
    path = f"M {points[0][0]:.1f},{points[0][1]:.1f}"
    
    for i in range(1, len(points)):
        cp1x = points[i-1][0] + step * 0.4
        cp1y = points[i-1][1]
        cp2x = points[i][0] - step * 0.4
        cp2y = points[i][1]
        path += f" C {cp1x:.1f},{cp1y:.1f} {cp2x:.1f},{cp2y:.1f} {points[i][0]:.1f},{points[i][1]:.1f}"
    
    return path


def generate_grid_lines(width: int, height: int, cols: int = 12, rows: int = 4) -> str:
    """Generate subtle grid lines for the oscilloscope background."""
    lines = []
    
    for i in range(1, cols):
        x = (width / cols) * i
        lines.append(f'<line x1="{x:.0f}" y1="0" x2="{x:.0f}" y2="{height}" stroke="currentColor" stroke-width="0.5" opacity="0.08"/>')
    
    for i in range(1, rows):
        y = (height / rows) * i
        lines.append(f'<line x1="0" y1="{y:.0f}" x2="{width}" y2="{y:.0f}" stroke="currentColor" stroke-width="0.5" opacity="0.08"/>')
    
    return "\n  ".join(lines)


def render_pulse_svg(
    contributions: List[int],
    username: str,
    primary_color: str = "#00FF9F",
    secondary_color: str = "#0099FF",
    total_contributions: Optional[int] = None,
    streak_days: Optional[int] = None,
    year: int = 2024,
    width: int = 860,
    height: int = 130,
) -> str:
    """
    Render the full Developer Pulse SVG.
    
    This is the signature visual that makes FORGE profiles instantly recognizable.
    It looks like a medical/audio oscilloscope, but it's actually your GitHub story.
    """
    fill_path = generate_pulse_path(contributions, width - 40, height - 40)
    line_path = generate_pulse_line_path(contributions, width - 40, height - 40)
    grid = generate_grid_lines(width - 40, height - 40)
    
    total_str = f"{total_contributions:,}" if total_contributions else "—"
    streak_str = f"{streak_days}d" if streak_days else "—"
    
    return f"""<svg width="{width}" height="{height + 50}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height + 50}">
  <defs>
    <linearGradient id="pulseGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:{primary_color};stop-opacity:0.35"/>
      <stop offset="100%" style="stop-color:{primary_color};stop-opacity:0.02"/>
    </linearGradient>
    <linearGradient id="lineGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:{secondary_color};stop-opacity:0.6"/>
      <stop offset="40%" style="stop-color:{primary_color};stop-opacity:1"/>
      <stop offset="100%" style="stop-color:{secondary_color};stop-opacity:0.6"/>
    </linearGradient>
    <filter id="pulseGlow">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="pulseClip">
      <rect x="20" y="10" width="{width - 40}" height="{height - 20}"/>
    </clipPath>
    <style>
      .pulse-label {{ font: 9px 'Courier New', monospace; fill: #666; letter-spacing: 1.5px; }}
      .pulse-value {{ font: 700 13px 'Courier New', monospace; fill: {primary_color}; }}
    </style>
  </defs>
  
  <!-- Outer container -->
  <rect width="{width}" height="{height + 50}" rx="6" fill="#0D1117"/>
  <rect width="{width}" height="{height + 50}" rx="6" fill="none" stroke="{primary_color}" stroke-width="0.8" opacity="0.25"/>
  
  <!-- Top label -->
  <text x="24" y="22" class="pulse-label">DEVELOPER PULSE — {year} CONTRIBUTION SIGNAL</text>
  
  <!-- Oscilloscope grid (clipped) -->
  <g clip-path="url(#pulseClip)" transform="translate(20, 30)">
    {grid}
    
    <!-- Filled waveform -->
    <path d="{fill_path}" fill="url(#pulseGrad)" clip-path="url(#pulseClip)"/>
    
    <!-- Glowing line -->
    <path d="{line_path}" fill="none" stroke="url(#lineGrad)" stroke-width="2.5" 
          filter="url(#pulseGlow)" clip-path="url(#pulseClip)"/>
    
    <!-- Secondary faded line (echo effect) -->
    <path d="{line_path}" fill="none" stroke="{primary_color}" stroke-width="1" 
          opacity="0.15" transform="translate(0, 4)" clip-path="url(#pulseClip)"/>
  </g>
  
  <!-- Live indicator dot -->
  <circle cx="{width - 30}" cy="22" r="4" fill="{primary_color}">
    <animate attributeName="opacity" values="1;0.3;1" dur="1.5s" repeatCount="indefinite"/>
  </circle>
  <text x="{width - 22}" y="26" class="pulse-label" text-anchor="end">LIVE</text>
  
  <!-- Stats bar at bottom -->
  <line x1="20" y1="{height + 28}" x2="{width - 20}" y2="{height + 28}" 
        stroke="{primary_color}" stroke-width="0.5" opacity="0.2"/>
  
  <text x="30" y="{height + 44}" class="pulse-label">TOTAL CONTRIBUTIONS</text>
  <text x="30" y="{height + 60}" class="pulse-value">{total_str}</text>
  
  <text x="{width // 2 - 40}" y="{height + 44}" class="pulse-label">CURRENT STREAK</text>
  <text x="{width // 2 - 40}" y="{height + 60}" class="pulse-value">{streak_str}</text>
  
  <text x="{width - 30}" y="{height + 44}" text-anchor="end" class="pulse-label">SIGNAL</text>
  <text x="{width - 30}" y="{height + 60}" text-anchor="end" class="pulse-value">ACTIVE ◈</text>
</svg>"""


if __name__ == "__main__":
    # Test with synthetic data
    import random
    random.seed(42)
    
    # Simulate a sprinter's contribution pattern
    test_data = []
    for week in range(52):
        if week % 8 < 2:
            test_data.append(random.randint(40, 80))
        elif week % 8 < 3:
            test_data.append(random.randint(15, 30))
        else:
            test_data.append(random.randint(0, 5))
    
    svg = render_pulse_svg(
        contributions=test_data,
        username="testuser",
        primary_color="#00FF9F",
        secondary_color="#0099FF",
        total_contributions=847,
        streak_days=12,
        year=2024,
    )
    
    with open("/tmp/test_pulse.svg", "w") as f:
        f.write(svg)
    
    print("✓ Pulse SVG generated at /tmp/test_pulse.svg")
    print(f"  Weeks of data: {len(test_data)}")
    print(f"  Peak week: {max(test_data)} contributions")
    print(f"  SVG size: {len(svg)} bytes")
