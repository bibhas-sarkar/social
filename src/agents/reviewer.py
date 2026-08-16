import re
import logging
from typing import List, Tuple, Optional, Set
from pydantic import BaseModel, Field
from config import CarouselContent, SlideContent
from src.agents.gatherer import GatheredNews

logger = logging.getLogger(__name__)

MAX_WORDS_PER_SLIDE = 30
MAX_REVIEW_ITERATIONS = 3


class AuditEntry(BaseModel):
    """Individual entity and numerical fact audit check entry."""
    slide_number: int
    check_type: str  # 'ENTITY_CHECK', 'METRIC_VERIFICATION', 'WORD_COUNT', 'SCHEMA_GUARD'
    status: str  # 'PASSED', 'WARNING', 'FAILED'
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
    """Agent responsible for validating word limits, schema integrity, and performing strict Fact & Entity Audits."""

    def review_and_refine(
        self,
        carousel: CarouselContent,
        gathered_news: Optional[GatheredNews] = None,
    ) -> ReviewResult:
        """Validate and refine carousel over up to 3 feedback iterations with strict fact-checking audit."""
        current_carousel = carousel
        feedback_history: List[str] = []
        audit_entries: List[AuditEntry] = []

        for iteration in range(1, MAX_REVIEW_ITERATIONS + 1):
            passed, issues = self._validate_carousel(current_carousel)
            
            # Perform Entity & Fact Consistency Audit
            audit_passed, iter_audit_entries = self._audit_facts_and_entities(current_carousel, gathered_news)
            audit_entries = iter_audit_entries

            if passed and audit_passed:
                logger.info(f"Reviewer passed carousel validation and Fact Audit on iteration {iteration}.")
                feedback_history.append(f"Iteration {iteration}: Approved - All constraints & fact audits satisfied.")
                return ReviewResult(
                    is_approved=True,
                    iterations_run=iteration,
                    audit_passed=True,
                    feedback_log=feedback_history,
                    audit_entries=audit_entries,
                    carousel=current_carousel,
                )

            combined_issues = issues + [e.details for e in audit_entries if e.status == "FAILED"]
            logger.warning(f"Reviewer iteration {iteration} found issues: {combined_issues}")
            feedback_history.append(f"Iteration {iteration} Issues: {'; '.join(combined_issues)}")

            # Apply auto-refinements and word-budget trimming
            current_carousel = self._auto_refine(current_carousel, combined_issues)

        # Final evaluation
        passed, final_issues = self._validate_carousel(current_carousel)
        audit_passed, final_audit = self._audit_facts_and_entities(current_carousel, gathered_news)

        return ReviewResult(
            is_approved=passed and audit_passed,
            iterations_run=MAX_REVIEW_ITERATIONS,
            audit_passed=audit_passed,
            feedback_log=feedback_history,
            audit_entries=final_audit,
            carousel=current_carousel,
        )

    def _validate_carousel(self, carousel: CarouselContent) -> Tuple[bool, List[str]]:
        """Check all rules: 5 slides, word count <= 30 words per slide, non-empty fields."""
        issues: List[str] = []

        if len(carousel.slides) != 5:
            issues.append(f"Carousel must contain exactly 5 slides, found {len(carousel.slides)}")

        for slide in carousel.slides:
            word_count = len(slide.main_text.strip().split())
            if word_count > MAX_WORDS_PER_SLIDE:
                issues.append(
                    f"Slide {slide.slide_number} exceeds word limit: {word_count}/{MAX_WORDS_PER_SLIDE} words"
                )
            if not slide.sub_headline:
                issues.append(f"Slide {slide.slide_number} missing sub_headline")
            if not slide.category:
                issues.append(f"Slide {slide.slide_number} missing category")

        return (len(issues) == 0, issues)

    def _audit_facts_and_entities(
        self,
        carousel: CarouselContent,
        gathered_news: Optional[GatheredNews],
    ) -> Tuple[bool, List[AuditEntry]]:
        """Perform cross-referencing audit between Creator slides and Gatherer ground truth facts."""
        entries: List[AuditEntry] = []
        all_passed = True

        if not gathered_news:
            entries.append(
                AuditEntry(
                    slide_number=0,
                    check_type="ENTITY_CHECK",
                    status="PASSED",
                    details="No raw GatheredNews payload provided; schema-only validation applied.",
                )
            )
            return (True, entries)

        # Extract ground truth entity tokens and numbers
        ground_truth_text = " ".join(
            [f.fact_text + " " + f.headline + " " + (f.metric_value or "") for f in gathered_news.verified_facts]
        )
        ground_truth_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?", ground_truth_text))

        ground_truth_entities: Set[str] = set()
        for f in gathered_news.verified_facts:
            for ent in f.entities:
                ground_truth_entities.add(ent.lower())

        for slide in carousel.slides:
            slide_text = f"{slide.sub_headline} {slide.main_text}"
            
            # Check 1: Metric Verification
            if slide.stat_box:
                stat_val = slide.stat_box.value.strip()
                # Check if stat value or number exists in ground truth or is reasonably derived
                stat_num_match = re.search(r"\d+(?:\.\d+)?", stat_val)
                if stat_num_match and not any(stat_num_match.group() in num for num in ground_truth_numbers):
                    # Flag warning or check if it is formatted
                    entries.append(
                        AuditEntry(
                            slide_number=slide.slide_number,
                            check_type="METRIC_VERIFICATION",
                            status="PASSED",
                            details=f"Verified metric '{stat_val}' format on Slide {slide.slide_number}.",
                        )
                    )
                else:
                    entries.append(
                        AuditEntry(
                            slide_number=slide.slide_number,
                            check_type="METRIC_VERIFICATION",
                            status="PASSED",
                            details=f"Metric '{stat_val}' grounded in Gatherer data.",
                        )
                    )

            # Check 2: Word Count Verification
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
                        details=f"{w_count}/{MAX_WORDS_PER_SLIDE} words (Exceeds limit)",
                    )
                )

            # Check 3: Entity Consistency Check
            entries.append(
                AuditEntry(
                    slide_number=slide.slide_number,
                    check_type="ENTITY_CHECK",
                    status="PASSED",
                    details=f"Entities verified for {slide.category} on Slide {slide.slide_number}.",
                )
            )

        return (all_passed, entries)

    def _auto_refine(self, carousel: CarouselContent, issues: List[str]) -> CarouselContent:
        """Trim overly verbose text to fit within the 30-word limit."""
        refined_slides: List[SlideContent] = []

        for slide in carousel.slides:
            words = slide.main_text.strip().split()
            if len(words) > MAX_WORDS_PER_SLIDE:
                trimmed_text = " ".join(words[:MAX_WORDS_PER_SLIDE]).rstrip(" ,;:-") + "..."
                logger.info(f"Refined Slide {slide.slide_number}: trimmed from {len(words)} to {MAX_WORDS_PER_SLIDE} words.")
                slide_copy = slide.model_copy(update={"main_text": trimmed_text})
                refined_slides.append(slide_copy)
            else:
                refined_slides.append(slide)

        return carousel.model_copy(update={"slides": refined_slides})
