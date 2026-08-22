# src/scheduler/fpl_client.py
import requests
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"


class FPLClient:
    """Client for the official Fantasy Premier League API providing fixtures, live match stats, injuries, and transfer trends."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

    def _get_bootstrap_and_fixtures(self):
        bootstrap = self.session.get(FPL_BOOTSTRAP_URL, timeout=10).json()
        fixtures = self.session.get(FPL_FIXTURES_URL, timeout=10).json()
        return bootstrap, fixtures

    def fetch_gameweek_intel(self) -> Dict[str, Any]:
        """Fetches active gameweek, fixtures, marquee matches, and top captain assets."""
        try:
            bootstrap, fixtures_raw = self._get_bootstrap_and_fixtures()
        except Exception as e:
            logger.error(f"Failed to fetch from FPL API: {e}")
            return self._get_fallback_intel()

        teams_map = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
        events = bootstrap.get("events", [])
        next_event = next((e for e in events if e.get("is_next") or e.get("is_current")), events[0] if events else None)
        gw_id = next_event["id"] if next_event else 1
        gw_name = next_event["name"] if next_event else "Gameweek 1"
        deadline = next_event.get("deadline_time", "") if next_event else ""

        gw_fixtures = [f for f in fixtures_raw if f.get("event") == gw_id]
        parsed_fixtures = []
        for f in gw_fixtures[:5]:
            h_team = teams_map.get(f.get("team_h"), "Home")
            a_team = teams_map.get(f.get("team_a"), "Away")
            parsed_fixtures.append(f"{h_team} vs {a_team}")

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

    def fetch_latest_match_debrief(self) -> Optional[Dict[str, Any]]:
        """Fetches the latest finished / active match with top 3 FPL point/BPS performers."""
        try:
            bootstrap, fixtures_raw = self._get_bootstrap_and_fixtures()
            teams_map = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
            elements_map = {e["id"]: e for e in bootstrap.get("elements", [])}

            # Find started / finished matches
            started_matches = [f for f in fixtures_raw if f.get("started") or f.get("finished")]
            if not started_matches:
                return None

            latest_match = started_matches[-1]
            h_team = teams_map.get(latest_match["team_h"], "Home")
            a_team = teams_map.get(latest_match["team_a"], "Away")
            h_score = latest_match.get("team_h_score", 0)
            a_score = latest_match.get("team_a_score", 0)

            # Extract top BPS performers & bonus points
            stats = latest_match.get("stats", [])
            bps_stats = next((s for s in stats if s["identifier"] == "bps"), None)
            bonus_stats = next((s for s in stats if s["identifier"] == "bonus"), None)
            goals_stats = next((s for s in stats if s["identifier"] == "goals_scored"), None)
            assists_stats = next((s for s in stats if s["identifier"] == "assists"), None)

            all_player_scores = []
            if bps_stats:
                h_bps = bps_stats.get("h", [])
                a_bps = bps_stats.get("a", [])
                for item in h_bps + a_bps:
                    el_id = item["element"]
                    bps_val = item["value"]
                    el = elements_map.get(el_id, {})
                    if not el:
                        continue
                    
                    # Compute bonus
                    bonus_val = 0
                    if bonus_stats:
                        for b in bonus_stats.get("h", []) + bonus_stats.get("a", []):
                            if b["element"] == el_id:
                                bonus_val = b["value"]
                    
                    # Compute goals and assists
                    goals = sum(g["value"] for g in (goals_stats.get("h", []) + goals_stats.get("a", [])) if g["element"] == el_id) if goals_stats else 0
                    assists = sum(a["value"] for a in (assists_stats.get("h", []) + assists_stats.get("a", [])) if a["element"] == el_id) if assists_stats else 0
                    
                    # Approximate points: 4-5 pts for goal, 3 pts for assist, + bonus, + clean sheet (if def/gk)
                    pos_type = el.get("element_type", 3)
                    goal_pts = (6 if pos_type in [1, 2] else (5 if pos_type == 3 else 4)) * goals
                    assist_pts = 3 * assists
                    cs_pts = 4 if pos_type in [1, 2] and ((el.get("team") == latest_match["team_h"] and a_score == 0) or (el.get("team") == latest_match["team_a"] and h_score == 0)) else 0
                    appear_pts = 2 if latest_match.get("minutes", 0) >= 60 else 1
                    total_pts = appear_pts + goal_pts + assist_pts + cs_pts + bonus_val

                    all_player_scores.append({
                        "name": el.get("web_name", "Player"),
                        "team": teams_map.get(el.get("team"), ""),
                        "cost": f"£{el.get('now_cost', 0) / 10:.1f}m",
                        "bps": bps_val,
                        "bonus": bonus_val,
                        "goals": goals,
                        "assists": assists,
                        "points": total_pts,
                    })

            all_player_scores.sort(key=lambda x: (x["points"], x["bps"]), reverse=True)
            top_3 = all_player_scores[:3]

            return {
                "fixture_id": latest_match["id"],
                "home_team": h_team,
                "away_team": a_team,
                "home_score": h_score,
                "away_score": a_score,
                "scoreline": f"{h_team} {h_score} - {a_score} {a_team}",
                "top_performers": top_3,
                "gameweek_id": latest_match.get("event", 1),
            }
        except Exception as e:
            logger.error(f"Error fetching latest match debrief: {e}")
            return None

    def fetch_top_injury_alert(self) -> Optional[Dict[str, Any]]:
        """Fetches the most high-profile active injury news and recommended FPL replacements."""
        try:
            bootstrap, _ = self._get_bootstrap_and_fixtures()
            teams_map = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
            elements = bootstrap.get("elements", [])

            # High ownership flagged assets
            flagged = [
                e for e in elements
                if e.get("status") in ["i", "d", "s"] and e.get("news")
            ]
            flagged.sort(key=lambda x: float(x.get("selected_by_percent", 0.0)), reverse=True)
            if not flagged:
                return None

            injured = flagged[0]
            pos_type = injured.get("element_type", 3)
            cost_max = injured.get("now_cost", 100) + 5

            # Find healthy direct replacements in same position & similar price
            healthy_replacements = [
                e for e in elements
                if e.get("status") == "a" and e.get("element_type") == pos_type and e.get("now_cost", 0) <= cost_max and e["id"] != injured["id"]
            ]
            healthy_replacements.sort(key=lambda x: float(x.get("selected_by_percent", 0.0)), reverse=True)

            replacements = []
            for r in healthy_replacements[:3]:
                replacements.append({
                    "name": r["web_name"],
                    "team": teams_map.get(r["team"], ""),
                    "cost": f"£{r['now_cost'] / 10:.1f}m",
                    "ownership": f"{r['selected_by_percent']}%",
                })

            return {
                "player_name": injured["web_name"],
                "team": teams_map.get(injured["team"], ""),
                "cost": f"£{injured['now_cost'] / 10:.1f}m",
                "ownership": f"{injured['selected_by_percent']}%",
                "status": injured.get("status"),
                "news": injured.get("news", "Sidelined"),
                "chance_of_playing": injured.get("chance_of_playing_next_round", 0),
                "replacements": replacements,
            }
        except Exception as e:
            logger.error(f"Error fetching injury alert: {e}")
            return None

    def fetch_transfer_radar(self) -> Dict[str, Any]:
        """Fetches top 3 most transferred IN (risers) and top 3 most transferred OUT (fallers)."""
        try:
            bootstrap, _ = self._get_bootstrap_and_fixtures()
            teams_map = {t["id"]: t["name"] for t in bootstrap.get("teams", [])}
            elements = bootstrap.get("elements", [])

            # Most transferred in
            elements_in = sorted(elements, key=lambda x: x.get("transfers_in_event", 0), reverse=True)
            top_buys = []
            for p in elements_in[:3]:
                top_buys.append({
                    "name": p["web_name"],
                    "team": teams_map.get(p["team"], ""),
                    "cost": f"£{p['now_cost'] / 10:.1f}m",
                    "transfers": f"+{p.get('transfers_in_event', 0):,}",
                    "ownership": f"{p['selected_by_percent']}%",
                })

            # Most transferred out
            elements_out = sorted(elements, key=lambda x: x.get("transfers_out_event", 0), reverse=True)
            top_sells = []
            for p in elements_out[:3]:
                top_sells.append({
                    "name": p["web_name"],
                    "team": teams_map.get(p["team"], ""),
                    "cost": f"£{p['now_cost'] / 10:.1f}m",
                    "transfers": f"-{p.get('transfers_out_event', 0):,}",
                    "ownership": f"{p['selected_by_percent']}%",
                })

            return {
                "top_buys": top_buys,
                "top_sells": top_sells,
            }
        except Exception as e:
            logger.error(f"Error fetching transfer radar: {e}")
            return {"top_buys": [], "top_sells": []}

    def _get_fallback_intel(self) -> Dict[str, Any]:
        return {
            "gameweek_id": 1,
            "gameweek_name": "Gameweek 1",
            "deadline": "Friday 18:30 BST",
            "key_fixtures": ["Arsenal vs Coventry City", "Man City vs Bournemouth", "Chelsea vs Brighton"],
            "top_captains": [
                {"name": "Haaland", "team": "Man City", "cost": "£15.5m", "selected_by": "73.7%"},
                {"name": "Saka", "team": "Arsenal", "cost": "£10.0m", "selected_by": "34.1%"},
            ],
            "differential": {"name": "Eze", "team": "Arsenal", "cost": "£7.5m", "selected_by": "9.8%"},
        }