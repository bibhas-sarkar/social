# src/scheduler/autonomous_scheduler.py
import os
import sys
import time
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
        "name": "Morning Fixture Intel",
        "utc_time": "08:30",
        "phase": SchedulePhase.PRE_MATCH_PREVIEW,
        "theme_badge": "FIXTURE INTEL",
        "topic_suffix": "Tactical Head-to-Head, Predicted Lineups & High-Press Systems",
    },
    {
        "slot_id": 2,
        "name": "Midday FPL Scout & Armband",
        "utc_time": "12:30",
        "phase": SchedulePhase.FPL_PREVIEW,
        "theme_badge": "FPL SCOUT",
        "topic_suffix": "Gameweek 1 Captaincy Lock, Price Metrics & Sub-10% Differentials",
    },
    {
        "slot_id": 3,
        "name": "Afternoon Opta Data Blueprint",
        "utc_time": "16:30",
        "phase": SchedulePhase.MIDWEEK_ANALYSIS,
        "theme_badge": "TACTICAL BLUEPRINT",
        "topic_suffix": "Opta xG Creation, Defensive Recovery Lines & Passing Networks",
    },
    {
        "slot_id": 4,
        "name": "Evening Matchday Debrief & Debate",
        "utc_time": "20:30",
        "phase": SchedulePhase.LIVE_MATCH_REACTION,
        "theme_badge": "MATCHDAY LIVE",
        "topic_suffix": "Matchday Hot Takes, Clinical Finishing Trends & Fan Prediction Debate",
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
            return CADENCE_SLOTS[0]  # 08:30 Morning slot
        elif current_hour < 15:
            return CADENCE_SLOTS[1]  # 12:30 Midday FPL slot
        elif current_hour < 19:
            return CADENCE_SLOTS[2]  # 16:30 Opta Blueprint slot
        else:
            return CADENCE_SLOTS[3]  # 20:30 Evening Debrief slot

    def build_slot_context(self, slot_id: Optional[int] = None) -> MatchdayScheduleContext:
        """Build dynamic MatchdayScheduleContext tailored for the selected slot."""
        slot = next((s for s in CADENCE_SLOTS if s["slot_id"] == slot_id), None) if slot_id else self.get_current_slot()
        phase_def = PHASE_DEFINITIONS.get(slot["phase"], PHASE_DEFINITIONS[SchedulePhase.GW1_LAUNCH])

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
# Morning Fixture Intel (08:30 UTC / 09:30 BST)
30 8 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 1 >> cron.log 2>&1

# Midday FPL Scout & Armband Lock (12:30 UTC / 13:30 BST)
30 12 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 2 >> cron.log 2>&1

# Afternoon Opta Tactical Blueprint (16:30 UTC / 17:30 BST)
30 16 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 3 >> cron.log 2>&1

# Evening Debrief & Community Debate (20:30 UTC / 21:30 BST)
30 20 * * * cd {script_dir} && {py_path} main.py --channel matchday --slot 4 >> cron.log 2>&1
# ==============================================================================
"""
        return cron_text
