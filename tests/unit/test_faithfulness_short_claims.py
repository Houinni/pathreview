"""Regression tests for issue #152.

Faithfulness checker can never mark short claims as supported.

These tests encode the *expected* behaviour and are expected to FAIL against
the current implementation. They document three distinct root causes:

1. ``_is_supported`` tokenizes on whitespace only, so trailing punctuation in
   the context (``"Python."``) never matches a claim token (``"Python"``).
2. ``_is_supported`` requires an absolute ``>= 2`` meaningful-token overlap
   regardless of claim length, so a two-token claim must match 100% of its
   tokens and a one-meaningful-token claim can never be supported at all.
3. ``_extract_claims`` discards any sentence of 10 characters or fewer, so
   very short feedback yields zero claims and silently returns the 0.5
   neutral default instead of a real score.
"""

import pytest

from rag.evaluator.faithfulness_checker import FaithfulnessChecker


@pytest.mark.unit
class TestShortClaimsAreSupported:
    """Short but fully grounded claims must not be scored as unsupported."""

    @pytest.fixture
    def checker(self) -> FaithfulnessChecker:
        return FaithfulnessChecker()

    def test_punctuation_in_context_does_not_break_support(
        self, checker: FaithfulnessChecker
    ) -> None:
        """Root cause 1: 'Python.' in context must match 'Python' in claim."""
        score = checker.check(
            "Knows Python",
            [{"text": "The candidate knows Python."}],
        )

        assert score == 1.0, "Claim is verbatim in the context; only the trailing period differs."

    def test_short_claim_with_paraphrased_context_is_supported(
        self, checker: FaithfulnessChecker
    ) -> None:
        """Root cause 2: one strong keyword match is enough for a 2-word claim."""
        score = checker.check(
            "Knows Python",
            [{"text": "The candidate is proficient in Python and ships production services."}],
        )

        assert score == 1.0, "Context clearly grounds the claim, but only one token overlaps."

    def test_single_meaningful_token_claim_can_be_supported(
        self, checker: FaithfulnessChecker
    ) -> None:
        """Root cause 2: a claim with one meaningful token is not automatically false."""
        supported = checker._is_supported(
            "Uses Kubernetes",
            "Deployments are managed on Kubernetes.",
        )

        assert supported is True

    def test_very_short_claim_is_not_silently_dropped(self, checker: FaithfulnessChecker) -> None:
        """Root cause 3: a 9-char sentence must still be scored, not skipped."""
        score = checker.check(
            "Uses Rust",
            [{"text": "The candidate uses Rust for systems work."}],
        )

        assert score == 1.0, "Claim was dropped by the >10-character filter and fell back to 0.5."


@pytest.mark.unit
class TestExistingBehaviourPreserved:
    """Guardrails: the fix must not turn unsupported claims into supported ones."""

    @pytest.fixture
    def checker(self) -> FaithfulnessChecker:
        return FaithfulnessChecker()

    def test_unsupported_claim_stays_unsupported(self, checker: FaithfulnessChecker) -> None:
        score = checker.check(
            "This developer is an expert in Rust systems programming.",
            [{"text": "The developer has Python and JavaScript experience."}],
        )

        assert score == 0.0

    def test_long_supported_claim_stays_supported(self, checker: FaithfulnessChecker) -> None:
        score = checker.check(
            "The developer has strong Python skills and experience with Django.",
            [{"text": "The portfolio shows Python expertise and Django framework experience."}],
        )

        assert score == 1.0

    def test_stop_words_alone_are_not_support(self, checker: FaithfulnessChecker) -> None:
        supported = checker._is_supported(
            "The team is in the office",
            "A of to for that and or but in the",
        )

        assert supported is False
