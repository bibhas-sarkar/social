# src/scheduler/matchday_calendar.py
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class SchedulePhase(str, Enum):
    """Publishing cadence phases across the Premier League weekly cycle."""
    GW1_LAUNCH = "GW1_LAUNCH"
    POST_MATCH_DEBRIEF = "POST_MATCH_DEBRIEF"
    INJURY_INTEL = "INJURY_INTEL"
    TRANSFER_RADAR = "TRANSFER_RADAR"
    FPL_PREVIEW = "FPL_PREVIEW"
    PRE_MATCH_PREVIEW = "PRE_MATCH_PREVIEW"
    MIDWEEK_ANALYSIS = "MIDWEEK_ANALYSIS"
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
    SchedulePhase.POST_MATCH_DEBRIEF: {
        "phase_name": "Post-Match Debrief & Top 3 FPL Points Stars",
        "theme_badge": "MATCH DEBRIEF",
        "badge_color": "#00FF87",  # Emerald Neon
        "topic_focus": "Marquee match result, top 3 FPL bonus point earners, and tactical key takeaways",
        "default_topic": "Matchday Debrief: Scoreline, Top 3 FPL Performers & Tactical Takeaways",
        "prompt_guidance": (
            "Analyze the marquee Premier League match result. Feature the final scoreline, "
            "break down the Top 3 FPL points scorers with goals/assists/clean sheets and bonus points, "
            "and provide immediate transfer lookout recommendations."
        ),
        "narrative_arc": [
            "Slide 1 (Hook): Final Scoreline & Match Winner announcement",
            "Slide 2 (Top 3 FPL Stars): Top 3 point haulers podium with exact points & bonus",
            "Slide 3 (Tactical Blueprint): Decisive underlying stats, xG and key chance creation",
            "Slide 4 (FPL Transfer Lookout): Buy/Sell momentum and upcoming fixture swing",
            "Slide 5 (Debate): Who was your Man of the Match? Drop your verdict below!"
        ],
        "suggested_hashtags": [
            "#PremierLeague", "#FPL", "#FPLCommunity", "#MatchdayDebrief",
            "#Arsenal", "#PL", "#FantasyPremierLeague", "#EPL", "#OptaStats", "#MatchdayEPL"
        ],
    },
    SchedulePhase.INJURY_INTEL: {
        "phase_name": "Breaking Injury Alerts & FPL Replacement Radar",
        "theme_badge": "INJURY INTEL",
        "badge_color": "#EF4444",  # Crimson Red
        "topic_focus": "High-profile player injury updates, recovery timeline, and top 3 direct replacements",
        "default_topic": "Injury Alert: Star Sidelined & Top 3 FPL Direct Replacements",
        "prompt_guidance": (
            "Deliver breaking injury status for key Premier League assets. Highlight manager press conference "
            "updates, expected return dates, and scout top 3 healthy direct replacements in the same price tier."
        ),
        "narrative_arc": [
            "Slide 1 (Hook): Breaking Injury Alert with player name, club, and status",
            "Slide 2 (Medical Update): Injury details, expected return date, and manager quotes",
            "Slide 3 (Tactical Impact): How the club adapts formation and set-piece duty shifts",
            "Slide 4 (Replacement Radar): Top 3 healthy direct replacements with prices and ownership",
            "Slide 5 (Debate): Are you selling immediately or holding on the bench? Comment below!"
        ],
        "suggested_hashtags": [
            "#FPL", "#FPLInjuries", "#PremierLeague", "#FPLCommunity",
            "#FPLTips", "#FantasyPremierLeague", "#EPLNews", "#MatchdayEPL"
        ],
    },
    SchedulePhase.TRANSFER_RADAR: {
        "phase_name": "FPL Transfer Market Radar & Price Alerts",
        "theme_badge": "TRANSFER RADAR",
        "badge_color": "#00F0FF",  # Electric Cyan
        "topic_focus": "Market movers: top 3 most transferred IN (risers) and top 3 transferred OUT (fallers)",
        "default_topic": "Transfer Radar: Top Price Risers, Fallers & Deadline Strategy",
        "prompt_guidance": (
            "Track the biggest transfer market swings in FPL. Identify players on the verge of price rises "
            "and mass fire-sales, offering tactical advice to preserve team value."
        ),
        "narrative_arc": [
            "Slide 1 (Hook): Transfer Market Alert & Impending Price Changes",
            "Slide 2 (Price Risers): Top 3 most bought players with transfer volume",
            "Slide 3 (Price Fallers): Top 3 most sold players facing value drops",
            "Slide 4 (Strategy Watch): Value trap warning and fixture swing analysis",
            "Slide 5 (Debate): What is your priority transfer this gameweek? Comment below!"
        ],
        "suggested_hashtags": [
            "#FPL", "#FPLTransfers", "#FPLPriceChanges", "#FPLCommunity",
            "#PremierLeague", "#FPLScout", "#FantasyPL", "#MatchdayEPL"
        ],
    },
    SchedulePhase.FPL_PREVIEW: {
        "phase_name": "FPL Scout & Gameweek Armband Lock",
        "theme_badge": "FPL SCOUT",
        "badge_color": "#F59E0B",  # Vibrant Amber
        "topic_focus": "Fantasy Premier League captaincy picks, differentials, and fixture swings",
        "default_topic": "Gameweek FPL Captain Essentials & Premium Differentials",
        "prompt_guidance": (
            "Focus on upcoming Gameweek FPL strategy: captaincy ceiling picks, sub-10% differentials, "
            "and fixture difficulty ratings."
        ),
        "narrative_arc": [
            "Slide 1 (Hook): Gameweek Captaincy dilemma and deadline lock",
            "Slide 2 (Template Captain): Premium captain asset metric and fixture upside",
            "Slide 3 (Differential Watch): High-ceiling sub-10% ownership differential",
            "Slide 4 (Key Metric): Team ownership and projected points ceiling",
            "Slide 5 (Debate): Who gets your armband this weekend? Comment below!"
        ],
        "suggested_hashtags": [
            "#FPL", "#FPLCaptain", "#FPLScout", "#FPLCommunity",
            "#PremierLeague", "#FPLGW1", "#MatchdayEPL"
        ],
    },
    SchedulePhase.GW1_LAUNCH: {
        "phase_name": "Premier League Season Kickoff & GW1",
        "theme_badge": "SEASON LAUNCH",
        "badge_color": "#00FF87",  # Emerald Green
        "topic_focus": "Premier League Kickoff: Arsenal vs Coventry City opener, summer transfers & GW1 FPL lock",
        "default_topic": "Premier League Kickoff: Arsenal vs Coventry City & GW1 Essentials",
        "prompt_guidance": "The 2026/27 Premier League campaign officially starts this week.",
        "narrative_arc": [
            "Slide 1 (Hook): Season return & Arsenal vs Coventry City Emirates opener",
            "Slide 2 (Match Focus): Tactical preview & opening day metric for Arsenal vs Coventry",
            "Slide 3 (Transfer / Squad): Confirmed summer transfer impact and team depth",
            "Slide 4 (FPL GW1): Essential Gameweek 1 captain pick and differential asset",
            "Slide 5 (Debate): Opening weekend score prediction prompt"
        ],
        "suggested_hashtags": ["#PremierLeague", "#PLKickoff", "#Arsenal", "#CoventryCity", "#FPL", "#MatchdayEPL"],
    },
    SchedulePhase.PRE_MATCH_PREVIEW: {
        "phase_name": "Weekend Fixture Intel & Head-to-Head",
        "theme_badge": "FIXTURE INTEL",
        "badge_color": "#A855F7",  # Royal Violet
        "topic_focus": "Marquee opening clashes tactical breakdown and predicted lineups",
        "default_topic": "Matchday Fixture Intel: Tactical Head-to-Head & Key Clashes",
        "prompt_guidance": "Break down the tactical dynamic between marquee clubs.",
        "narrative_arc": [
            "Slide 1 (Hook): Marquee clash head-to-head preview",
            "Slide 2 (Tactical Blueprint): High-press intensity vs low-block counter",
            "Slide 3 (Squad News): Confirmed injury returns and starting XI battles",
            "Slide 4 (Key Metric): Historical opening match win rate and xG projection",
            "Slide 5 (Debate): Predict the matchday scoreline below!"
        ],
        "suggested_hashtags": ["#PremierLeague", "#EPLPreview", "#TacticalAnalysis", "#MatchdayEPL"],
    },
    SchedulePhase.MIDWEEK_ANALYSIS: {
        "phase_name": "Midweek Tactical Breakdown",
        "theme_badge": "OPTA BREAKDOWN",
        "badge_color": "#00F0FF",  # Electric Cyan
        "topic_focus": "In-depth tactical systems, summer signing integration, and pressing data",
        "default_topic": "Tactical Breakdown: New Signings Integration & High-Press Evolution",
        "prompt_guidance": "Analyze tactical adjustments, ball progression patterns, and squad depth.",
        "narrative_arc": [
            "Slide 1 (Hook): Tactical evolution breakdown for the campaign",
            "Slide 2 (Core Metric): Midfield recovery and transition data",
            "Slide 3 (System Shift): Manager tactical adjustments",
            "Slide 4 (Player Spotlight): Key distributor / defensive anchor stats",
            "Slide 5 (Debate): Will this system win silverware?"
        ],
        "suggested_hashtags": ["#TacticalAnalysis", "#FootballTactics", "#OptaAnalysis", "#MatchdayEPL"],
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
        "suggested_hashtags": ["#MatchdayLive", "#PremierLeagueLive", "#EPL", "#MatchdayEPL"],
    },
}


def resolve_phase_from_datetime(dt: datetime) -> SchedulePhase:
    """Resolves daily cadence phase based on time and day."""
    hour = dt.hour
    if hour < 11:
        return SchedulePhase.TRANSFER_RADAR  # Morning
    elif hour < 15:
        return SchedulePhase.FPL_PREVIEW     # Midday
    elif hour < 19:
        return SchedulePhase.INJURY_INTEL    # Afternoon
    else:
        return SchedulePhase.POST_MATCH_DEBRIEF  # Evening


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