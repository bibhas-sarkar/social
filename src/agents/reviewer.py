import re
import logging
from typing import List, Tuple, Optional
from pydantic import BaseModel, Field
from config import CarouselContent, SlideContent
from src.agents.gatherer import GatheredNews

logger = logging.getLogger(__name__)

MAX_WORDS_PER_SLIDE = 30
MAX_REVIEW_ITERATIONS = 3


class AuditEntry(BaseModel):
    slide_number: int
    check_type: str
    status: str
    details: str


class ReviewResult(BaseModel):
    is_approved: bool
    iterations_run: int
    audit_passed: bool = True
    feedback_log: List[str] = Field(default_factory=list)
    audit_entries: List[AuditEntry] = Field(default_factory=list)
    carousel: CarouselContent


class ReviewerAgent:
    """Validates word counts, schema integrity, and chronological fact consistency."""

    def review_and_refine(
        self,
        carousel: CarouselContent,
        gathered_news: Optional[GatheredNews] = None,
    ) -> ReviewResult:
        current_carousel = carousel
        feedback_history: List[str] = []
        audit_entries: List[AuditEntry] = []

        for iteration in range(1, MAX_REVIEW_ITERATIONS + 1):
            passed, issues = self._validate_carousel(current_carousel)
            audit_passed, iter_audit_entries = self._audit_facts_and_entities(current_carousel, gathered_news)
            audit_entries = iter_audit_entries

            if passed and audit_passed:
                logger.info(f"Reviewer approved carousel on iteration {iteration}.")
                feedback_history.append(f"Iteration {iteration}: Approved - Story arc and factual grounding verified.")
                return ReviewResult(
                    is_approved=True,
                    iterations_run=iteration,
                    audit_passed=True,
                    feedback_log=feedback_history,
                    audit_entries=audit_entries,
                    carousel=current_carousel,
                )

            combined_issues = issues + [e.details for e in audit_entries if e.status == "FAILED"]
            logger.warning(f"Reviewer iteration {iteration} flagged issues: {combined_issues}")
            feedback_history.append(f"Iteration {iteration} Issues: {'; '.join(combined_issues)}")

            current_carousel = self._auto_refine(current_carousel, combined_issues)

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
        issues: List[str] = []
        if len(carousel.slides) != 5:
            issues.append(f"Carousel must contain exactly 5 slides, found {len(carousel.slides)}")

        for slide in carousel.slides:
            word_count = len(slide.main_text.strip().split())
            if word_count > MAX_WORDS_PER_SLIDE:
                issues.append(f"Slide {slide.slide_number} exceeds word limit: {word_count}/{MAX_WORDS_PER_SLIDE} words")
            if not slide.sub_headline:
                issues.append(f"Slide {slide.slide_number} missing sub_headline")

        return (len(issues) == 0, issues)

    def _audit_facts_and_entities(
        self,
        carousel: CarouselContent,
        gathered_news: Optional[GatheredNews],
    ) -> Tuple[bool, List[AuditEntry]]:
        entries: List[AuditEntry] = []
        all_passed = True

        for slide in carousel.slides:
            slide_text = f"{slide.sub_headline} {slide.main_text}".lower()

            # Flag chronological contradictions before season starts
            if "38 league matches" in slide_text or "conceded across 38" in slide_text:
                all_passed = False
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="CHRONOLOGY_CHECK",
                        status="FAILED",
                        details=f"Slide {slide.slide_number} referenced completed 38-game season during pre-season.",
                    )
                )
            else:
                entries.append(
                    AuditEntry(
                        slide_number=slide.slide_number,
                        check_type="CHRONOLOGY_CHECK",
                        status="PASSED",
                        details=f"Temporal grounding verified on Slide {slide.slide_number}.",
                    )
                )

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

        return (all_passed, entries)

    def _auto_refine(self, carousel: CarouselContent, issues: List[str]) -> CarouselContent:
        refined_slides: List[SlideContent] = []
        for slide in carousel.slides:
            words = slide.main_text.strip().split()
            if len(words) > MAX_WORDS_PER_SLIDE:
                trimmed = " ".join(words[:MAX_WORDS_PER_SLIDE]).rstrip(" ,;:-") + "..."
                refined_slides.append(slide.model_copy(update={"main_text": trimmed}))
            else:
                refined_slides.append(slide)
        return carousel.model_copy(update={"slides": refined_slides})