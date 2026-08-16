import argparse
import sys
import logging
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import get_channel_config, CHANNELS
from src.scheduler.matchday_calendar import (
    get_current_matchday_context,
    MatchdayScheduleContext,
    SchedulePhase,
)
from src.agents.gatherer import NewsGathererAgent
from src.agents.creator import ContentCreatorAgent
from src.agents.reviewer import ReviewerAgent
from src.agents.social_publisher import MetaSocialPublisherAgent
from src.agents.monitor import AnalyticsMonitorAgent
from src.renderer.card_renderer import CardRenderer

# Setup logging & Rich console
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
console = Console()


def run_pipeline(
    channel_key: str = "matchday",
    dry_run: bool = True,
    topic_override: Optional[str] = None,
    run_monitor: bool = True,
    auto_schedule: bool = False,
    phase_override: Optional[str] = None,
) -> bool:
    """Execute the multi-agent autonomous publishing pipeline with dynamic cadence routing."""
    try:
        channel = get_channel_config(channel_key)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return False

    # 0. RESOLVE SCHEDULE CONTEXT (For matchday channel or when auto mode / phase override is enabled)
    schedule_context: Optional[MatchdayScheduleContext] = None
    if channel_key == "matchday" or auto_schedule or phase_override:
        try:
            schedule_context = get_current_matchday_context(override_phase=phase_override)
        except ValueError as e:
            console.print(f"[bold red]Schedule Error:[/bold red] {e}")
            return False

    # Rich Startup Banner
    banner_text = (
        f"[bold cyan]AUTONOMOUS SOCIAL CARD PUBLISHING ENGINE[/bold cyan]\n"
        f"[bold white]Channel:[/bold white] [green]{channel.name}[/green] ({channel.brand_handle})\n"
        f"[bold white]Email Account:[/bold white] [yellow]{channel.email}[/yellow]\n"
        f"[bold white]Mode:[/bold white] [bold magenta]{'DRY RUN (No live Meta API calls)' if dry_run else 'LIVE PUBLISH'}[/bold magenta]"
    )
    if schedule_context:
        banner_text += (
            f"\n[bold white]Cadence Phase:[/bold white] [bold yellow]{schedule_context.phase_name}[/bold yellow] "
            f"([bold white]Theme Badge:[/bold white] [{schedule_context.badge_color}]{schedule_context.theme_badge}[/{schedule_context.badge_color}])\n"
            f"[bold white]Topic Focus:[/bold white] [italic]{schedule_context.topic_focus}[/italic]"
        )

    console.print(Panel.fit(banner_text, border_style="cyan"))

    # 1. GATHERER AGENT
    console.print("\n[bold blue]▶ [Step 1/5] Running NewsGathererAgent (Schedule-Aware)...[/bold blue]")
    gatherer = NewsGathererAgent()
    gathered_news = gatherer.gather(
        channel,
        topic_override=topic_override,
        schedule_context=schedule_context,
    )
    console.print(f"  ✓ Gathered [bold]{len(gathered_news.verified_facts)} verified facts[/bold] for: [italic]{gathered_news.topic}[/italic]")
    console.print(f"  ✓ Primary Source: [dim]{gathered_news.primary_source}[/dim]")

    # 2. CREATOR AGENT
    console.print("\n[bold blue]▶ [Step 2/5] Running ContentCreatorAgent (Cadence Badging)...[/bold blue]")
    creator = ContentCreatorAgent()
    carousel_draft = creator.create(
        channel,
        gathered_news,
        schedule_context=schedule_context,
    )
    console.print(f"  ✓ Generated 5-card carousel schema: [bold]{carousel_draft.headline}[/bold]")
    if carousel_draft.badge_color:
        console.print(f"  ✓ Theme Palette: [{carousel_draft.badge_color}]{carousel_draft.badge_color}[/{carousel_draft.badge_color}]")

    # 3. REVIEWER AGENT
    console.print("\n[bold blue]▶ [Step 3/5] Running ReviewerAgent (Word Budget & Schema Guard)...[/bold blue]")
    reviewer = ReviewerAgent()
    review_result = reviewer.review_and_refine(carousel_draft)

    if not review_result.is_approved:
        console.print(f"[bold red]✗ Reviewer rejected carousel:[/bold red] {review_result.feedback_log}")
        return False

    console.print(f"  ✓ Carousel APPROVED after {review_result.iterations_run} review iteration(s).")
    for log in review_result.feedback_log:
        console.print(f"    [dim]{log}[/dim]")

    # Display Carousel Slides Summary Table
    table = Table(title="Approved 5-Slide Carousel Content", border_style="green")
    table.add_column("Slide", justify="center", style="cyan", no_wrap=True)
    table.add_column("Category", style="bold magenta")
    table.add_column("Sub-Headline", style="bold white")
    table.add_column("Body (<=30 words)", style="white")
    table.add_column("Stat Box", style="yellow")

    approved_carousel = review_result.carousel
    for s in approved_carousel.slides:
        stat_str = f"{s.stat_box.label}: {s.stat_box.value}" if s.stat_box else "-"
        table.add_row(
            f"0{s.slide_number}/0{s.total_slides}",
            f"[{s.category_color or 'white'}]{s.category}[/{s.category_color or 'white'}]",
            s.sub_headline,
            f"{s.main_text} [dim]({len(s.main_text.split())} words)[/dim]",
            stat_str,
        )
    console.print(table)

    # 4. PLAYWRIGHT CARD RENDERER
    console.print("\n[bold blue]▶ [Step 4/5] Running Headless Playwright CardRenderer (Dynamic Badge Coloring)...[/bold blue]")
    renderer = CardRenderer()
    output_pngs = renderer.render_carousel(channel, approved_carousel)
    console.print(f"  ✓ Rendered [bold green]{len(output_pngs)} cards[/bold green] (1080x1350 PNG) into [bold]{output_pngs[0].parent}[/bold]:")
    for p in output_pngs:
        console.print(f"    - [cyan]{p.name}[/cyan] ({p.stat().st_size // 1024} KB)")

    # 5. SOCIAL PUBLISHER AGENT
    console.print("\n[bold blue]▶ [Step 5/5] Running MetaSocialPublisherAgent...[/bold blue]")
    publisher = MetaSocialPublisherAgent()
    publish_result = publisher.publish_carousel(
        channel=channel,
        carousel=approved_carousel,
        image_paths=output_pngs,
        dry_run=dry_run,
    )
    console.print(f"  ✓ Publishing Status: [bold green]{publish_result.status}[/bold green]")
    if publish_result.instagram_post_id:
        console.print(f"    - Instagram Post ID: [cyan]{publish_result.instagram_post_id}[/cyan]")
    if publish_result.facebook_post_id:
        console.print(f"    - Facebook Post ID: [cyan]{publish_result.facebook_post_id}[/cyan]")

    # 6. OPTIONAL ANALYTICS MONITOR
    if run_monitor:
        console.print("\n[bold blue]▶ [Feedback Loop] Running AnalyticsMonitorAgent...[/bold blue]")
        monitor = AnalyticsMonitorAgent()
        report = monitor.extract_metrics(
            channel=channel,
            post_id=publish_result.instagram_post_id or "post_sample",
            timeframe="24h",
        )
        console.print(
            Panel(
                f"[bold]Impressions:[/bold] {report.impressions:,} | "
                f"[bold]Reach:[/bold] {report.reach:,} | "
                f"[bold]Engagement Rate:[/bold] {report.engagement_rate}%\n"
                f"[bold]Saves:[/bold] {report.saves} | [bold]Shares:[/bold] {report.shares} | [bold]Likes:[/bold] {report.likes}\n"
                f"[bold]Verdict:[/bold] [green]{report.performance_verdict}[/green]\n"
                f"[bold]Feedback Recommendation:[/bold] [italic]{report.feedback_recommendation}[/italic]",
                title="24h Performance & Loop Recommendation",
                border_style="yellow",
            )
        )

    console.print("\n[bold green]✔ Autonomous Cadence Publishing Cycle Completed Successfully![/bold green]\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Modular Autonomous Publishing Engine with Schedule-Aware Automation."
    )
    parser.add_argument(
        "--channel",
        type=str,
        default="matchday",
        help=f"Channel key to run (options: {list(CHANNELS.keys())}, default: matchday)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        default=False,
        help="Automatically resolve today's publishing cadence phase and generate matching cards.",
    )
    parser.add_argument(
        "--phase",
        type=str,
        default=None,
        choices=[p.value for p in SchedulePhase],
        help="Manually force a specific cadence phase (e.g. POST_MATCH_WRAP, MIDWEEK_ANALYSIS, FPL_PREVIEW, PRE_MATCH_PREVIEW, LIVE_MATCH_REACTION).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Execute full pipeline without making live Meta API publish calls.",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Optional custom topic override for gathering & card generation.",
    )
    parser.add_argument(
        "--skip-monitor",
        action="store_true",
        default=False,
        help="Skip the 24h feedback analytics monitoring report.",
    )

    args = parser.parse_args()

    success = run_pipeline(
        channel_key=args.channel,
        dry_run=args.dry_run,
        topic_override=args.topic,
        run_monitor=not args.skip_monitor,
        auto_schedule=args.auto,
        phase_override=args.phase,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
