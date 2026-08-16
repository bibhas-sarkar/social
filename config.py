import os
from typing import Dict, List, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "src" / "templates"
DIST_DIR = BASE_DIR / "dist"


class StatBox(BaseModel):
    """Stat callout box displayed on cards."""
    label: str = Field(description="Short uppercase metric label, e.g. 'CHANCES CREATED' or 'ACCURACY'")
    value: str = Field(description="Value string, e.g. '3.4/90' or '89.2%' or '18 GOALS'")
    subtext: Optional[str] = Field(default=None, description="Optional brief context e.g. 'Top in Premier League'")


class SlideContent(BaseModel):
    """Structured data model for an individual carousel slide."""
    slide_number: int = Field(description="1-based slide index (1 to 5)")
    total_slides: int = Field(default=5, description="Total number of slides")
    category: str = Field(description="Badge text e.g. 'BREAKING TACTICS', 'SQUAD UPDATE', 'MATCH PREVIEW'")
    category_color: Optional[str] = Field(default=None, description="Custom hex color for category badge dot/border")
    sub_headline: str = Field(description="Punchy sub-headline or context hook")
    main_text: str = Field(description="Main body text, must be concise (<= 30 words)")
    stat_box: Optional[StatBox] = Field(default=None, description="Optional stat metric block")
    highlight_text: Optional[str] = Field(default=None, description="Highlighted keyword or short quote")
    source_attribution: Optional[str] = Field(default=None, description="Source attribution, e.g. 'Opta / The Athletic'")
    brand_handle: str = Field(default="@MatchdayEPL", description="Footer handle")


class CarouselContent(BaseModel):
    """Complete 5-slide carousel data payload with post caption."""
    channel_key: str
    topic: str
    headline: str
    caption: str
    badge_color: Optional[str] = Field(default=None, description="Theme badge color for the carousel")
    hashtags: List[str] = Field(default_factory=list)
    slides: List[SlideContent] = Field(min_length=5, max_length=5)


class ThemePalette(BaseModel):
    """Color palette tokens for dynamic card badging and ambient gradients."""
    name: str
    primary: str  # Vibrant accent for badges, borders, and numbers
    secondary: str  # Dark ambient background gradient
    glow: str  # Ambient glow color
    text_accent: str  # Subtext and label accent


THEME_PALETTES: Dict[str, ThemePalette] = {
    "breaking": ThemePalette(
        name="Breaking / Live / Injuries",
        primary="#F43F5E",  # Rose / Crimson
        secondary="#2A0A12",
        glow="rgba(244, 63, 94, 0.35)",
        text_accent="#FDA4AF",
    ),
    "tactics": ThemePalette(
        name="Tactical Breakdown / Opta",
        primary="#00F0FF",  # Electric Cyan
        secondary="#041C2C",
        glow="rgba(0, 240, 255, 0.35)",
        text_accent="#67E8F9",
    ),
    "fpl": ThemePalette(
        name="FPL Scout / Differentials",
        primary="#F59E0B",  # Vibrant Amber / Gold
        secondary="#261600",
        glow="rgba(245, 158, 11, 0.35)",
        text_accent="#FDE68A",
    ),
    "results": ThemePalette(
        name="Matchday Results / Debrief",
        primary="#00FF87",  # Emerald Neon Green
        secondary="#021D13",
        glow="rgba(0, 255, 135, 0.35)",
        text_accent="#A7F3D0",
    ),
    "marquee": ThemePalette(
        name="Marquee / Special Edition",
        primary="#A855F7",  # Royal Violet
        secondary="#240738",
        glow="rgba(168, 85, 247, 0.35)",
        text_accent="#D8B4FE",
    ),
}


def resolve_theme_palette(badge_or_category: Optional[str] = None) -> ThemePalette:
    """Resolve theme palette tokens from badge or category name."""
    if not badge_or_category:
        return THEME_PALETTES["results"]

    text = badge_or_category.upper().strip()
    if any(k in text for k in ["BREAK", "INJUR", "LIVE", "HOT TAKE"]):
        return THEME_PALETTES["breaking"]
    elif any(k in text for k in ["TACTIC", "BLUEPRINT", "SYSTEM", "OPTA", "PASS"]):
        return THEME_PALETTES["tactics"]
    elif any(k in text for k in ["FPL", "SCOUT", "CAPTAIN", "DIFFERENTIAL", "ASSET"]):
        return THEME_PALETTES["fpl"]
    elif any(k in text for k in ["DEBRIEF", "WRAP", "AUTOPSY", "REVIEW", "STANDINGS", "RESULT"]):
        return THEME_PALETTES["results"]
    elif any(k in text for k in ["PREVIEW", "INTEL", "FIXTURE", "MARQUEE", "SPECIAL"]):
        return THEME_PALETTES["marquee"]
    return THEME_PALETTES["results"]


class ChannelConfig(BaseModel):
    """Configuration model for an isolated content vertical."""
    key: str
    name: str
    email: str
    brand_handle: str
    category_name: str
    tagline: str
    template_path: str
    topic_prompt: str
    accent_color: str = "#00FF87"  # Default sports neon green
    secondary_color: str = "#021D3A"  # Dark navy/slate
    fb_page_id: Optional[str] = None
    ig_account_id: Optional[str] = None
    access_token: Optional[str] = None
    default_hashtags: List[str] = Field(default_factory=list)


def load_channels() -> Dict[str, ChannelConfig]:
    """Build and return registry of configured channels with environment variable overrides."""
    meta_token = os.getenv("META_SYSTEM_USER_TOKEN")

    channels: Dict[str, ChannelConfig] = {
        "matchday": ChannelConfig(
            key="matchday",
            name="Matchday EPL",
            email="matchday@leandev.studio",
            brand_handle="@MatchdayEPL",
            category_name="PREMIER LEAGUE INSIGHTS",
            tagline="Tactical Breakdowns • Transfer News • Match Analytics",
            template_path="matchday_card.html",
            topic_prompt=(
                "Focus on high-impact Premier League tactical shifts, breaking transfers, "
                "or key weekend fixture storylines with verified Opta/FBref-style metrics."
            ),
            accent_color="#00FF87",  # Premier League neon green
            secondary_color="#38003C",  # Premier League royal purple
            fb_page_id=os.getenv("MATCHDAY_FB_PAGE_ID"),
            ig_account_id=os.getenv("MATCHDAY_IG_ACCOUNT_ID"),
            access_token=meta_token,
            default_hashtags=[
                "#PremierLeague",
                "#EPL",
                "#MatchdayEPL",
                "#TacticalAnalysis",
                "#FootballStats",
                "#FPL",
            ],
        ),
        "worldnews": ChannelConfig(
            key="worldnews",
            name="Global Dispatch",
            email="news@leandev.studio",
            brand_handle="@GlobalDispatchHQ",
            category_name="WORLD NEWS",
            tagline="Geopolitics • Macroeconomics • Global Affairs",
            template_path="matchday_card.html",
            topic_prompt="Analyze key international developments with clear macroeconomic data.",
            accent_color="#3B82F6",  # Electric Blue
            secondary_color="#0F172A",
            fb_page_id=os.getenv("WORLDNEWS_FB_PAGE_ID"),
            ig_account_id=os.getenv("WORLDNEWS_IG_ACCOUNT_ID"),
            access_token=meta_token,
            default_hashtags=["#WorldNews", "#Geopolitics", "#GlobalEconomy"],
        ),
        "tech": ChannelConfig(
            key="tech",
            name="Kernel & Cloud",
            email="tech@leandev.studio",
            brand_handle="@KernelAndCloud",
            category_name="TECH & AI",
            tagline="Deep Tech • AI Research • Cloud Systems",
            template_path="matchday_card.html",
            topic_prompt="Break down frontier AI models, systems architecture, and engineering breakthroughs.",
            accent_color="#8B5CF6",  # Violet
            secondary_color="#09090B",
            fb_page_id=os.getenv("TECH_FB_PAGE_ID"),
            ig_account_id=os.getenv("TECH_IG_ACCOUNT_ID"),
            access_token=meta_token,
            default_hashtags=["#TechNews", "#AI", "#SoftwareEngineering"],
        ),
    }
    return channels


CHANNELS = load_channels()


def get_channel_config(channel_key: str) -> ChannelConfig:
    """Retrieve configuration for a specific channel key with fallback."""
    key = channel_key.lower().strip()
    if key not in CHANNELS:
        raise ValueError(
            f"Unknown channel '{channel_key}'. Available channels: {list(CHANNELS.keys())}"
        )
    return CHANNELS[key]
