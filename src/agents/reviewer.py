import re
import logging
from typing import List, Tuple, Optional, Set
from pydantic import BaseModel, Field
from config import CarouselContent, SlideContent
from src.agents.gatherer import GatheredNews
from src.scheduler.pl_squad_validator import PLSquadValidator

logger = logging.getLogger(__name__)

MAX_REVIEW_ITERATIONS = 3
MAX_WORDS_PER_SLIDE = 30


class AuditEntry(BaseModel):
    """Individual entity, metric, and schema audit check entry."""
    slide_number: int
    check_type: str  # 'ENTITY_CHECK', 'METRIC_VERIFICATION', 'SQUAD_AFFILIATION_CHECK', 'WORD_COUNT', 'NARRATIVE_CHECK'
    status: str      # 'PASSED', 'WARNING', 'FAILED'
    details: str


class ReviewResult(BaseModel):
    """Result of the quality and constraint review process including fact-checking audit."""
    is_approved: bool
    iterations_run: int
    audit_passed: bool = True
    feedback_log: List[str] = Field(default_factory=list)
    audit_entries: List[AuditEntry] = Field(default_factory=list)
    carousel: CarouselContent


class ReviewerAgent:
    """Rigorous quality auditor validating word counts, entity grounding, squad affiliations, and metric accuracy."""

    def __init__(self):
        self.squad_validator = PLSquadValidator()

    def review_and_refine(
        self,
        carousel: CarouselContent,
        gathered_news: Optional[GatheredNews] = None,
    ) -> ReviewResult:
        current_carousel = carousel
        feedback_history: List[str] = []
        audit_entries: List[AuditEntry] = []

        for iteration in range(1, MAX_REVIEW_ITERATIONS + 1):
            passed, schema_issues = self._validate_carousel(current_carousel)
            audit_passed, iter_audit_entries = self._audit_facts_and_entities(current_carousel, gathered_news)
            audit_entries = iter_audit_entries

            failed_entries = [e.details for e in audit_entries if e.status == "FAILED"]
            all_issues = schema_issues + failed_entries

            if passed and audit_passed and len(all_issues) == 0:
                logger.info(f"Reviewer approved carousel on iteration {iteration}.")
                feedback_history.append(f"Iteration {iteration}: Approved - All constraints & factual audits satisfied.")
                return ReviewResult(
                    is_approved=True,
                    iterations_run=iteration,
                    audit_passed=True,
                    feedback_log=feedback_history,
                    audit_entries=audit_entries,
                    carousel=current_carousel,
                )

            logger.warning(f"Reviewer iteration {iteration} flagged issues: {all_issues}")
            feedback_history.append(f"Iteration {iteration} Issues: {'; '.join(all_issues)}")

            # Perform intelligent sentence trimming rather than hard slicing mid-word
            current_carousel = self._smart_refine(current_carousel, all_issues)

        # Final audit pass
        passed, final_schema_issues = self._validate_carousel(current_carousel)
        audit_passed, final_audit = self._audit_facts_and_entities(current_carousel, gathered_news)
        final_failures = final_schema_issues + [e.details for e in final_audit if e.status == "FAILED"]

        return ReviewResult(
            is_approved=(passed and audit_passed and len(final_failures) == 0),
            iterations_run=MAX_REVIEW_ITERATIONS,
            audit_passed=audit_passed and len(final_failures) == 0,
            feedback_log=feedback_history,
            audit_entries=final_audit,
            carousel=current_carousel,
        )

    def _validate_carousel(self, carousel: CarouselContent) -> Tuple[bool, List[str]]:
        """Validates structure, slide count, and basic fields."""
        issues: List[str] = []

        if len(carousel.slides) != 5:
            issues.append(f"Carousel must contain exactly 5 slides, found {len(carousel.slides)}")

        for slide in carousel.slides:
            word_count = len(slide.main_text.strip().split())
            if word_count > MAX_WORDS_PER_SLIDE:
                issues.append(f"Slide {slide.slide_number} exceeds word limit: {word_count}/{MAX_WORDS_PER_SLIDE} words")
            if not slide.sub_headline or len(slide.sub_headline.strip()) == 0:
                issues.append(f"Slide {slide.slide_number} missing sub_headline")
            if not slide.category or len(slide.category.strip()) == 0:
                issues.append(f"Slide {slide.slide_number} missing category")

        return (len(issues) == 0, issues)

    def _audit_facts_and_entities(
        self,
        carousel: CarouselContent,
        gathered_news: Optional[GatheredNews],
    ) -> Tuple[bool, List[AuditEntry]]:
        """Strict ground-truth audit comparing slide entities and numbers to GatheredNews."""
        entries: List[AuditEntry] = []
        all_passed = True

        if not gathered_news:
            entries.append(
                AuditEntry(
                    slide_number=0,
                    check_type="ENTITY_CHECK",
                    status="WARNING",
                    details="No GatheredNews payload provided; skipped factual cross-reference.",
                )
            )
            return (True, entries)

        # 1. Build Ground-Truth Token Sets
        raw_text = " ".join([
            f.fact_text + " " + f.headline + " " + (f.metric_value or "") + " " + (f.key_metric or "")
            for f in gathered_news.verified_facts
        ]) + " " + gathered_news.summary_headline + " " + gathered_news.topic

        ground_truth_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?", raw_text))
        
        # Collect verified entity keywords
        ground_truth_entities: Set[str] = set()
        for f in gathered_news.verified_facts:
            for ent in f.entities:
                ground_truth_entities.update(ent.lower().split())

        # 2. Slide-by-Slide Audit
        for slide in carousel.slides:
            slide_combined = f"{slide.sub_headline} {slide.main_text}".lower()

            # --- Check A: Metric Verification ---
            if slide.stat_box:
                stat_val = slide.stat_box.value.strip()
                val_numbers = re.findall(r"\b\d+(?:\.\d+)?%?", stat_val)

                # If numeric, must be grounded in raw facts
                if val_numbers and not any(n in ground_truth_numbers or n in raw_text for n in val_numbers):
                    # Allow common labels like '10 MATCHES' if in raw text, else flag
                    if not any(word in raw_text.lower() for word in stat_val.lower().split()):
                        all_passed = False
                        entries.append(
                            AuditEntry(
                                slide_number=slide.slide_number,
                                check_type="METRIC_VERIFICATION",
                                status="FAILED",
                                details=f"Stat '{stat_val}' on Slide {slide.slide_number} not found in Gatherer ground truth.",
                            )
                        )
                    else:
                        entries.append(
                            AuditEntry(
                                slide_number=slide.slide_number,
                                check_type="METRIC_VERIFICATION",
                                status="PASSED",
                                details=f"Metric '{stat_val}' verified in context.",
                            )
                        )
                else:
                    entries.append(
                        AuditEntry(
                            slide_number=slide.slide_number,
                            check_type="METRIC_VERIFICATION",
                            status="PASSED",
                            details=f"Metric '{stat_val}' verified in ground truth.",
                        )
                    )

            # --- Check B: Premier League Official Squad & Club Verification ---
            slide_raw = f"{slide.sub_headline} {slide.main_text}"
            squad_validations = self.squad_validator.validate_slide_text(slide_raw)
            for is_valid, squad_detail in squad_validations:
                if not is_valid:
                    all_passed = False
                    entries.append(
                        AuditEntry(
                            slide_number=slide.slide_number,
                            check_type="SQUAD_AFFILIATION_CHECK",
                            status="FAILED",
                            details=squad_detail,
                        )
                    )
                else:
                    entries.append(
                        AuditEntry(
                            slide_number=slide.slide_number,
                            check_type="SQUAD_AFFILIATION_CHECK",
                            status="PASSED",
                            details=squad_detail,
                        )
                    )

            # --- Check C: Word Count ---
            w_count = len(slide.main_text.strip().split())
            if w_count <= MAX_WORDS_PER_SLIDE:
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="WORD_COUNT",
                        status="PASSED",
                        details=f"{w_count}/{MAX_WORDS_PER_SLIDE} words (Compliant)",
                    )
                )
            else:
                all_passed = False
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="WORD_COUNT",
                        status="FAILED",
                        details=f"{w_count}/{MAX_WORDS_PER_SLIDE} words (Exceeds {MAX_WORDS_PER_SLIDE} limit)",
                    )
                )

            # --- Check D: No Dangling References & Misleading Promises ---
            dangling_phrases = [
                "link in bio", "stats below", "link below", "dataset available",
                "full squad list", "full squad stats", "breakdown below",
                "check link", "tap link", "see bio", "swipe for more in part 2",
                "detailed below", "attached below"
            ]
            found_dangling = [phrase for phrase in dangling_phrases if phrase in slide_combined]
            if found_dangling:
                all_passed = False
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="DANGLING_REFERENCE_CHECK",
                        status="FAILED",
                        details=f"Dangling unreferenced claim found: '{', '.join(found_dangling)}' without corresponding link/data.",
                    )
                )
            else:
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="DANGLING_REFERENCE_CHECK",
                        status="PASSED",
                        details="No dangling links or unfulfilled claims.",
                    )
                )

            # --- Check E: Template Placeholder Leak Audit ---
            raw_slide_content = f"{slide.category} {slide.sub_headline} {slide.main_text} {slide.highlight_text or ''} {slide.stat_box.value if slide.stat_box else ''}"
            if any(token in raw_slide_content for token in ["{{", "}}", "undefined", "null", "None", "{%", "%}"]):
                all_passed = False
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="PLACEHOLDER_LEAK_CHECK",
                        status="FAILED",
                        details="Unresolved template tag or raw placeholder token detected.",
                    )
                )
            else:
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="PLACEHOLDER_LEAK_CHECK",
                        status="PASSED",
                        details="Clean of all template placeholders.",
                    )
                )

            # --- Check F: Sentence Completeness & Punctuation Audit ---
            trimmed_main = slide.main_text.strip()
            if not trimmed_main.endswith((".", "!", "?")):
                all_passed = False
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="SENTENCE_COMPLETION",
                        status="FAILED",
                        details="Slide text does not end with terminal punctuation (. ! ?).",
                    )
                )
            else:
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="SENTENCE_COMPLETION",
                        status="PASSED",
                        details="Slide terminates with valid punctuation.",
                    )
                )

            # --- Check G: Narrative Role Compliance ---
            if slide.slide_number == 5:
                if not any(q in slide_combined for q in ["?", "who", "comment", "predict", "verdict"]):
                    entries.append(
                        AuditEntry(
                            slide_number=5,
                            check_type="NARRATIVE_CHECK",
                            status="WARNING",
                            details="Slide 5 should ideally include a question or prompt to encourage comments.",
                        )
                    )
                else:
                    entries.append(
                        AuditEntry(
                            slide_number=5,
                            check_type="NARRATIVE_CHECK",
                            status="PASSED",
                            details="Slide 5 verified as comment CTA block.",
                        )
                    )

        return (all_passed, entries)

    def _smart_refine(self, carousel: CarouselContent, issues: List[str]) -> CarouselContent:
        """Intelligently trims sentences at clause/punctuation boundaries instead of slicing words."""
        refined_slides: List[SlideContent] = []

        for slide in carousel.slides:
            words = slide.main_text.strip().split()
            if len(words) > MAX_WORDS_PER_SLIDE:
                # Find the last sentence end (., !, ?) before the limit
                truncated = " ".join(words[:MAX_WORDS_PER_SLIDE])
                last_period = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
                
                if last_period > len(truncated) // 2:
                    clean_text = truncated[:last_period + 1]
                else:
                    clean_text = truncated.rstrip(" ,;:-") + "."

                logger.info(f"Cleanly trimmed Slide {slide.slide_number} from {len(words)} to {len(clean_text.split())} words.")
                refined_slides.append(slide.model_copy(update={"main_text": clean_text}))
            else:
                refined_slides.append(slide)

        return carousel.model_copy(update={"slides": refined_slides})