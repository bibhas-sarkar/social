# src/scheduler/fpl_client.py
import requests
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"

class FPLClient:
    """Client for the official Fantasy Premier League API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

    def fetch_gameweek_intel(self) -> Dict[str, Any]:
        """Fetches active gameweek, fixtures, marquee matches, and top captain assets."""
        try:
            bootstrap = self.session.get(FPL_BOOTSTRAP_URL, timeout=10).json()
            fixtures_raw = self.session.get(FPL_FIXTURES_URL, timeout=10).json()
        except Exception as e:
            logger.error(f"Failed to fetch from FPL API: {e}")
            return self._get_fallback_intel()

        # 1. Map Teams
        teams_map = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}

        # 2. Find Next / Active Gameweek
        events = bootstrap.get("events", [])
        next_event = next((e for e in events if e.get("is_next") or e.get("is_current")), events[0] if events else None)
        gw_id = next_event["id"] if next_event else 1
        gw_name = next_event["name"] if next_event else "Gameweek 1"
        deadline = next_event.get("deadline_time", "") if next_event else ""

        # 3. Filter Fixtures for this Gameweek
        gw_fixtures = [f for f in fixtures_raw if f.get("event") == gw_id]
        parsed_fixtures = []
        for f in gw_fixtures[:5]:  # Top 5 matchups
            h_team = teams_map.get(f.get("team_h"), "Home")
            a_team = teams_map.get(f.get("team_a"), "Away")
            parsed_fixtures.append(f"{h_team} vs {a_team}")

        # 4. Extract Top Captain Assets (Sorted by Selected By % & Price)
        elements = bootstrap.get("elements", [])
        active_players = [p for p in elements if p.get("status") != "u"]
        active_players.sort(key=lambda x: float(x.get("selected_by_percent", 0.0)), reverse=True)

        top_captains = []
        for p in active_players[:3]:
            team_name = teams_map.get(p["team"], "")
            top_captains.append({
                "name": p["web_name"],
                "team": team_name,
                "cost": f"£{p['now_cost'] / 10:.1f}m",
                "selected_by": f"{p['selected_by_percent']}%",
                "news": p.get("news", "")
            })

        # 5. Extract Top Differential (<10% ownership, high value)
        differentials = [p for p in active_players if float(p.get("selected_by_percent", 0.0)) < 10.0 and (p.get("now_cost", 0) >= 65)]
        diff_player = differentials[0] if differentials else active_players[-1]
        top_diff = {
            "name": diff_player["web_name"],
            "team": teams_map.get(diff_player["team"], ""),
            "cost": f"£{diff_player['now_cost'] / 10:.1f}m",
            "selected_by": f"{diff_player['selected_by_percent']}%",
        }

        return {
            "gameweek_id": gw_id,
            "gameweek_name": gw_name,
            "deadline": deadline,
            "key_fixtures": parsed_fixtures,
            "top_captains": top_captains,
            "differential": top_diff,
        }

    def _get_fallback_intel(self) -> Dict[str, Any]:
        return {
            "gameweek_id": 1,
            "gameweek_name": "Gameweek 1",
            "deadline": "Friday 18:30 BST",
            "key_fixtures": ["Arsenal vs Coventry City", "Man City vs Bournemouth", "Chelsea vs Brighton"],
            "top_captains": [
                {"name": "Haaland", "team": "Man City", "cost": "£15.0m", "selected_by": "62.4%"},
                {"name": "Saka", "team": "Arsenal", "cost": "£10.0m", "selected_by": "34.1%"},
            ],
            "differential": {"name": "Mbeumo", "team": "Brentford", "cost": "£7.5m", "selected_by": "7.8%"},
        }