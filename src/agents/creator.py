import os
import json
import logging
from typing import Optional, List
from config import ChannelConfig, CarouselContent, SlideContent, StatBox
from src.agents.gatherer import GatheredNews

logger = logging.getLogger(__name__)


class ContentCreatorAgent:
    """Agent responsible for structuring raw gathered facts into a 5-slide carousel format."""

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    def create(self, channel: ChannelConfig, news: GatheredNews) -> CarouselContent:
        """Create a 5-slide carousel payload from gathered news."""
        logger.info(f"[{channel.name}] Creating 5-slide structured carousel content...")

        # If LLM key is configured, use LLM for creative wording
        if self.openai_key:
            try:
                return self._create_via_openai(channel, news)
            except Exception as e:
                logger.warning(f"OpenAI creation failed: {e}. Using deterministic structured engine.")

        # Fallback / offline deterministic builder
        return self._create_structured_carousel(channel, news)

    def _create_structured_carousel(
        self, channel: ChannelConfig, news: GatheredNews
    ) -> CarouselContent:
        """Deterministic 5-slide structured generation following strict constraints."""
        facts = news.verified_facts

        # Slide 1: Hook / Breaking Headline
        slide1_text = (
            "Why this tactical battle will decide the Premier League title race this weekend."
            if channel.key == "matchday"
            else f"Essential briefing and critical takeaways from {channel.name}."
        )
        slide1 = SlideContent(
            slide_number=1,
            total_slides=5,
            category="BREAKING TACTICS" if channel.key == "matchday" else "SPECIAL REPORT",
            sub_headline=news.summary_headline,
            main_text=slide1_text,
            highlight_text="CRITICAL ANALYSIS",
            source_attribution=news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 2: Main Point + Key Stat Block
        fact1 = facts[0] if len(facts) > 0 else None
        slide2 = SlideContent(
            slide_number=2,
            total_slides=5,
            category="KEY STAT BLOCK" if channel.key == "matchday" else "PRIMARY METRIC",
            sub_headline=fact1.headline if fact1 else "Key Benchmark Performance",
            main_text=fact1.fact_text if fact1 else "Unmatched recovery metrics driving sustained performance.",
            stat_box=StatBox(
                label=fact1.key_metric if (fact1 and fact1.key_metric) else "BENCHMARK",
                value=fact1.metric_value if (fact1 and fact1.metric_value) else "100%",
                subtext="Verified analytical metric",
            ),
            highlight_text="PERFORMANCE LEADER",
            source_attribution=fact1.source if fact1 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 3: Tactical / Squad Context
        fact2 = facts[1] if len(facts) > 1 else None
        slide3 = SlideContent(
            slide_number=3,
            total_slides=5,
            category="TACTICAL DYNAMICS" if channel.key == "matchday" else "CORE ARCHITECTURE",
            sub_headline=fact2.headline if fact2 else "System Architecture & Dynamics",
            main_text=fact2.fact_text if fact2 else "Accelerated adoption and optimization across all nodes.",
            stat_box=StatBox(
                label=fact2.key_metric if (fact2 and fact2.key_metric) else "SCALE",
                value=fact2.metric_value if (fact2 and fact2.metric_value) else "40% GAIN",
                subtext="Top tier benchmark rating",
            ) if fact2 and fact2.key_metric else None,
            highlight_text="KEY LEVER",
            source_attribution=fact2.source if fact2 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 4: Matchup / Fixture Preview
        fact3 = facts[2] if len(facts) > 2 else None
        slide4 = SlideContent(
            slide_number=4,
            total_slides=5,
            category="FIXTURE PREVIEW" if channel.key == "matchday" else "OUTLOOK & IMPACT",
            sub_headline=fact3.headline if fact3 else "Forward Projections",
            main_text=fact3.fact_text if fact3 else "Long-term efficiency gains continue to reshape operating models.",
            stat_box=StatBox(
                label=fact3.key_metric if (fact3 and fact3.key_metric) else "METRIC",
                value=fact3.metric_value if (fact3 and fact3.metric_value) else "99.9%",
                subtext="Field verified index",
            ) if fact3 and fact3.key_metric else None,
            highlight_text="FUTURE OUTLOOK",
            source_attribution=fact3.source if fact3 else news.primary_source,
            brand_handle=channel.brand_handle,
        )

        # Slide 5: CTA / Question to spark comments
        slide5_sub = "Who Takes All 3 Points?" if channel.key == "matchday" else "What Is Your Take?"
        slide5_text = (
            "Can the high press neutralize Haaland, or will City find the breakthrough?"
            if channel.key == "matchday"
            else "How will this development impact your workflow and industry outlook?"
        )
        slide5 = SlideContent(
            slide_number=5,
            total_slides=5,
            category="FAN VERDICT" if channel.key == "matchday" else "COMMUNITY DEBATE",
            sub_headline=slide5_sub,
            main_text=slide5_text,
            stat_box=None,
            highlight_text="JOIN THE DISCUSSION",
            source_attribution=channel.brand_handle,
            brand_handle=channel.brand_handle,
        )

        caption = (
            f"🔥 {news.summary_headline}\n\n"
            f"Swipe through for the complete 5-card breakdown and key Opta metrics.\n\n"
            f"👇 Who dominates the midfield battle this weekend? Drop your score prediction below!\n\n"
            f"{' '.join(channel.default_hashtags)}"
        )

        return CarouselContent(
            channel_key=channel.key,
            topic=news.topic,
            headline=news.summary_headline,
            caption=caption,
            hashtags=channel.default_hashtags,
            slides=[slide1, slide2, slide3, slide4, slide5],
        )

    def _create_via_openai(self, channel: ChannelConfig, news: GatheredNews) -> CarouselContent:
        """Generate structured 5-slide carousel using OpenAI."""
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_key)

        schema = {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "caption": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
                "slides": {
                    "type": "array",
                    "minItems": 5,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "slide_number": {"type": "integer"},
                            "category": {"type": "string"},
                            "sub_headline": {"type": "string"},
                            "main_text": {"type": "string", "description": "Strictly under 30 words"},
                            "highlight_text": {"type": "string"},
                            "source_attribution": {"type": "string"},
                            "stat_box": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "value": {"type": "string"},
                                    "subtext": {"type": "string"}
                                },
                                "required": ["label", "value"]
                            }
                        },
                        "required": ["slide_number", "category", "sub_headline", "main_text"]
                    }
                }
            },
            "required": ["headline", "caption", "hashtags", "slides"]
        }

        prompt = f"""You are a master social media card writer for '{channel.name}' ({channel.brand_handle}).
Facts gathered: {news.model_dump_json()}

Generate an ultra-engaging 5-slide social carousel JSON according to these exact guidelines:
- Slide 1: Hook / Breaking headline
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
                    category=s.get("category", "MATCHDAY INSIGHT"),
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
            hashtags=data.get("hashtags", channel.default_hashtags),
            slides=slides,
        )
