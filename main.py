import argparse
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import get_channel_config, CHANNELS, resolve_theme_palette
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
from src.scheduler.autonomous_scheduler import (
    MatchdayAutonomousScheduler,
    CADENCE_SLOTS,
)

# Setup logging & Rich console
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
console = Console()


def run_pipeline(
    channel_key: str = "matchday",
    dry_run: bool = True,
    topic_override: Optional[str] = None,
    run_monitor: bool = True,
    auto_schedule: bool = False,
    phase_override: Optional[str] = None,
    slot_id: Optional[int] = None,
) -> bool:
    """Execute the multi-agent autonomous publishing pipeline with strict fact-checking guardrails."""
    try:
        channel = get_channel_config(channel_key)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return False

    # 0. RESOLVE SCHEDULE CONTEXT & THEME PALETTE
    schedule_context: Optional[MatchdayScheduleContext] = None
    if slot_id:
        scheduler = MatchdayAutonomousScheduler(channel_key)
        schedule_context = scheduler.build_slot_context(slot_id)
    elif channel_key == "matchday" or auto_schedule or phase_override:
        try:
            schedule_context = get_current_matchday_context(override_phase=phase_override)
        except ValueError as e:
            console.print(f"[bold red]Schedule Error:[/bold red] {e}")
            return False

    active_theme = resolve_theme_palette(
        schedule_context.theme_badge if schedule_context else "TACTICS"
    )

    # Rich Startup Banner
    banner_text = (
        f"[bold cyan]AUTONOMOUS SOCIAL CARD PUBLISHING ENGINE[/bold cyan]\n"
        f"[bold white]Channel:[/bold white] [green]{channel.name}[/green] ({channel.brand_handle})\n"
        f"[bold white]Email Account:[/bold white] [yellow]{channel.email}[/yellow]\n"
        f"[bold white]Mode:[/bold white] [bold magenta]{'DRY RUN (No live Meta API calls)' if dry_run else 'LIVE PUBLISH'}[/bold magenta]"
    )
    if schedule_context:
        banner_text += (
            f"\n[bold white]Cadence Phase:[/bold white] {schedule_context.phase_name} "
            f"([bold {active_theme.primary}]Theme Badge: {schedule_context.theme_badge}[/bold {active_theme.primary}])\n"
            f"[bold white]Theme Palette:[/bold white] {active_theme.name} ([dim]Primary: {active_theme.primary}[/dim])\n"
            f"[bold white]Topic Focus:[/bold white] [italic]{schedule_context.topic_focus}[/italic]"
        )

    console.print(Panel(banner_text, border_style="cyan"))

    # 1. NEWS GATHERER AGENT (With UTC Date & Entity Grounding)
    console.print("\n[bold blue]▶ [Step 1/5] Running NewsGathererAgent (Date & Entity Grounding)...[/bold blue]")
    gatherer = NewsGathererAgent()
    gathered_news = gatherer.gather(
        channel=channel,
        topic_override=topic_override,
        schedule_context=schedule_context,
    )
    console.print(f"  ✓ Verified Calendar Date: [cyan]{gathered_news.calendar_date_utc}[/cyan]")
    console.print(
        f"  ✓ Gathered [bold green]{len(gathered_news.verified_facts)} verified facts[/bold green] for: [yellow]{gathered_news.summary_headline}[/yellow]"
    )
    console.print(f"  ✓ Primary Source: [dim]{gathered_news.primary_source}[/dim]")

    # 2. CONTENT CREATOR AGENT (Extractive Policy & Dynamic Badges)
    console.print("\n[bold blue]▶ [Step 2/5] Running ContentCreatorAgent (Extractive Policy & Cadence Badging)...[/bold blue]")
    creator = ContentCreatorAgent()
    carousel_draft = creator.create(
        channel=channel,
        news=gathered_news,
        schedule_context=schedule_context,
    )
    console.print(f"  ✓ Generated 5-card carousel schema: [bold]{carousel_draft.headline}[/bold]")
    console.print(f"  ✓ Theme Accent: [bold {carousel_draft.badge_color}]{carousel_draft.badge_color}[/bold {carousel_draft.badge_color}]")

    # 3. REVIEWER AGENT (Entity & Fact Consistency Audit + Smart Trimming)
    console.print("\n[bold blue]▶ [Step 3/5] Running ReviewerAgent (Entity & Fact Consistency Audit)...[/bold blue]")
    reviewer = ReviewerAgent()
    review_result = reviewer.review_and_refine(
        carousel=carousel_draft,
        gathered_news=gathered_news,
    )

    if not review_result.is_approved:
        console.print(
            f"[bold red]✗ Reviewer rejected carousel:[/bold red] {review_result.feedback_log}"
        )
        return False

    console.print(f"  ✓ Carousel Approved after [bold green]{review_result.iterations_run} iteration(s)[/bold green].")

    # Display Entity & Fact Audit Table
    audit_table = Table(title="Entity, Metric & Constraint Audit Report", border_style="cyan")
    audit_table.add_column("Slide", justify="center", style="cyan", no_wrap=True)
    audit_table.add_column("Check Type", style="bold yellow")
    audit_table.add_column("Status", justify="center")
    audit_table.add_column("Audit Details", style="white")

    for entry in review_result.audit_entries:
        audit_table.add_row(
            f"0{entry.slide_number}" if entry.slide_number > 0 else "ALL",
            entry.check_type,
            f"[{'green' if entry.status == 'PASSED' else 'red'}]{entry.status}[/]",
            entry.details,
        )
    console.print(audit_table)

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
    console.print("\n[bold blue]▶ [Step 4/5] Running Headless Playwright CardRenderer (Dynamic Theme Palettes)...[/bold blue]")
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
                f"[bold]Engagement Rate:[/bold] {report.engagement_rate:.1f}%\n"
                f"[bold]Saves:[/bold] {report.saves} | "
                f"[bold]Shares:[/bold] {report.shares} | "
                f"[bold]Likes:[/bold] {report.likes} | "
                f"[bold]Comments:[/bold] {report.comments}\n"
                f"[bold]Verdict:[/bold] [green]{report.performance_verdict}[/green]\n"
                f"[bold]Feedback Recommendation:[/bold] [yellow]{report.feedback_recommendation}[/yellow]",
                title="24h Performance & Loop Recommendation",
                border_style="green" if report.engagement_rate > 5.0 else "yellow",
            )
        )

    console.print(
        "\n[bold green]✔ Autonomous Pipeline Cycle Completed Successfully with Zero-Hallucination Guardrails![/bold green]\n"
    )
    return True


# Account Warmup Safeguards (Anti-Spam Flags Prevention)
WARMUP_MODE = True
WARMUP_MAX_POSTS_PER_DAY = 2
MIN_COOLDOWN_SECONDS = 4 * 3600  # 4 hours minimum between posts
WARMUP_ALLOWED_SLOTS = [2, 4]  # Midday FPL Scout & Evening Match Debrief


def _get_published_state_path() -> Path:
    state_dir = Path(__file__).resolve().parent / "dist"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "published_slots.json"


def _load_published_state() -> Dict[str, Any]:
    state_file = _get_published_state_path()
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_published_state(date_str: str, slot_id: int):
    state_file = _get_published_state_path()
    data = _load_published_state()
    if "slots_by_date" not in data:
        data["slots_by_date"] = {}
    if date_str not in data["slots_by_date"]:
        data["slots_by_date"][date_str] = []
    if slot_id not in data["slots_by_date"][date_str]:
        data["slots_by_date"][date_str].append(slot_id)
    data["last_published_timestamp"] = time.time()
    with open(state_file, "w") as f:
        json.dump(data, f, indent=2)


def run_daemon_loop(channel_key: str = "matchday", dry_run: bool = False):
    """Continuous daemon loop with account warmup rate limits, 4h cooldown, and anti-spam protection."""
    scheduler = MatchdayAutonomousScheduler(channel_key)
    console.print(f"[bold green]Starting Autonomous Matchday Daemon for {channel_key}...[/bold green]")
    console.print(f"[bold yellow]🛡️ Account Warmup Safeguards Active: Max {WARMUP_MAX_POSTS_PER_DAY} posts/day, Min 4h cooldown between posts.[/bold yellow]")
    console.print("[dim]Checking schedule every 60 seconds... (Press Ctrl+C to stop)[/dim]\n")

    while True:
        try:
            utc_now = datetime.now(timezone.utc)
            current_date = utc_now.strftime("%Y-%m-%d")
            
            state_data = _load_published_state()
            executed_slots_today = set(state_data.get("slots_by_date", {}).get(current_date, []))
            last_pub_ts = state_data.get("last_published_timestamp", 0)
            seconds_since_last_pub = time.time() - last_pub_ts

            current_slot = scheduler.get_current_slot()
            slot_id = current_slot["slot_id"]

            # Warmup filter: Only run allowed warmup slots and max 2/day
            if WARMUP_MODE and slot_id not in WARMUP_ALLOWED_SLOTS:
                logger.debug(f"[Warmup Guard] Slot {slot_id} skipped in warmup mode. Waiting for Midday/Evening slot.")
            elif len(executed_slots_today) >= WARMUP_MAX_POSTS_PER_DAY:
                logger.debug(f"[Warmup Guard] Daily post limit ({WARMUP_MAX_POSTS_PER_DAY}) reached for today ({current_date}).")
            elif seconds_since_last_pub < MIN_COOLDOWN_SECONDS and not dry_run:
                remaining_cooldown = int((MIN_COOLDOWN_SECONDS - seconds_since_last_pub) / 60)
                logger.debug(f"[Cooldown Guard] Cooldown active. {remaining_cooldown} minutes remaining before next post.")
            elif slot_id not in executed_slots_today:
                console.print(f"\n[bold magenta]⚡ Triggering Scheduled Slot {slot_id}: {current_slot['name']} ({current_slot['utc_time']} UTC)[/bold magenta]")
                success = run_pipeline(
                    channel_key=channel_key,
                    dry_run=dry_run,
                    slot_id=slot_id,
                )
                if success:
                    _save_published_state(current_date, slot_id)
                    console.print(f"[green]✓ Slot {slot_id} published successfully and recorded to persistent state. Next slot scheduled automatically.[/green]")
            else:
                logger.debug(f"Slot {slot_id} already executed today ({current_date}). Standing by.")

            time.sleep(60)
        except KeyboardInterrupt:
            console.print("\n[yellow]Daemon stopped by user.[/yellow]")
            break
        except Exception as e:
            logger.error(f"Daemon error: {e}")
            time.sleep(60)


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Multi-Channel Social Media Card Publishing Engine"
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
        "--slot",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="Execute a specific daily cadence slot (1: Morning Fixture Intel, 2: Midday FPL Scout, 3: Afternoon Opta Blueprint, 4: Evening Debrief).",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        default=False,
        help="Run continuously in background daemon mode executing 4x daily cadence slots.",
    )
    parser.add_argument(
        "--print-cron",
        action="store_true",
        default=False,
        help="Print ready-to-use Linux crontab configuration for VPS deployment.",
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

    if args.print_cron:
        scheduler = MatchdayAutonomousScheduler(args.channel)
        print(scheduler.print_crontab_instructions())
        sys.exit(0)

    if args.daemon:
        run_daemon_loop(channel_key=args.channel, dry_run=args.dry_run)
        sys.exit(0)

    success = run_pipeline(
        channel_key=args.channel,
        dry_run=args.dry_run,
        topic_override=args.topic,
        run_monitor=not args.skip_monitor,
        auto_schedule=args.auto or (args.slot is not None),
        phase_override=args.phase,
        slot_id=args.slot,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
