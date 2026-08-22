# src/agents/creator.py
import logging
from typing import Optional, List, Dict, Any
from config import ChannelConfig, CarouselContent, SlideContent, StatBox, resolve_theme_palette
from src.agents.gatherer import GatheredNews
from src.scheduler.matchday_calendar import MatchdayScheduleContext, SchedulePhase

logger = logging.getLogger(__name__)


class ContentCreatorAgent:
    """Structures official FPL & PL intelligence into high-converting 6-card carousel decks with dedicated Follow & Like outro."""

    def create(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        schedule_context: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        ctx = schedule_context or news.schedule_context
        extra = news.extra_payload
        payload_type = extra.get("type", "FPL_SCOUT")

        if payload_type == "MATCH_DEBRIEF":
            return self._create_match_debrief(channel, news, extra.get("data", {}))
        elif payload_type == "INJURY_INTEL":
            return self._create_injury_intel(channel, news, extra.get("data", {}))
        elif payload_type == "TRANSFER_RADAR":
            return self._create_transfer_radar(channel, news, extra.get("data", {}))
        else:
            return self._create_fpl_scout(channel, news, extra.get("data", {}))

    def _build_outro_slide(
        self,
        slide_number: int,
        total_slides: int,
        channel: ChannelConfig,
        theme_badge: str,
        badge_color: str,
    ) -> SlideContent:
        return SlideContent(
            slide_number=slide_number,
            total_slides=total_slides,
            category="JOIN THE SQUAD",
            category_color=badge_color,
            sub_headline="NEVER MISS A MATCHDAY UPDATE",
            main_text=f"Follow {channel.brand_handle} for daily Premier League tactics, FPL price risers, top point haulers & injury intel. Like & save this post for your gameweek!",
            stat_box=StatBox(
                label="DAILY EPL INTEL",
                value="FOLLOW",
                subtext="Like • Comment • Save • Share",
            ),
            highlight_text=f"FOLLOW {channel.brand_handle.upper()}",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

    def _create_match_debrief(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        debrief: Dict[str, Any],
    ) -> CarouselContent:
        theme_badge = "MATCH DEBRIEF"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary
        total_slides = 6

        scoreline = debrief.get("scoreline", "Arsenal 3 - 0 Coventry City")
        h_team = debrief.get("home_team", "Arsenal")
        h_score = debrief.get("home_score", 3)
        a_score = debrief.get("away_score", 0)
        top_p = debrief.get("top_performers", [])

        p1 = top_p[0] if len(top_p) > 0 else {"name": "White", "team": "Arsenal", "points": 11, "cost": "£5.5m"}
        p2 = top_p[1] if len(top_p) > 1 else {"name": "Ødegaard", "team": "Arsenal", "points": 10, "cost": "£6.5m"}
        p3 = top_p[2] if len(top_p) > 2 else {"name": "Calafiori", "team": "Arsenal", "points": 9, "cost": "£5.5m"}

        slide1 = SlideContent(
            slide_number=1,
            total_slides=total_slides,
            category=theme_badge,
            category_color=badge_color,
            sub_headline=f"FULL-TIME: {scoreline.upper()}",
            main_text=f"{h_team} deliver a commanding {h_score}-{a_score} victory to open the campaign. High-intensity pressing and clinical execution secure all three points.",
            stat_box=StatBox(
                label="FINAL RESULT",
                value=f"{h_score} - {a_score}",
                subtext=f"{h_team} Opening Win",
            ),
            highlight_text="MATCHDAY RESULT",
            source_attribution="Premier League Official",
            brand_handle=channel.brand_handle,
        )

        slide2 = SlideContent(
            slide_number=2,
            total_slides=total_slides,
            category="TOP FPL HAULER",
            category_color=badge_color,
            sub_headline=f"1ST PLACE: {p1['name'].upper()} ({p1['team'].upper()})",
            main_text=f"{p1['name']} tops the bonus point system with {p1['points']} points at {p1['cost']}. Essential clean sheet and attacking contribution.",
            stat_box=StatBox(
                label="FPL HAUL",
                value=f"{p1['points']} PTS",
                subtext=f"{p1.get('bonus', 2)} Bonus Points",
            ),
            highlight_text="STAR PERFORMER",
            source_attribution="Official FPL Feed",
            brand_handle=channel.brand_handle,
        )

        slide3 = SlideContent(
            slide_number=3,
            total_slides=total_slides,
            category="BONUS PODIUM",
            category_color=badge_color,
            sub_headline=f"PODIUM: {p2['name'].upper()} & {p3['name'].upper()}",
            main_text=f"{p2['name']} delivered {p2['points']} points and {p3['name']} racked up {p3['points']} points to anchor maximum bonus points for {h_team} assets.",
            stat_box=StatBox(
                label="PODIUM RETURNS",
                value=f"{p2['points']} & {p3['points']} PTS",
                subtext="Goals & Assists Combined",
            ),
            highlight_text="BONUS LOCK",
            source_attribution="Official FPL Feed",
            brand_handle=channel.brand_handle,
        )

        slide4 = SlideContent(
            slide_number=4,
            total_slides=total_slides,
            category="TRANSFER LOOKOUT",
            category_color=badge_color,
            sub_headline="IMMEDIATE TRANSFER TARGETS",
            main_text=f"With {h_team} showing elite defensive metrics and attacking fluidity, their £5.5m defenders and £6.5m midfielders offer prime value.",
            stat_box=StatBox(
                label="TRANSFER MOMENTUM",
                value="HIGH DEMAND",
                subtext="Rising Ownership Ahead",
            ),
            highlight_text="MARKET RADAR",
            source_attribution="FPL Scout",
            brand_handle=channel.brand_handle,
        )

        slide5 = SlideContent(
            slide_number=5,
            total_slides=total_slides,
            category="FAN VERDICT",
            category_color=badge_color,
            sub_headline="WHO WAS MAN OF THE MATCH?",
            main_text=f"Who stood out most in {scoreline}? Are you bringing {p1['name']} or {p2['name']} into your squad? Comment below!",
            highlight_text="JOIN THE DEBATE",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        slide6 = self._build_outro_slide(6, total_slides, channel, theme_badge, badge_color)

        caption = (
            f"🚨 [{theme_badge}] {scoreline}: Full-Time Debrief & Top FPL Points Stars\n\n"
            f"Dominant performance from {h_team}! Swipe through for the Top 3 FPL points haulers, bonus breakdown, and immediate transfer recommendations.\n\n"
            f"🌟 Top 3 Haulers:\n"
            f"1️⃣ {p1['name']} ({p1['team']}) - {p1['points']} pts ({p1['cost']})\n"
            f"2️⃣ {p2['name']} ({p2['team']}) - {p2['points']} pts ({p2['cost']})\n"
            f"3️⃣ {p3['name']} ({p3['team']}) - {p3['points']} pts ({p3['cost']})\n\n"
            f"👉 Follow @MatchdayEPL for daily Premier League tactics & FPL alerts!\n"
            f"❤️ Like & Save this post if you enjoyed the debrief!\n\n"
            f"#PremierLeague #FPL #FPLCommunity #MatchdayEPL #FantasyPL #Arsenal #EPL"
        )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=f"Full-Time Debrief: {scoreline}",
            caption=caption,
            badge_color=badge_color,
            hashtags=["#PremierLeague", "#FPL", "#FPLCommunity", "#MatchdayEPL", "#FantasyPL"],
            slides=[slide1, slide2, slide3, slide4, slide5, slide6],
        )

    def _create_injury_intel(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        inj: Dict[str, Any],
    ) -> CarouselContent:
        theme_badge = "INJURY INTEL"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary
        total_slides = 6

        player = inj.get("player_name", "Pedro Porro")
        team = inj.get("team", "Spurs")
        cost = inj.get("cost", "£5.5m")
        own = inj.get("ownership", "17.0%")
        news_text = inj.get("news", "Lack of match fitness")
        reps = inj.get("replacements", [])
        rep1 = reps[0] if reps else {"name": "Calafiori", "team": "Arsenal", "cost": "£5.5m", "ownership": "39.8%"}
        rep2 = reps[1] if len(reps) > 1 else {"name": "Shaw", "team": "Man Utd", "cost": "£4.5m", "ownership": "21.6%"}

        slide1 = SlideContent(
            slide_number=1,
            total_slides=total_slides,
            category=theme_badge,
            category_color=badge_color,
            sub_headline=f"INJURY ALERT: {player.upper()} ({team.upper()})",
            main_text=f"{player} ({cost}, {own} owned) is sidelined with {news_text}. High volume of sales expected ahead of the next deadline.",
            stat_box=StatBox(
                label="OWNERSHIP AT RISK",
                value=own,
                subtext=f"{player} ({cost}) Sidelined",
            ),
            highlight_text="BREAKING UPDATE",
            source_attribution="Premier League Press Brief",
            brand_handle=channel.brand_handle,
        )

        slide2 = SlideContent(
            slide_number=2,
            total_slides=total_slides,
            category="MEDICAL TIMELINE",
            category_color=badge_color,
            sub_headline="RECOVERY & RETURN DATE",
            main_text=f"Official club updates confirm {news_text}. Managers face immediate price drop risk if not transferred out swiftly.",
            stat_box=StatBox(
                label="CHANCE OF PLAYING",
                value="0%",
                subtext="Ruled Out Next Fixture",
            ),
            highlight_text="OUT OF ACTION",
            source_attribution="Club Medical Bulletin",
            brand_handle=channel.brand_handle,
        )

        slide3 = SlideContent(
            slide_number=3,
            total_slides=total_slides,
            category="PRIMARY REPLACEMENT",
            category_color=badge_color,
            sub_headline=f"TOP BUY: {rep1['name'].upper()} ({rep1['team'].upper()})",
            main_text=f"{rep1['name']} ({rep1['cost']}) represents a straight swap in the same price tier with high clean sheet potential and attacking threat.",
            stat_box=StatBox(
                label="DIRECT SWAP",
                value=rep1['cost'],
                subtext=f"{rep1['ownership']} Selected",
            ),
            highlight_text="PRIORITY TARGET",
            source_attribution="FPL Scout",
            brand_handle=channel.brand_handle,
        )

        slide4 = SlideContent(
            slide_number=4,
            total_slides=total_slides,
            category="BUDGET ENABLER",
            category_color=badge_color,
            sub_headline=f"VALUE PICK: {rep2['name'].upper()} ({rep2['team'].upper()})",
            main_text=f"{rep2['name']} at {rep2['cost']} frees up critical funds across midfield and attack while guaranteeing regular Premier League starts.",
            stat_box=StatBox(
                label="BUDGET RELIEF",
                value=rep2['cost'],
                subtext="Freed Funds for Premium Picks",
            ),
            highlight_text="VALUE ENABLER",
            source_attribution="FPL Scout",
            brand_handle=channel.brand_handle,
        )

        slide5 = SlideContent(
            slide_number=5,
            total_slides=total_slides,
            category="COMMUNITY POLL",
            category_color=badge_color,
            sub_headline="ARE YOU SELLING OR HOLDING?",
            main_text=f"Do you plan an immediate transfer for {player}, or are you benching him for the weekend? Drop your strategy below!",
            highlight_text="JOIN THE POLL",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        slide6 = self._build_outro_slide(6, total_slides, channel, theme_badge, badge_color)

        caption = (
            f"🚨 [{theme_badge}] {player} ({team}) Sidelined: Top FPL Direct Replacements\n\n"
            f"{player} ({cost}, {own} owned) is confirmed out: {news_text}.\n\n"
            f"🔄 Top Replacement Options:\n"
            f"1️⃣ {rep1['name']} ({rep1['team']}) - {rep1['cost']} ({rep1['ownership']} owned)\n"
            f"2️⃣ {rep2['name']} ({rep2['team']}) - {rep2['cost']} ({rep2['ownership']} owned)\n\n"
            f"👉 Follow @MatchdayEPL for daily Premier League injury updates & FPL tactics!\n"
            f"❤️ Like & Save this post for your Gameweek planning!\n\n"
            f"#FPL #FPLInjuries #PremierLeague #FPLCommunity #FPLTips #MatchdayEPL"
        )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=f"Injury Alert: {player} Sidelined",
            caption=caption,
            badge_color=badge_color,
            hashtags=["#FPL", "#FPLInjuries", "#PremierLeague", "#FPLCommunity", "#MatchdayEPL"],
            slides=[slide1, slide2, slide3, slide4, slide5, slide6],
        )

    def _create_transfer_radar(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        radar: Dict[str, Any],
    ) -> CarouselContent:
        theme_badge = "TRANSFER RADAR"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary
        total_slides = 6

        top_buys = radar.get("top_buys", [])
        top_sells = radar.get("top_sells", [])
        b1 = top_buys[0] if top_buys else {"name": "Calafiori", "team": "Arsenal", "cost": "£5.5m", "transfers": "+31,390"}
        b2 = top_buys[1] if len(top_buys) > 1 else {"name": "Tzolis", "team": "Arsenal", "cost": "£6.5m", "transfers": "+21,496"}
        s1 = top_sells[0] if top_sells else {"name": "Pedro Porro", "team": "Spurs", "cost": "£5.5m", "transfers": "-49,692"}

        slide1 = SlideContent(
            slide_number=1,
            total_slides=total_slides,
            category=theme_badge,
            category_color=badge_color,
            sub_headline="FPL TRANSFER RADAR: MARKET MOVERS",
            main_text="FPL managers are making decisive moves ahead of the price lock. Rapid ownership swings across premium assets.",
            stat_box=StatBox(
                label="MARKET SURGE",
                value="HIGH VOL",
                subtext="Impending Price Rises",
            ),
            highlight_text="MARKET ALERT",
            source_attribution="Fantasy Premier League",
            brand_handle=channel.brand_handle,
        )

        slide2 = SlideContent(
            slide_number=2,
            total_slides=total_slides,
            category="TOP PRICE RISER",
            category_color=badge_color,
            sub_headline=f"SURGING: {b1['name'].upper()} ({b1['team'].upper()})",
            main_text=f"{b1['name']} at {b1['cost']} leads all players in transfer volume with {b1['transfers']} net buys, tracking toward a price rise.",
            stat_box=StatBox(
                label="NET TRANSFERS",
                value=b1['transfers'],
                subtext=f"{b1['name']} ({b1['cost']})",
            ),
            highlight_text="PRICE RISE IMMINENT",
            source_attribution="FPL Transfer Feed",
            brand_handle=channel.brand_handle,
        )

        slide3 = SlideContent(
            slide_number=3,
            total_slides=total_slides,
            category="MASS EXODUS",
            category_color=badge_color,
            sub_headline=f"FALLING: {s1['name'].upper()} ({s1['team'].upper()})",
            main_text=f"{s1['name']} ({s1['cost']}) leads outgoing transfers with {s1['transfers']} sales, facing an imminent £0.1m price drop.",
            stat_box=StatBox(
                label="MASS FIRE SALE",
                value=s1['transfers'],
                subtext=f"{s1['name']} Price Drop Risk",
            ),
            highlight_text="PRICE FALL RISK",
            source_attribution="FPL Transfer Feed",
            brand_handle=channel.brand_handle,
        )

        slide4 = SlideContent(
            slide_number=4,
            total_slides=total_slides,
            category="MOMENTUM PICK",
            category_color=badge_color,
            sub_headline=f"VALUE BUY: {b2['name'].upper()} ({b2['team'].upper()})",
            main_text=f"{b2['name']} priced at {b2['cost']} has gained {b2['transfers']} managers following explosive form and favourable fixtures.",
            stat_box=StatBox(
                label="TRANSFERS IN",
                value=b2['transfers'],
                subtext="Rising Demand",
            ),
            highlight_text="VALUE SURGE",
            source_attribution="FPL Scout",
            brand_handle=channel.brand_handle,
        )

        slide5 = SlideContent(
            slide_number=5,
            total_slides=total_slides,
            category="FAN STRATEGY",
            category_color=badge_color,
            sub_headline="WHAT IS YOUR NEXT TRANSFER?",
            main_text="Are you chasing the price rises or banking your free transfer for next week? Comment your strategy below!",
            highlight_text="SHARE YOUR MOVE",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        slide6 = self._build_outro_slide(6, total_slides, channel, theme_badge, badge_color)

        caption = (
            f"📈 [{theme_badge}] FPL Transfer Radar: Top Price Risers & Fallers\n\n"
            f"Huge market shifts ahead of the upcoming deadline. Don't lose team value!\n\n"
            f"🟢 Top Buys (Price Rise Alert):\n"
            f"• {b1['name']} ({b1['team']}) - {b1['cost']} ({b1['transfers']})\n"
            f"• {b2['name']} ({b2['team']}) - {b2['cost']} ({b2['transfers']})\n\n"
            f"🔴 Top Sells (Price Drop Warning):\n"
            f"• {s1['name']} ({s1['team']}) - {s1['cost']} ({s1['transfers']})\n\n"
            f"👉 Follow @MatchdayEPL for daily Premier League tactics & FPL market movers!\n"
            f"❤️ Like & Save to keep your rank rising!\n\n"
            f"#FPL #FPLTransfers #FPLPriceChanges #FPLCommunity #PremierLeague #MatchdayEPL"
        )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline="FPL Transfer Radar: Market Movers",
            caption=caption,
            badge_color=badge_color,
            hashtags=["#FPL", "#FPLTransfers", "#FPLPriceChanges", "#FPLCommunity", "#MatchdayEPL"],
            slides=[slide1, slide2, slide3, slide4, slide5, slide6],
        )

    def _create_fpl_scout(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        fpl_data: Dict[str, Any],
    ) -> CarouselContent:
        theme_badge = "FPL SCOUT"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary
        total_slides = 6
        facts = news.verified_facts

        slide1 = SlideContent(
            slide_number=1,
            total_slides=total_slides,
            category=theme_badge,
            category_color=badge_color,
            sub_headline="PREMIER LEAGUE RETURNS",
            main_text="The 2026/27 season is here. Marquee fixtures, transfer impacts, and crucial FPL captaincy decisions await.",
            stat_box=StatBox(
                label="CAMPAIGN OPENER",
                value="GW 1",
                subtext="2026/27 Premier League",
            ),
            highlight_text="SEASON LAUNCH",
            source_attribution="Premier League",
            brand_handle=channel.brand_handle,
        )

        fact1 = facts[0]
        slide2 = SlideContent(
            slide_number=2,
            total_slides=total_slides,
            category="KEY FIXTURES",
            category_color=badge_color,
            sub_headline="MATCHES TO WATCH",
            main_text=fact1.fact_text,
            stat_box=StatBox(
                label=fact1.key_metric or "KEY FIXTURES",
                value=fact1.metric_value or "3 MATCHES",
                subtext="Opening weekend slate",
            ),
            highlight_text="MARQUEE CLASHES",
            source_attribution=fact1.source,
            brand_handle=channel.brand_handle,
        )

        fact2 = facts[1]
        slide3 = SlideContent(
            slide_number=3,
            total_slides=total_slides,
            category="CAPTAINCY PICK",
            category_color=badge_color,
            sub_headline=fact2.headline,
            main_text=fact2.fact_text,
            stat_box=StatBox(
                label=fact2.key_metric or "OWNERSHIP",
                value=fact2.metric_value or "72.9%",
                subtext="Official FPL backing",
            ),
            highlight_text="TEMPLATE ANCHOR",
            source_attribution=fact2.source,
            brand_handle=channel.brand_handle,
        )

        fact3 = facts[2]
        slide4 = SlideContent(
            slide_number=4,
            total_slides=total_slides,
            category="DIFFERENTIAL",
            category_color=badge_color,
            sub_headline=fact3.headline,
            main_text=fact3.fact_text,
            stat_box=StatBox(
                label="OWNERSHIP",
                value=fact3.metric_value or "9.8%",
                subtext="Rank boost potential",
            ),
            highlight_text="HIGH CEILING",
            source_attribution=fact3.source,
            brand_handle=channel.brand_handle,
        )

        slide5 = SlideContent(
            slide_number=5,
            total_slides=total_slides,
            category="FAN VERDICT",
            category_color=badge_color,
            sub_headline="WHO IS YOUR CAPTAIN?",
            main_text="Who gets your Gameweek 1 armband? Back the template or roll the dice on a differential? Comment below!",
            highlight_text="JOIN THE DEBATE",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        slide6 = self._build_outro_slide(6, total_slides, channel, theme_badge, badge_color)

        caption = (
            f"🚨 [{theme_badge}] {news.summary_headline}\n\n"
            f"The Premier League is officially BACK. Swipe through for the complete opening fixture guide, top captain picks, and high-upside differentials.\n\n"
            f"👉 Follow @MatchdayEPL for daily Premier League news & FPL tips!\n"
            f"❤️ Like & Save to support the channel!\n\n"
            f"#PremierLeague #FPL #Gameweek1 #EPL #MatchdayEPL #FantasyPremierLeague"
        )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=news.summary_headline,
            caption=caption,
            badge_color=badge_color,
            hashtags=["#PremierLeague", "#FPL", "#Gameweek1", "#MatchdayEPL"],
            slides=[slide1, slide2, slide3, slide4, slide5, slide6],
        )