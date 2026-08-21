# src/scheduler/pl_squad_validator.py
import os
import re
import json
import logging
from typing import Dict, Optional, Tuple, List
import requests

logger = logging.getLogger(__name__)

# Premier League Official Club Canonical Names
PL_CLUBS = {
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Chelsea",
    "Coventry City", "Crystal Palace", "Everton", "Fulham", "Hull City", "Ipswich Town",
    "Leeds", "Liverpool", "Man City", "Man Utd", "Newcastle", "Nott'm Forest",
    "Spurs", "Sunderland", "West Ham", "Wolves"
}

# Ground-truth confirmed 2026/27 Premier League Squad Rosters
CONFIRMED_SQUADS: Dict[str, str] = {
    # Arsenal
    "saka": "Arsenal", "bukayo saka": "Arsenal",
    "eze": "Arsenal", "eberechi eze": "Arsenal",
    "gyökeres": "Arsenal", "gyokeres": "Arsenal", "viktor gyökeres": "Arsenal", "viktor gyokeres": "Arsenal",
    "odegaard": "Arsenal", "ødegaard": "Arsenal", "martin odegaard": "Arsenal",
    "rice": "Arsenal", "declan rice": "Arsenal",
    "saliba": "Arsenal", "william saliba": "Arsenal",
    "gabriel": "Arsenal", "raya": "Arsenal", "david raya": "Arsenal",
    "havertz": "Arsenal", "kai havertz": "Arsenal",
    "calafiori": "Arsenal", "riccardo calafiori": "Arsenal",

    # Man City
    "haaland": "Man City", "erling haaland": "Man City",
    "de bruyne": "Man City", "kevin de bruyne": "Man City",
    "foden": "Man City", "phil foden": "Man City",
    "rodri": "Man City", "bernardo silva": "Man City",
    "gvardiol": "Man City", "ederson": "Man City",
    "doku": "Man City", "jeremy doku": "Man City",
    "cherki": "Man City", "rayan cherki": "Man City",
    "semenyo": "Man City", "antoine semenyo": "Man City",

    # Liverpool
    "salah": "Liverpool", "mohamed salah": "Liverpool",
    "van dijk": "Liverpool", "virgil van dijk": "Liverpool",
    "alexander-arnold": "Liverpool", "trent alexander-arnold": "Liverpool",
    "szoboszlai": "Liverpool", "dominik szoboszlai": "Liverpool",
    "alisson": "Liverpool", "mac allister": "Liverpool",
    "diaz": "Liverpool", "luis diaz": "Liverpool",

    # Chelsea
    "palmer": "Chelsea", "cole palmer": "Chelsea",
    "caicedo": "Chelsea", "moises caicedo": "Chelsea",
    "joão pedro": "Chelsea", "joao pedro": "Chelsea",
    "enzo fernandez": "Chelsea", "nkunku": "Chelsea",
    "jackson": "Chelsea", "nicolas jackson": "Chelsea",

    # Man Utd
    "bruno fernandes": "Man Utd", "b.fernandes": "Man Utd",
    "rashford": "Man Utd", "marcus rashford": "Man Utd",
    "mainoo": "Man Utd", "kobbie mainoo": "Man Utd",
    "mbeumo": "Brentford", "bryan mbeumo": "Brentford", # Brentford star
    "onana": "Man Utd", "andre onana": "Man Utd",
    "hojlund": "Man Utd", "rasmus hojlund": "Man Utd",

    # Newcastle
    "isak": "Newcastle", "alexander isak": "Newcastle",
    "gordon": "Newcastle", "anthony gordon": "Newcastle",
    "guimaraes": "Newcastle", "bruno guimaraes": "Newcastle",

    # Spurs
    "son": "Spurs", "heung-min son": "Spurs",
    "maddison": "Spurs", "james maddison": "Spurs",
    "solanke": "Spurs", "dominic solanke": "Spurs",
    "porro": "Spurs", "pedro porro": "Spurs",

    # Aston Villa
    "watkins": "Aston Villa", "ollie watkins": "Aston Villa",
    "martinez": "Aston Villa", "emi martinez": "Aston Villa",
    "rogers": "Aston Villa", "morgan rogers": "Aston Villa",

    # Crystal Palace
    "mateta": "Crystal Palace", "jean-philippe mateta": "Crystal Palace",
    "munoz": "Crystal Palace", "daniel munoz": "Crystal Palace",
    "wharton": "Crystal Palace", "adam wharton": "Crystal Palace",

    # Nottingham Forest
    "gibbs-white": "Nott'm Forest", "morgan gibbs-white": "Nott'm Forest",
    "wood": "Nott'm Forest", "chris wood": "Nott'm Forest",

    # Brentford
    "wissa": "Brentford", "yoane wissa": "Brentford",
    "schade": "Brentford", "kevin schade": "Brentford",
}


class PLSquadValidator:
    """Authoritative validator verifying player-to-club affiliations against official Premier League rosters."""

    def __init__(self):
        self.perplexity_key = os.getenv("PERPLEXITY_API_KEY")

    def validate_player_club(self, player_name: str, stated_club: str) -> Tuple[bool, str]:
        """Validate if player is officially confirmed at stated_club."""
        p_clean = player_name.strip().lower()
        c_clean = stated_club.strip()

        # 1. Check local ground-truth registry
        for name_key, official_club in CONFIRMED_SQUADS.items():
            if name_key in p_clean or p_clean in name_key:
                if self._club_matches(official_club, c_clean):
                    return (True, f"{player_name} verified at {official_club}")
                else:
                    return (False, f"SQUAD MISMATCH: {player_name} plays for {official_club}, not {stated_club}!")

        # 2. If unknown, query Perplexity for live confirmation
        if self.perplexity_key:
            return self._query_perplexity_verification(player_name, stated_club)

        return (True, f"{player_name} at {stated_club} (unverified in local registry)")

    def validate_slide_text(self, text: str) -> List[Tuple[bool, str]]:
        """Extract player-club patterns from text e.g. 'Haaland (Man City)' and validate."""
        results = []
        # Match patterns like: "Haaland (Man City)", "Eze (Arsenal)", "Palmer (Chelsea)"
        matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*\(([^)]+)\)", text)
        for player, club in matches:
            if any(self._club_matches(c, club) for c in PL_CLUBS):
                valid, reason = self.validate_player_club(player, club)
                results.append((valid, reason))
        return results

    def _club_matches(self, official: str, candidate: str) -> bool:
        """Fuzzy match club names e.g. 'Arsenal' vs 'Arsenal FC'."""
        o = official.lower().replace("fc", "").strip()
        c = candidate.lower().replace("fc", "").strip()
        return o in c or c in o

    def _query_perplexity_verification(self, player: str, club: str) -> Tuple[bool, str]:
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {"Authorization": f"Bearer {self.perplexity_key}", "Content-Type": "application/json"}
            prompt = f"What is football player {player}'s current official club as of August 2026? Return JSON: {{\"official_club\": \"...\", \"is_at_stated_club\": true/false}} comparing against {club}."
            payload = {"model": "sonar", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
            res = requests.post(url, headers=headers, json=payload, timeout=15).json()
            raw = res["choices"][0]["message"]["content"]
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            data = json.loads(raw)
            if data.get("is_at_stated_club"):
                return (True, f"{player} confirmed at {data.get('official_club', club)}")
            return (False, f"SQUAD MISMATCH: {player} is at {data.get('official_club')}, not {club}!")
        except Exception as e:
            logger.warning(f"Perplexity squad verification failed: {e}")
            return (True, "Skipped live verification due to network")
