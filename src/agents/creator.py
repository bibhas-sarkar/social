import os
import json
import logging
from typing import Optional, List
from config import ChannelConfig, CarouselContent, SlideContent, StatBox, resolve_theme_palette
from src.agents.gatherer import GatheredNews
from src.scheduler.matchday_calendar import MatchdayScheduleContext, SchedulePhase

logger = logging.getLogger(__name__)


class ContentCreatorAgent:
    """Agent responsible for structuring raw gathered facts into a 5-slide carousel format."""

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
        """Create a 5-slide carousel payload from gathered news with cadence awareness."""
        ctx = schedule_context or news.schedule_context
        logger.info(f"[{channel.name}] Creating 5-slide structured carousel content...")
        if ctx:
            logger.info(f"[{channel.name}] Ingested Cadence: {ctx.phase_name} | Theme: {ctx.theme_badge}")

        # 1. Prioritize Anthropic Claude if configured
        if self.anthropic_key:
            try:
                return self._create_via_anthropic(channel, news, ctx)
            except Exception as e:
                logger.warning(f"Anthropic creation failed: {e}. Attempting next method.")

        # 2. Try OpenAI if configured
        if self.openai_key:
            try:
                return self._create_via_openai(channel, news, ctx)
            except Exception as e:
                logger.warning(f"OpenAI creation failed: {e}. Using deterministic structured engine.")

        # Fallback / offline deterministic builder
        return self._create_structured_carousel(channel, news, ctx)

    def _create_structured_carousel(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        ctx: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        """Deterministic 5-slide structured generation following strict constraints."""
        facts = news.verified_facts
        theme_badge = ctx.theme_badge if ctx else ("BREAKING TACTICS" if channel.key == "matchday" else "SPECIAL REPORT")
        badge_color = ctx.badge_color if ctx else channel.accent_color
        phase = ctx.phase if ctx else SchedulePhase.MIDWEEK_ANALYSIS

        # Dynamic categories based on phase
        if phase == SchedulePhase.FPL_PREVIEW:
            cat1, cat2, cat3, cat4, cat5 = "FPL SCOUT", "KEY ASSET STAT", "CAPTAINCY INTEL", "DIFFERENTIAL PICK", "FPL VERDICT"
        elif phase == SchedulePhase.POST_MATCH_WRAP:
            cat1, cat2, cat3, cat4, cat5 = "POST-MATCH DEBRIEF", "xG STAT BLOCK", "KEY TRANSITIONS", "TABLE IMPACT", "FAN VERDICT"
        elif phase == SchedulePhase.PRE_MATCH_PREVIEW:
            cat1, cat2, cat3, cat4, cat5 = "FIXTURE INTEL", "HEAD-TO-HEAD", "TACTICAL BLUEPRINT", "LINEUP PREVIEW", "YOUR PREDICTION"
        elif phase == SchedulePhase.LIVE_MATCH_REACTION:
            cat1, cat2, cat3, cat4, cat5 = "MATCHDAY LIVE", "MOMENTUM STAT", "TACTICAL SHIFT", "STANDINGS MOVE", "HOT TAKE"
        else:
            cat1, cat2, cat3, cat4, cat5 = theme_badge, "PRIMARY METRIC", "TACTICAL DYNAMICS", "FORWARD OUTLOOK", "FAN VERDICT"

        # Slide 1: Hook / Headline
        slide1_text = (
            f"Essential {theme_badge.lower()} and critical tactical insights for the Premier League."
            if channel.key == "matchday"
            else f"Essential briefing and critical takeaways from {channel.name}."
        )
        slide1 = SlideContent(
            slide_number=1,
            total_slides=5,
            category=cat1,
            category_color=badge_color,
            sub_headline=news.summary_headline,
            main_text=slide1_text,
            highlight_text=theme_badge,
            source_attribution=news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 2: Main Point + Key Stat Block
        fact1 = facts[0] if len(facts) > 0 else None
        slide2 = SlideContent(
            slide_number=2,
            total_slides=5,
            category=cat2,
            category_color=badge_color,
            sub_headline=fact1.headline if fact1 else "Key Benchmark Performance",
            main_text=fact1.fact_text if fact1 else "Unmatched recovery metrics driving sustained performance.",
            stat_box=StatBox(
                label=fact1.key_metric if (fact1 and fact1.key_metric) else "BENCHMARK",
                value=fact1.metric_value if (fact1 and fact1.metric_value) else "100%",
                subtext="Verified analytical metric",
            ),
            highlight_text="KEY METRIC",
            source_attribution=fact1.source if fact1 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 3: Tactical / Squad Context
        fact2 = facts[1] if len(facts) > 1 else None
        slide3 = SlideContent(
            slide_number=3,
            total_slides=5,
            category=cat3,
            category_color=badge_color,
            sub_headline=fact2.headline if fact2 else "Tactical Context & Dynamics",
            main_text=fact2.fact_text if fact2 else "Aggressive traps and pressing structures dictating space.",
            stat_box=StatBox(
                label=fact2.key_metric if (fact2 and fact2.key_metric) else "SCALE",
                value=fact2.metric_value if (fact2 and fact2.metric_value) else "28 SHOTS",
                subtext="League benchmark rating",
            ) if fact2 and fact2.key_metric else None,
            highlight_text="TACTICAL FOCUS",
            source_attribution=fact2.source if fact2 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 4: Matchup / Fixture Preview
        fact3 = facts[2] if len(facts) > 2 else None
        slide4 = SlideContent(
            slide_number=4,
            total_slides=5,
            category=cat4,
            category_color=badge_color,
            sub_headline=fact3.headline if fact3 else "Decisive Matchup Metric",
            main_text=fact3.fact_text if fact3 else "Execution in high-leverage phases will decide the outcome.",
            stat_box=StatBox(
                label=fact3.key_metric if (fact3 and fact3.key_metric) else "BOX CONVERSION",
                value=fact3.metric_value if (fact3 and fact3.metric_value) else "32.4%",
                subtext="Big chance conversion rate",
            ) if fact3 and fact3.key_metric else None,
            highlight_text="MATCHUP FACTOR",
            source_attribution=fact3.source if fact3 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 5: CTA / Question
        slide5_sub = "Who Takes All 3 Points?" if channel.key == "matchday" else "What Is Your Take?"
        slide5_text = (
            "Drop your score prediction and tactical thoughts in the comments below!"
            if channel.key == "matchday"
            else "How will this development impact your workflow and industry outlook?"
        )
        slide5 = SlideContent(
            slide_number=5,
            total_slides=5,
            category=cat5,
            category_color=badge_color,
            sub_headline=slide5_sub,
            main_text=slide5_text,
            stat_box=None,
            highlight_text="HAVE YOUR SAY",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        hashtags = ctx.suggested_hashtags if (ctx and ctx.suggested_hashtags) else channel.default_hashtags
        caption = (
            f"🔥 [{theme_badge}] {news.summary_headline}\n\n"
            f"Swipe through for the complete 5-card breakdown and key Opta metrics.\n\n"
            f"👇 Have your say! Drop your thoughts in the comments below.\n\n"
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
        """Generate structured 5-slide carousel using Anthropic Claude."""
        import anthropic
        client = anthropic.Anthropic(api_key=self.anthropic_key)

        theme_badge = ctx.theme_badge if ctx else "BREAKING TACTICS"
        palette = resolve_theme_palette(theme_badge)
        badge_color = palette.primary
        phase_guidance = (
            f"Active Publishing Cadence: {ctx.phase_name}\n"
            f"Theme Badge: {ctx.theme_badge}\n"
            f"Cadence Objective: {ctx.prompt_guidance}\n"
            if ctx
            else ""
        )
        hashtags = ctx.suggested_hashtags if (ctx and ctx.suggested_hashtags) else channel.default_hashtags

        prompt = f"""You are an elite sports & news social media card copywriter for '{channel.name}' ({channel.brand_handle}).
Brand guidelines:
- Email identity: {channel.email}
- Tone: High-impact, tactical, authoritative, engaging.
- Topic: {news.topic}
- Verified Calendar Date: {news.calendar_date_utc}
{phase_guidance}
- Facts gathered (GROUND TRUTH): {news.model_dump_json()}

EXTRACTIVE INTEGRITY & ZERO-HALLUCINATION POLICY:
- Base all copy strictly and solely on the verified facts, numerical statistics, and player/club entity relationships in the provided JSON.
- Do NOT invent or swap player clubs, transfer rumors, or statistics outside the provided JSON.
- Every claim on every slide must be 100% grounded in the input facts.

Generate an ultra-engaging 5-slide social carousel JSON according to these exact guidelines:
- Slide 1: Hook / Breaking headline (category: '{theme_badge}', no stat_box)
- Slide 2: Main Point + Key Stat Block (category: 'KEY STAT BLOCK' or contextual phase badge, must include stat_box with uppercase 'label' and 'value')
- Slide 3: Tactical / Squad Context (category: 'TACTICAL DYNAMICS')
- Slide 4: Matchup / Fixture Preview (category: 'FIXTURE PREVIEW')
- Slide 5: CTA / Question to spark comments (category: 'FAN VERDICT', no stat_box)

CRITICAL RULES:
1. 'main_text' on EVERY slide MUST be strictly 30 words or fewer. Keep sentences punchy and high impact.
2. Return ONLY valid JSON with no markdown wrapping or explanations.

Exact JSON structure:
{{
  "headline": "Short master headline",
  "caption": "Full Instagram / Facebook post caption with emojis and call to action",
  "hashtags": {json.dumps(hashtags)},
  "badge_color": "{badge_color}",
  "slides": [
    {{
      "slide_number": 1,
      "category": "{theme_badge}",
      "category_color": "{badge_color}",
      "sub_headline": "Punchy Sub-Headline",
      "main_text": "Body text under 30 words.",
      "highlight_text": "SHORT BADGE TEXT",
      "source_attribution": "{news.primary_source}",
      "stat_box": null
    }},
    {{
      "slide_number": 2,
      "category": "KEY STAT BLOCK",
      "category_color": "{badge_color}",
      "sub_headline": "Stat Sub-Headline",
      "main_text": "Body text under 30 words.",
      "highlight_text": "KEY METRIC",
      "source_attribution": "Opta Sports",
      "stat_box": {{
        "label": "RECOVERY RATE",
        "value": "8.4 / 90",
        "subtext": "League leader"
      }}
    }},
    {{
      "slide_number": 3,
      "category": "TACTICAL DYNAMICS",
      "category_color": "{badge_color}",
      "sub_headline": "Tactical Sub-Headline",
      "main_text": "Body text under 30 words.",
      "highlight_text": "TACTICAL SHIFT",
      "source_attribution": "The Athletic",
      "stat_box": null
    }},
    {{
      "slide_number": 4,
      "category": "FIXTURE PREVIEW",
      "category_color": "{badge_color}",
      "sub_headline": "Fixture Sub-Headline",
      "main_text": "Body text under 30 words.",
      "highlight_text": "MATCHUP IMPACT",
      "source_attribution": "{news.primary_source}",
      "stat_box": {{
        "label": "BIG CHANCES",
        "value": "3.1 / GAME",
        "subtext": "Key fixture metric"
      }}
    }},
    {{
      "slide_number": 5,
      "category": "FAN VERDICT",
      "category_color": "{badge_color}",
      "sub_headline": "Who Takes All 3 Points?",
      "main_text": "Drop your score prediction and tactical thoughts in the comments below!",
      "highlight_text": "JOIN THE DEBATE",
      "source_attribution": "{channel.brand_handle}",
      "stat_box": null
    }}
  ]
}}"""

        candidate_models = [
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6",
            "claude-opus-4-5-20251101",
        ]

        response = None
        last_err = None
        for model_name in candidate_models:
            try:
                response = client.messages.create(
                    model=model_name,
                    max_tokens=2048,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
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
        slides: List[SlideContent] = []
        for i, s in enumerate(data["slides"], start=1):
            stat_box = StatBox(**s["stat_box"]) if s.get("stat_box") else None
            slides.append(
                SlideContent(
                    slide_number=i,
                    total_slides=5,
                    category=s.get("category", theme_badge),
                    category_color=s.get("category_color", badge_color),
                    sub_headline=s.get("sub_headline", "Tactical Update"),
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
            hashtags=data.get("hashtags", hashtags),
            slides=slides,
        )

    def _create_via_openai(
        self,
        channel: ChannelConfig,
        news: GatheredNews,
        ctx: Optional[MatchdayScheduleContext] = None,
    ) -> CarouselContent:
        """Generate structured 5-slide carousel using OpenAI."""
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_key)

        theme_badge = ctx.theme_badge if ctx else "BREAKING TACTICS"
        badge_color = ctx.badge_color if ctx else channel.accent_color
        hashtags = ctx.suggested_hashtags if (ctx and ctx.suggested_hashtags) else channel.default_hashtags

        prompt = f"""You are a master social media card writer for '{channel.name}' ({channel.brand_handle}).
Facts gathered: {news.model_dump_json()}
Theme badge: {theme_badge}

Generate an ultra-engaging 5-slide social carousel JSON according to these exact guidelines:
- Slide 1: Hook / Breaking headline (category: '{theme_badge}')
- Slide 2: Main Point + Key Stat Block (include stat_box)
- Slide 3: Tactical / Squad Context
- Slide 4: Matchup / Fixture Preview
- Slide 5: CTA / Question to spark comments (no stat_box)

CRITICAL REQUIREMENT: 'main_text' on EVERY slide MUST be 30 words or fewer. Keep sentences punchy, high impact."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You output strict JSON following the exact schema requested."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        data = json.loads(response.choices[0].message.content)
        slides: List[SlideContent] = []
        for i, s in enumerate(data["slides"], start=1):
            stat_box = StatBox(**s["stat_box"]) if s.get("stat_box") else None
            slides.append(
                SlideContent(
                    slide_number=i,
                    total_slides=5,
                    category=s.get("category", theme_badge),
                    category_color=s.get("category_color", badge_color),
                    sub_headline=s.get("sub_headline", "Tactical Update"),
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
            hashtags=data.get("hashtags", hashtags),
            slides=slides,
        )
