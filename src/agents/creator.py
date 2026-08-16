import os
import json
import logging
from typing import Optional, List
from config import ChannelConfig, CarouselContent, SlideContent, StatBox, resolve_theme_palette
from src.agents.gatherer import GatheredNews
from src.scheduler.matchday_calendar import MatchdayScheduleContext

logger = logging.getLogger(__name__)


class ContentCreatorAgent:
    """Agent responsible for structuring gathered facts into a 5-card connected story arc."""

    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY") or (
            os.getenv("LLM_API_KEY") if (os.getenv("LLM_API_KEY") or "").startswith("sk-ant-") else None
        )
        self.openai_key = os.getenv("OPENAI_API_KEY") or (
            os.getenv("LLM_API_KEY") if (os.getenv("LLM_API_KEY") or "").startswith("sk-") and not (os.getenv("LLM_API_KEY") or "").startswith("sk-ant-") else None
        )

    def create(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        schedule_context: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        ctx = schedule_context or news.schedule_context
        logger.info(f"[{channel.name}] Composing 5-slide connected narrative carousel...")

        if self.anthropic_key:
            try:
                return self._create_via_anthropic(channel, news, ctx)
            except Exception as e:
                logger.warning(f"Anthropic creation failed: {e}. Falling back to deterministic builder.")

        if self.openai_key:
            try:
                return self._create_via_openai(channel, news, ctx)
            except Exception as e:
                logger.warning(f"OpenAI creation failed: {e}. Falling back to deterministic builder.")

        return self._create_structured_carousel(channel, news, ctx)

    def _create_structured_carousel(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        ctx: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        facts = news.verified_facts
        theme_badge = ctx.theme_badge if ctx else "SEASON LAUNCH"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary

        # Slide 1: Hook (Season Kickoff & Opener)
        slide1 = SlideContent(
            slide_number=1,
            total_slides=5,
            category=theme_badge,
            category_color=badge_color,
            sub_headline="PREMIER LEAGUE RETURNS",
            main_text="The 2026/27 campaign kicks off this week as Arsenal host newly-promoted Coventry City at the Emirates. The wait is over.",
            highlight_text="GW1 KICKOFF",
            source_attribution=news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 2: Marquee Opener Match & Key Metric
        fact1 = facts[0] if len(facts) > 0 else None
        slide2 = SlideContent(
            slide_number=2,
            total_slides=5,
            category="MATCH PREVIEW",
            category_color=badge_color,
            sub_headline="ARSENAL VS COVENTRY",
            main_text=fact1.fact_text if fact1 else "Arsenal host Coventry City under Friday night lights to begin the 2026/27 season at Emirates Stadium.",
            stat_box=StatBox(
                label=fact1.key_metric if fact1 and fact1.key_metric else "OPENING MATCH",
                value=fact1.metric_value if fact1 and fact1.metric_value else "EMIRATES CLASH",
                subtext="Gameweek 1 Fixture",
            ),
            highlight_text="FRIDAY OPENER",
            source_attribution=fact1.source if fact1 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 3: Squad & Transfer Reinforcement
        fact2 = facts[1] if len(facts) > 1 else None
        slide3 = SlideContent(
            slide_number=3,
            total_slides=5,
            category="SQUAD & TRANSFERS",
            category_color=badge_color,
            sub_headline="SUMMER TACTICAL SHIFTS",
            main_text=fact2.fact_text if fact2 else "Summer reinforcements give Mikel Arteta tactical depth and pressing intensity for the title chase.",
            stat_box=StatBox(
                label=fact2.key_metric if fact2 and fact2.key_metric else "TACTICAL FOCUS",
                value=fact2.metric_value if fact2 and fact2.metric_value else "PRESS READY",
                subtext="Opening campaign readiness",
            ) if fact2 and fact2.key_metric else None,
            highlight_text="TACTICAL INTEL",
            source_attribution=fact2.source if fact2 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 4: FPL Gameweek 1 Essential Asset
        fact3 = facts[2] if len(facts) > 2 else None
        slide4 = SlideContent(
            slide_number=4,
            total_slides=5,
            category="FPL SCOUT",
            category_color=badge_color,
            sub_headline="GAMEWEEK 1 CAPTAINS",
            main_text=fact3.fact_text if fact3 else "Bukayo Saka and Erling Haaland project as premium captaincy anchors for the opening weekend lock.",
            stat_box=StatBox(
                label=fact3.key_metric if fact3 and fact3.key_metric else "FPL ESSENTIAL",
                value=fact3.metric_value if fact3 and fact3.metric_value else "PREMIUM ASSET",
                subtext="Top projected ceiling",
            ) if fact3 and fact3.key_metric else None,
            highlight_text="FPL DEADLINE",
            source_attribution=fact3.source if fact3 else "Fantasy Premier League",
            brand_handle=channel.brand_handle,
        )

        # Slide 5: Fan Debate & Community Prediction
        slide5 = SlideContent(
            slide_number=5,
            total_slides=5,
            category="FAN VERDICT",
            category_color=badge_color,
            sub_headline="PREDICT THE OPENER",
            main_text="Can Coventry shock the Emirates, or will Arsenal start with a statement win? Drop your score predictions below!",
            highlight_text="YOUR VERDICT",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        hashtags = ctx.suggested_hashtags if ctx and ctx.suggested_hashtags else channel.default_hashtags
        caption = (
            f"🚨 [{theme_badge}] Premier League Football is BACK!\n\n"
            f"Arsenal host Coventry City at the Emirates to kick off Gameweek 1.\n"
            f"Swipe through for the complete opening match tactical preview, transfer breakdown & FPL captaincy advice.\n\n"
            f"👇 Predict the opening scoreline in the comments!\n\n"
            f"{' '.join(hashtags)}"
        )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=news.summary_headline,
            caption=caption,
            badge_color=badge_color,
            hashtags=hashtags,
            slides=[slide1, slide2, slide3, slide4, slide5],
        )

    def _create_via_anthropic(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        ctx: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        import anthropic
        client = anthropic.Anthropic(api_key=self.anthropic_key)

        theme_badge = ctx.theme_badge if ctx else "SEASON LAUNCH"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary

        prompt = f"""You are the Senior Editorial Copywriter for '{channel.name}'.
Verified Context: {news.model_dump_json()}
Opening Fixture: Arsenal vs Coventry City (Emirates Stadium)
Verified Date: {news.calendar_date_utc}

Write a high-impact, cohesive 5-slide Instagram carousel following this EXACT story arc:
- Slide 1: Hook Headline (Season kickoff & Arsenal vs Coventry opener at Emirates)
- Slide 2: Match Preview Focus (Arsenal vs Coventry tactical key with stat_box)
- Slide 3: Squad & Transfer Dynamic (New signings & tactical depth)
- Slide 4: FPL Gameweek 1 Essential (Captaincy choices & deadline reminder with stat_box)
- Slide 5: Fan Debate Call-To-Action (Score prediction question, no stat_box)

STRICT RULES:
1. Body text on EVERY slide must be 28 words or fewer.
2. Only use verified active player-club pairings from the input.
3. Return strictly JSON with no markdown fences."""

        candidate_models = [
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6",
            "claude-3-5-sonnet-20241022",
            "claude-opus-4-5-20251101",
        ]

        response = None
        last_err = None
        for model_name in candidate_models:
            try:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=2048,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}],
                )
                if response:
                    break
            except Exception as err:
                last_err = err
                continue

        if not response:
            raise RuntimeError(f"All Anthropic models failed. Last error: {last_err}")

        raw_text = response.content[0].text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        data = json.loads(raw_text)
        slides = []
        for i, s in enumerate(data["slides"], start=1):
            stat_box = StatBox(**s["stat_box"]) if s.get("stat_box") else None
            slides.append(
                SlideContent(
                    slide_number=i,
                    total_slides=5,
                    category=s.get("category", theme_badge),
                    category_color=s.get("category_color", badge_color),
                    sub_headline=s.get("sub_headline", "Matchday Update"),
                    main_text=s.get("main_text", ""),
                    stat_box=stat_box,
                    highlight_text=s.get("highlight_text"),
                    source_attribution=s.get("source_attribution", news.primary_source),
                    brand_handle=channel.brand_handle,
                )
            )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=data.get("headline", news.summary_headline),
            caption=data.get("caption", ""),
            badge_color=badge_color,
            hashtags=data.get("hashtags", ctx.suggested_hashtags if ctx else channel.default_hashtags),
            slides=slides,
        )

    def _create_via_openai(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        ctx: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_key)

        theme_badge = ctx.theme_badge if ctx else "SEASON LAUNCH"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary

        prompt = f"""Format this verified football intel into a 5-card carousel:
Intel: {news.model_dump_json()}
Opener: Arsenal vs Coventry City
Story Arc: 1. Season Hook, 2. Match Preview, 3. Transfers, 4. FPL GW1, 5. Score Debate.
Constraint: Max 28 words per slide main_text."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return valid JSON only matching CarouselContent schema."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        data = json.loads(response.choices[0].message.content)
        slides = []
        for i, s in enumerate(data["slides"], start=1):
            stat_box = StatBox(**s["stat_box"]) if s.get("stat_box") else None
            slides.append(
                SlideContent(
                    slide_number=i,
                    total_slides=5,
                    category=s.get("category", theme_badge),
                    category_color=badge_color,
                    sub_headline=s.get("sub_headline", "Matchday Update"),
                    main_text=s.get("main_text", ""),
                    stat_box=stat_box,
                    highlight_text=s.get("highlight_text"),
                    source_attribution=s.get("source_attribution", news.primary_source),
                    brand_handle=channel.brand_handle,
                )
            )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=data.get("headline", news.summary_headline),
            caption=data.get("caption", ""),
            badge_color=badge_color,
            hashtags=data.get("hashtags", ctx.suggested_hashtags if ctx else channel.default_hashtags),
            slides=slides,
        )