import logging
from typing import List, Tuple
from pydantic import BaseModel, Field
from config import CarouselContent, SlideContent

logger = logging.getLogger(__name__)

MAX_WORDS_PER_SLIDE = 30
MAX_REVIEW_ITERATIONS = 3


class ReviewResult(BaseModel):
    """Result of the quality and constraint review process."""
    is_approved: bool
    iterations_run: int
    feedback_log: List[str] = Field(default_factory=list)
    carousel: CarouselContent


class ReviewerAgent:
    """Agent responsible for validating word limits, schema integrity, and readability."""

    def review_and_refine(self, carousel: CarouselContent) -> ReviewResult:
        """Validate and refine carousel over up to 3 feedback iterations."""
        current_carousel = carousel
        feedback_history: List[str] = []

        for iteration in range(1, MAX_REVIEW_ITERATIONS + 1):
            passed, issues = self._validate_carousel(current_carousel)
            
            if passed:
                logger.info(f"Reviewer passed carousel validation on iteration {iteration}.")
                feedback_history.append(f"Iteration {iteration}: Approved - All constraints satisfied.")
                return ReviewResult(
                    is_approved=True,
                    iterations_run=iteration,
                    feedback_log=feedback_history,
                    carousel=current_carousel,
                )

            logger.warning(f"Reviewer iteration {iteration} found issues: {issues}")
            feedback_history.append(f"Iteration {iteration} Issues: {'; '.join(issues)}")

            # Apply auto-refinements and word-budget trimming
            current_carousel = self._auto_refine(current_carousel, issues)

        # Final check
        passed, final_issues = self._validate_carousel(current_carousel)
        return ReviewResult(
            is_approved=passed,
            iterations_run=MAX_REVIEW_ITERATIONS,
            feedback_log=feedback_history,
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
