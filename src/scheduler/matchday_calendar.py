from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


class SchedulePhase(str, Enum):
    """Publishing cadence phases across the Premier League weekly cycle."""
    POST_MATCH_WRAP = "POST_MATCH_WRAP"
    MIDWEEK_ANALYSIS = "MIDWEEK_ANALYSIS"
    FPL_PREVIEW = "FPL_PREVIEW"
    PRE_MATCH_PREVIEW = "PRE_MATCH_PREVIEW"
    LIVE_MATCH_REACTION = "LIVE_MATCH_REACTION"


class MatchdayScheduleContext(BaseModel):
    """Rich dynamic schedule context passed to AI agents and rendering templates."""
    phase: SchedulePhase
    phase_name: str
    theme_badge: str
    badge_color: str
    topic_focus: str
    default_topic: str
    prompt_guidance: str
    suggested_hashtags: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


PHASE_DEFINITIONS = {
    SchedulePhase.POST_MATCH_WRAP: {
        "phase_name": "Post-Match Statistical Wrap",
        "theme_badge": "POST-MATCH DEBRIEF",
        "badge_color": "#A855F7",  # Royal Violet
        "topic_focus": "Weekend Premier League debrief, xG over/underperformance, and decisive moments",
        "default_topic": "Weekend Premier League Tactical Autopsy & Statistical Overperformers",
        "prompt_guidance": (
            "Focus on the biggest statistical takeaways from the completed weekend gameweek. "
            "Highlight xG margins, unexpected scorelines, pressing efficiency, and individual standout ratings."
        ),
        "suggested_hashtags": ["#PremierLeague", "#EPLDebrief", "#OptaStats", "#MatchdayReview", "#xGStats"],
    },
    SchedulePhase.MIDWEEK_ANALYSIS: {
        "phase_name": "Midweek Tactical Breakdown",
        "theme_badge": "OPTA BREAKDOWN",
        "badge_color": "#00F0FF",  # Electric Cyan
        "topic_focus": "In-depth tactical systems, pressing traps, transition data, and manager philosophies",
        "default_topic": "Arsenal vs Manchester City Tactical Blueprint & Midfield Dominance",
        "prompt_guidance": (
            "Perform a deep analytical masterclass on a specific tactical dynamic or team system. "
            "Use granular metrics like high turnovers, progressive passes, field tilt, and recovery zones."
        ),
        "suggested_hashtags": ["#TacticalAnalysis", "#FootballTactics", "#MidfieldMasterclass", "#OptaAnalysis"],
    },
    SchedulePhase.FPL_PREVIEW: {
        "phase_name": "FPL Scout & Gameweek Intel",
        "theme_badge": "FPL SCOUT",
        "badge_color": "#00FF87",  # Emerald Green
        "topic_focus": "Fantasy Premier League captaincy picks, differentials, injury flags, and FDR targets",
        "default_topic": "Gameweek Essential FPL Captains & High-Value Differentials",
        "prompt_guidance": (
            "Target Fantasy Premier League managers. Provide data-backed transfer targets, expected minutes, "
            "fixture difficulty rating (FDR), non-penalty xG+xA, and verified press-conference injury news."
        ),
        "suggested_hashtags": ["#FPL", "#FPLCommunity", "#FPLScout", "#FPLTips", "#FPLGameweek"],
    },
    SchedulePhase.PRE_MATCH_PREVIEW: {
        "phase_name": "Weekend Fixture Intel & Head-to-Head",
        "theme_badge": "FIXTURE INTEL",
        "badge_color": "#F59E0B",  # Vibrant Amber
        "topic_focus": "Marquee weekend clash preview, predicted XI, key head-to-head match-ups",
        "default_topic": "Weekend Marquee Clash: Tactical Head-to-Head & Key Battles",
        "prompt_guidance": (
            "Preview the marquee fixture of the upcoming weekend. Break down head-to-head records, "
            "predicted lineups, key 1v1 positional matchups, and manager tactical dilemmas."
        ),
        "suggested_hashtags": ["#MatchPreview", "#EPLPreview", "#HeadToHead", "#BigMatchFocus"],
    },
    SchedulePhase.LIVE_MATCH_REACTION: {
        "phase_name": "Live Matchday Reaction & Highlights",
        "theme_badge": "MATCHDAY LIVE",
        "badge_color": "#EF4444",  # Crimson Red
        "topic_focus": "Real-time matchday reaction, standout performances, and immediate tactical talking points",
        "default_topic": "Matchday Live: Key Tactical Adjustments & Match Winner Breakdown",
        "prompt_guidance": (
            "Deliver instant, high-energy matchday analysis. Highlight the key turning points, "
            "substitutions that changed the game, and standout statistical achievements from today's action."
        ),
        "suggested_hashtags": ["#MatchdayLive", "#EPL", "#PremierLeagueLive", "#GameChanger"],
    },
}


def resolve_phase_from_datetime(dt: datetime) -> SchedulePhase:
    """Resolve the weekly publishing phase based on weekday and hour (UTC/local).
    
    Weekly Schedule Mapping:
    - Monday (0): POST_MATCH_WRAP
    - Tuesday (1):
        - Before 12:00 -> POST_MATCH_WRAP
        - 12:00 and after -> MIDWEEK_ANALYSIS
    - Wednesday (2): MIDWEEK_ANALYSIS
    - Thursday (3): FPL_PREVIEW
    - Friday (4): PRE_MATCH_PREVIEW
    - Saturday (5): LIVE_MATCH_REACTION
    - Sunday (6): LIVE_MATCH_REACTION
    """
    weekday = dt.weekday()  # Monday is 0 and Sunday is 6
    hour = dt.hour

    if weekday == 0:
        return SchedulePhase.POST_MATCH_WRAP
    elif weekday == 1:
        return SchedulePhase.POST_MATCH_WRAP if hour < 12 else SchedulePhase.MIDWEEK_ANALYSIS
    elif weekday == 2:
        return SchedulePhase.MIDWEEK_ANALYSIS
    elif weekday == 3:
        return SchedulePhase.FPL_PREVIEW
    elif weekday == 4:
        return SchedulePhase.PRE_MATCH_PREVIEW
    else:  # Saturday (5) & Sunday (6)
        return SchedulePhase.LIVE_MATCH_REACTION


def get_current_matchday_context(
    dt: Optional[datetime] = None,
    override_phase: Optional[str] = None,
) -> MatchdayScheduleContext:
    """Resolve and return full schedule context object."""
    current_dt = dt or datetime.now()

    if override_phase:
        try:
            phase = SchedulePhase(override_phase.upper().strip())
        except ValueError:
            valid_phases = [p.value for p in SchedulePhase]
            raise ValueError(f"Invalid phase override '{override_phase}'. Valid phases: {valid_phases}")
    else:
        phase = resolve_phase_from_datetime(current_dt)

    def_data = PHASE_DEFINITIONS[phase]

    return MatchdayScheduleContext(
        phase=phase,
        phase_name=def_data["phase_name"],
        theme_badge=def_data["theme_badge"],
        badge_color=def_data["badge_color"],
        topic_focus=def_data["topic_focus"],
        default_topic=def_data["default_topic"],
        prompt_guidance=def_data["prompt_guidance"],
        suggested_hashtags=def_data["suggested_hashtags"],
        timestamp=current_dt,
    )
