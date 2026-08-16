import os
import asyncio
from pathlib import Path
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

from config import TEMPLATES_DIR, DIST_DIR, ChannelConfig, CarouselContent, SlideContent


class CardRenderer:
    """Headless Playwright renderer compiling Jinja2 HTML templates into 1080x1350 PNG cards."""

    def __init__(self, templates_dir: Optional[Path] = None, dist_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.dist_dir = dist_dir or DIST_DIR
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render_slide_html(self, channel: ChannelConfig, slide: SlideContent) -> str:
        """Render a single slide HTML using Jinja2."""
        template = self.jinja_env.get_template(channel.template_path)
        context = {
            "channel_name": channel.name,
            "brand_handle": channel.brand_handle,
            "email": channel.email,
            "category_name": channel.category_name,
            "accent_color": channel.accent_color,
            "secondary_color": channel.secondary_color,
            "category": slide.category,
            "slide_number": slide.slide_number,
            "total_slides": slide.total_slides,
            "sub_headline": slide.sub_headline,
            "main_text": slide.main_text,
            "stat_box": slide.stat_box.model_dump() if slide.stat_box else None,
            "highlight_text": slide.highlight_text,
            "source_attribution": slide.source_attribution,
        }
        return template.render(**context)

    async def render_carousel_async(
        self, channel: ChannelConfig, carousel: CarouselContent
    ) -> List[Path]:
        """Render all 5 slides of a carousel asynchronously to high-resolution PNGs."""
        channel_dist = self.dist_dir / channel.key
        channel_dist.mkdir(parents=True, exist_ok=True)

        output_paths: List[Path] = []

        async with async_playwright() as p:
            # Launch headless chromium
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--font-render-hinting=none",
                ],
            )

            # High-resolution context: 1080x1350 at 2x scale for crisp 4:5 mobile display
            context = await browser.new_context(
                viewport={"width": 1080, "height": 1350},
                device_scale_factor=2,
            )
            page = await context.new_page()

            for slide in carousel.slides:
                html_content = self.render_slide_html(channel, slide)
                
                # Set content and ensure web fonts & network requests complete
                await page.set_content(html_content, wait_until="networkidle")
                
                # Small wait to guarantee font rendering & CSS gradient layout passes
                await asyncio.sleep(0.3)

                output_path = channel_dist / f"slide_{slide.slide_number}.png"
                await page.screenshot(
                    path=str(output_path),
                    type="png",
                    full_page=False,
                )
                output_paths.append(output_path)

            await context.close()
            await browser.close()

        return output_paths

    def render_carousel(
        self, channel: ChannelConfig, carousel: CarouselContent
    ) -> List[Path]:
        """Synchronous wrapper for rendering cards."""
        return asyncio.run(self.render_carousel_async(channel, carousel))
