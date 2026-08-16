from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class SchedulePhase(str, Enum):
    """Publishing cadence phases across the Premier League weekly cycle."""
    GW1_LAUNCH = "GW1_LAUNCH"
    POST_MATCH_WRAP = "POST_MATCH_WRAP"
    MIDWEEK_ANALYSIS = "MIDWEEK_ANALYSIS"
    FPL_PREVIEW = "FPL_PREVIEW"
    PRE_MATCH_PREVIEW = "PRE_MATCH_PREVIEW"
    LIVE_MATCH_REACTION = "LIVE_MATCH_REACTION"


class MatchdayScheduleContext(BaseModel):
    """Dynamic schedule context passed to AI agents and rendering templates."""
    phase: SchedulePhase
    phase_name: str
    theme_badge: str
    badge_color: str
    topic_focus: str
    default_topic: str
    prompt_guidance: str
    opening_fixture: str = "Arsenal vs Coventry City (Emirates Stadium)"
    narrative_arc: List[str] = Field(default_factory=list)
    suggested_hashtags: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


PHASE_DEFINITIONS: Dict[SchedulePhase, dict] = {
    SchedulePhase.GW1_LAUNCH: {
        "phase_name": "Premier League Season Kickoff & GW1",
        "theme_badge": "SEASON LAUNCH",
        "badge_color": "#00FF87",  # Emerald Green
        "topic_focus": "Premier League Kickoff: Arsenal vs Coventry City opener, summer transfers & GW1 FPL lock",
        "default_topic": "Premier League Kickoff: Arsenal vs Coventry City & GW1 Essentials",
        "prompt_guidance": (
            "The 2026/27 Premier League campaign officially starts this week. The opening fixture is "
            "Arsenal vs newly-promoted Coventry City at the Emirates. Connect the narrative: "
            "Season kickoff hype -> Arsenal vs Coventry fixture tactical key -> summer transfer reinforcement -> "
            "Gameweek 1 FPL captaincy pick -> fan prediction debate."
        ),
        "narrative_arc": [
            "Slide 1 (Hook): Season return & Arsenal vs Coventry City Emirates opener",
            "Slide 2 (Match Focus): Tactical preview & opening day metric for Arsenal vs Coventry",
            "Slide 3 (Transfer / Squad): Confirmed summer transfer impact and team depth",
            "Slide 4 (FPL GW1): Essential Gameweek 1 captain pick and differential asset",
            "Slide 5 (Debate): Opening weekend score prediction prompt"
        ],
        "suggested_hashtags": ["#PremierLeague", "#PLKickoff", "#Arsenal", "#CoventryCity", "#FPL", "#MatchdayEPL"],
    },
    SchedulePhase.FPL_PREVIEW: {
        "phase_name": "FPL Scout & Gameweek Intel",
        "theme_badge": "FPL SCOUT",
        "badge_color": "#F59E0B",  # Vibrant Amber
        "topic_focus": "Fantasy Premier League captaincy picks, differentials, and fixture swings",
        "default_topic": "Gameweek 1 FPL Captain Essentials & Premium Differentials",
        "prompt_guidance": (
            "Focus on Gameweek 1 FPL strategy: opening fixture difficulty, confirmed starters, "
            "set-piece takers, and captaincy ceiling picks."
        ),
        "narrative_arc": [
            "Slide 1 (Hook): GW1 FPL Deadline countdown and captaincy dilemma",
            "Slide 2 (Template Pick): Top captain asset metric and fixture upside",
            "Slide 3 (Transfer Impact): High-value summer signing priced under £7.5m",
            "Slide 4 (Differential): Sub-10% ownership differential with green FDR",
            "Slide 5 (Debate): Who is your GW1 captain?"
        ],
        "suggested_hashtags": ["#FPL", "#FPLCommunity", "#FPLScout", "#FPLTips", "#FPLGW1"],
    },
    SchedulePhase.PRE_MATCH_PREVIEW: {
        "phase_name": "Weekend Fixture Intel & Head-to-Head",
        "theme_badge": "FIXTURE INTEL",
        "badge_color": "#A855F7",  # Royal Violet
        "topic_focus": "Arsenal vs Coventry City opening clash tactical breakdown and predicted lineups",
        "default_topic": "Emirates Opener: Arsenal vs Coventry City Tactical Head-to-Head",
        "prompt_guidance": (
            "Break down the tactical dynamic between Mikel Arteta's system and newly-promoted Coventry City. "
            "Highlight pressing lines, potential debutants, and opening day trends."
        ),
        "narrative_arc": [
            "Slide 1 (Hook): Emirates season opener head-to-head preview",
            "Slide 2 (Tactical Blueprint): High-press intensity vs low-block counter",
            "Slide 3 (Squad News): Confirmed injury returns and starting XI battles",
            "Slide 4 (Key Metric): Historical opening match win rate and xG projection",
            "Slide 5 (Debate): Predict the opening day scoreline"
        ],
        "suggested_hashtags": ["#Arsenal", "#CoventryCity", "#EPLPreview", "#EmiratesStadium", "#MatchdayEPL"],
    },
    SchedulePhase.POST_MATCH_WRAP: {
        "phase_name": "Post-Match Statistical Wrap",
        "theme_badge": "POST-MATCH DEBRIEF",
        "badge_color": "#00FF87",  # Emerald Neon
        "topic_focus": "Gameweek 1 statistical debrief, xG over/underperformance, and opening day winners",
        "default_topic": "Gameweek 1 Debrief: Tactical Autopsy & Statistical Overperformers",
        "prompt_guidance": "Analyze opening gameweek results, high-turnover shot generation, and early table standings.",
        "narrative_arc": [
            "Slide 1 (Hook): Gameweek 1 summary and biggest opening day statement",
            "Slide 2 (Opta Metric): xG margin / defensive control stat block",
            "Slide 3 (Standout Player): Match winner tactical impact",
            "Slide 4 (Table Move): Early standings and title contenders check",
            "Slide 5 (Debate): Performance of the weekend vote"
        ],
        "suggested_hashtags": ["#PremierLeague", "#EPLDebrief", "#OptaStats", "#GW1Review"],
    },
    SchedulePhase.MIDWEEK_ANALYSIS: {
        "phase_name": "Midweek Tactical Breakdown",
        "theme_badge": "OPTA BREAKDOWN",
        "badge_color": "#00F0FF",  # Electric Cyan
        "topic_focus": "In-depth tactical systems, summer signing integration, and pressing data",
        "default_topic": "Tactical Breakdown: New Signings Integration & High-Press Evolution",
        "prompt_guidance": "Analyze tactical adjustments, ball progression patterns, and squad depth.",
        "narrative_arc": [
            "Slide 1 (Hook): Tactical evolution breakdown for the new campaign",
            "Slide 2 (Core Metric): Midfield recovery and transition data",
            "Slide 3 (System Shift): Manager tactical adjustments in pre-season",
            "Slide 4 (Player Spotlight): Key distributor / defensive anchor stats",
            "Slide 5 (Debate): Will this system win silverware?"
        ],
        "suggested_hashtags": ["#TacticalAnalysis", "#FootballTactics", "#OptaAnalysis"],
    },
    SchedulePhase.LIVE_MATCH_REACTION: {
        "phase_name": "Live Matchday Reaction & Highlights",
        "theme_badge": "MATCHDAY LIVE",
        "badge_color": "#EF4444",  # Crimson Red
        "topic_focus": "Real-time matchday reaction and immediate tactical talking points",
        "default_topic": "Matchday Live: Opening Fixture Key Moments & Scoreline Impact",
        "prompt_guidance": "Deliver instant matchday analysis, substitutions impact, and decisive stats.",
        "narrative_arc": [
            "Slide 1 (Hook): Final whistle reaction",
            "Slide 2 (Key Stat): Decisive metric (shots on target / xG)",
            "Slide 3 (Turning Point): Tactical substitution or red card shift",
            "Slide 4 (Standings): Instant table update",
            "Slide 5 (Debate): Rate the performance 1-10"
        ],
        "suggested_hashtags": ["#MatchdayLive", "#PremierLeagueLive", "#EPL"],
    },
}


def resolve_phase_from_datetime(dt: datetime) -> SchedulePhase:
    """Resolves season launch phase or weekly cadence based on calendar date and weekday."""
    # If in August before/around Gameweek 1, anchor to GW1 Launch
    if dt.month == 8 and dt.day <= 23:
        weekday = dt.weekday()
        if weekday in (3, 4):  # Thu / Fri
            return SchedulePhase.GW1_LAUNCH
        elif weekday in (5, 6):  # Sat / Sun
            return SchedulePhase.PRE_MATCH_PREVIEW
        else:
            return SchedulePhase.GW1_LAUNCH

    weekday = dt.weekday()
    if weekday == 0:
        return SchedulePhase.POST_MATCH_WRAP
    elif weekday in (1, 2):
        return SchedulePhase.MIDWEEK_ANALYSIS
    elif weekday == 3:
        return SchedulePhase.FPL_PREVIEW
    elif weekday == 4:
        return SchedulePhase.PRE_MATCH_PREVIEW
    else:
        return SchedulePhase.LIVE_MATCH_REACTION


def get_current_matchday_context(
    dt: Optional[datetime] = None,
    override_phase: Optional[str] = None,
) -> MatchdayScheduleContext:
    """Resolve and return full schedule context object."""
    current_dt = dt or datetime.now(timezone.utc)

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
        narrative_arc=def_data.get("narrative_arc", []),
        suggested_hashtags=def_data["suggested_hashtags"],
        timestamp=current_dt,
    )