# src/scheduler/autonomous_scheduler.py
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from config import load_channels, ChannelConfig
from src.scheduler.matchday_calendar import (
    get_current_matchday_context,
    MatchdayScheduleContext,
    SchedulePhase,
    PHASE_DEFINITIONS,
)

logger = logging.getLogger(__name__)

# 4x Daily Cadence Schedule Slots (UTC times)
CADENCE_SLOTS: List[Dict[str, Any]] = [
    {
        "slot_id": 1,
        "name": "Morning Transfer Radar & Price Watch",
        "utc_time": "08:30",
        "phase": SchedulePhase.TRANSFER_RADAR,
        "theme_badge": "TRANSFER RADAR",
        "topic_suffix": "Top 3 Most Bought, Most Sold & Impending Price Changes",
    },
    {
        "slot_id": 2,
        "name": "Midday FPL Scout & Armband Lock",
        "utc_time": "12:30",
        "phase": SchedulePhase.FPL_PREVIEW,
        "theme_badge": "FPL SCOUT",
        "topic_suffix": "Gameweek Captaincy Lock, Price Metrics & Sub-10% Differentials",
    },
    {
        "slot_id": 3,
        "name": "Afternoon Injury Intel & Press Brief",
        "utc_time": "16:30",
        "phase": SchedulePhase.INJURY_INTEL,
        "theme_badge": "INJURY INTEL",
        "topic_suffix": "Breaking Injury News, Sidelined Stars & Top 3 Direct Replacements",
    },
    {
        "slot_id": 4,
        "name": "Evening Match Debrief & Top 3 FPL Stars",
        "utc_time": "20:30",
        "phase": SchedulePhase.POST_MATCH_DEBRIEF,
        "theme_badge": "MATCH DEBRIEF",
        "topic_suffix": "Full-Time Scoreline, Top 3 FPL Points Earners & Tactical Autopsy",
    },
]


class MatchdayAutonomousScheduler:
    """Manages multi-post daily matchday scheduling and continuous daemon execution."""

    def __init__(self, channel_key: str = "matchday"):
        self.channel_key = channel_key
        self.channels = load_channels()
        self.channel = self.channels.get(channel_key)

    def get_current_slot(self) -> Dict[str, Any]:
        """Determine which schedule slot is most appropriate for the current UTC hour."""
        current_hour = datetime.now(timezone.utc).hour
        if current_hour < 11:
            return CADENCE_SLOTS[0]  # 08:30 Transfer Radar
        elif current_hour < 15:
            return CADENCE_SLOTS[1]  # 12:30 FPL Scout
        elif current_hour < 19:
            return CADENCE_SLOTS[2]  # 16:30 Injury Intel
        else:
            return CADENCE_SLOTS[3]  # 20:30 Match Debrief

    def build_slot_context(self, slot_id: Optional[int] = None) -> MatchdayScheduleContext:
        """Build dynamic MatchdayScheduleContext tailored for the selected slot."""
        slot = next((s for s in CADENCE_SLOTS if s["slot_id"] == slot_id), None) if slot_id else self.get_current_slot()
        phase_def = PHASE_DEFINITIONS.get(slot["phase"], PHASE_DEFINITIONS[SchedulePhase.POST_MATCH_DEBRIEF])

        return MatchdayScheduleContext(
            phase=slot["phase"],
            phase_name=f"{slot['name']} ({phase_def['phase_name']})",
            theme_badge=slot["theme_badge"],
            badge_color=phase_def["badge_color"],
            topic_focus=f"{slot['name']}: {slot['topic_suffix']}",
            default_topic=f"{slot['name']}: {slot['topic_suffix']}",
            prompt_guidance=phase_def["prompt_guidance"],
            narrative_arc=phase_def["narrative_arc"],
            suggested_hashtags=phase_def["suggested_hashtags"],
        )

    def print_crontab_instructions(self) -> str:
        """Generate ready-to-use Linux crontab configuration for VPS deployment."""
        py_path = sys.executable
        script_dir = Path(__file__).resolve().parent.parent.parent
        cron_text = f"""# ==============================================================================
# Matchday EPL 4x Daily Autonomous Publishing Engine Crontab
# ==============================================================================
# Morning Transfer Radar & Price Watch (08:30 UTC / 09:30 BST)
30 8 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 1 >> cron.log 2>&1

# Midday FPL Scout & Armband Lock (12:30 UTC / 13:30 BST)
30 12 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 2 >> cron.log 2>&1

# Afternoon Injury Intel & Press Brief (16:30 UTC / 17:30 BST)
30 16 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 3 >> cron.log 2>&1

# Evening Match Debrief & Top 3 FPL Stars (20:30 UTC / 21:30 BST)
30 20 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 4 >> cron.log 2>&1
# ==============================================================================
"""
        return cron_text
