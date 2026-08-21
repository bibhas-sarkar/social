# src/agents/creator.py
import os
import json
import logging
from typing import Optional, List
from config import ChannelConfig, CarouselContent, SlideContent, StatBox, resolve_theme_palette
from src.agents.gatherer import GatheredNews
from src.scheduler.matchday_calendar import MatchdayScheduleContext

logger = logging.getLogger(__name__)

class ContentCreatorAgent:
    """Structures official FPL & PL fixtures into a high-converting 5-card carousel."""

    def create(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        schedule_context: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        ctx = schedule_context or news.schedule_context
        facts = news.verified_facts
        theme_badge = "GAMEWEEK 1 SCOUT" if "Gameweek 1" in news.summary_headline else "MATCHDAY INTEL"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary

        # Slide 1: Hook & Topic Overview
        slide1 = SlideContent(
            slide_number=1,
            total_slides=5,
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

        # Slide 2: Opening Matchups to Watch
        fact1 = facts[0]
        slide2 = SlideContent(
            slide_number=2,
            total_slides=5,
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

        # Slide 3: Essential Captain Pick
        fact2 = facts[1]
        slide3 = SlideContent(
            slide_number=3,
            total_slides=5,
            category="CAPTAINCY PICK",
            category_color=badge_color,
            sub_headline=fact2.headline,
            main_text=fact2.fact_text,
            stat_box=StatBox(
                label=fact2.key_metric or "OWNERSHIP",
                value=fact2.metric_value or "55.0%",
                subtext="Official FPL backing",
            ),
            highlight_text="TEMPLATE ANCHOR",
            source_attribution=fact2.source,
            brand_handle=channel.brand_handle,
        )

        # Slide 4: High-Upside Differential
        fact3 = facts[2]
        slide4 = SlideContent(
            slide_number=4,
            total_slides=5,
            category="DIFFERENTIAL",
            category_color=badge_color,
            sub_headline=fact3.headline,
            main_text=fact3.fact_text,
            stat_box=StatBox(
                label="OWNERSHIP",
                value=fact3.metric_value or "<10%",
                subtext="Rank boost potential",
            ),
            highlight_text="HIGH CEILING",
            source_attribution=fact3.source,
            brand_handle=channel.brand_handle,
        )

        # Slide 5: Debate CTA
        slide5 = SlideContent(
            slide_number=5,
            total_slides=5,
            category="FAN VERDICT",
            category_color=badge_color,
            sub_headline="WHO IS YOUR CAPTAIN?",
            main_text="Who gets your Gameweek 1 armband? Back the template or roll the dice on a differential? Comment below!",
            highlight_text="JOIN THE DEBATE",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        caption = (
            f"🚨 [{theme_badge}] {news.summary_headline}\n\n"
            f"The Premier League is officially BACK. Swipe through for the complete opening fixture guide, top captain picks, and high-upside differentials.\n\n"
            f"👇 Who gets your Gameweek 1 armband? Drop your team in the comments!\n\n"
            f"#PremierLeague #FPL #Gameweek1 #EPL #MatchdayEPL #FantasyPremierLeague"
        )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=news.summary_headline,
            caption=caption,
            badge_color=badge_color,
            hashtags=["#PremierLeague", "#FPL", "#Gameweek1", "#MatchdayEPL"],
            slides=[slide1, slide2, slide3, slide4, slide5],
        )