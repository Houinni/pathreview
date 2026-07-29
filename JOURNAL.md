## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/152

**Issue title:** Faithfulness checker can never mark short claims as supported

**Tier:** [x] Tier 1  [ ] Tier 2  [ ] Tier 3

**Problem summary:**
The bug is in the faithfulness checker used by the RAG evaluator. Its current logic requires too much overlap between a claim and the supporting context, so short but fully grounded claims such as “Knows Python” are incorrectly scored as unsupported even when the context clearly matches them. This causes feedback that contains short, valid claims to receive a score of 0.0 instead of being treated as supported. A successful fix would make the checker handle short claims more gracefully while preserving correct behavior for unsupported or weakly supported statements.

**Branch name:** fix/152-faithfulness-checker-can-never-mark-short-claims-as-supported

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/Houinni/pathreview/commit/0eb6989624f25939c776f71540ea2c069d8fce38

**Reproduction summary:**
I called `FaithfulnessChecker.check()` directly with short claims against contexts that plainly support them, printing the intermediate token sets rather than just the score — `"Knows Python"` against `"The candidate knows Python."` returns 0.0, because whitespace tokenization leaves the context token as `python.` (period attached) so it never matches `python`. Printing the overlap sets revealed three independent causes rather than the one the issue describes: punctuation-blind tokenization, a fixed `>= 2` overlap threshold that a two-token claim can only clear by matching 100% of its tokens, and a `len(s) > 10` character filter that silently drops `"Uses Rust"` and returns the 0.5 neutral default. I also confirmed 3 of the 4 pre-existing failures in `tests/unit/test_faithfulness_checker.py` are this same bug on an unmodified tree, which is stronger evidence than my own cases.

**PLAN.md link:** https://github.com/Houinni/pathreview/blob/fix/152-faithfulness-checker-can-never-mark-short-claims-as-supported/PLAN.md

**Walkthrough video (recommended):**

**Blockers or open questions:**
The threshold change is a design decision I don't want to make unilaterally. Measured against 10 labelled cases, fixing tokenization alone passes 8/10 — and the only two failures are cases I invented, asserting that one keyword match should ground a two-word claim (`"Knows Python"` vs `"proficient in Python"`). No maintainer test requires this, three different ratios fit all 10 cases equally well (overfitting to a set I wrote myself), and loosening the threshold pushes a safety metric toward false positives. I've marked those two tests `xfail` and plan to ask on the issue before touching `>= 2`.

Also noted but deliberately out of scope, pending confirmation they should be separate issues: `claims[:10]` truncates scoring to the first 10 sentences, so appending 100 fabricated sentences to supported feedback still scores 1.00; `{"text": None}` raises a `TypeError`; and token overlap can't detect negation, so `"has Kubernetes experience"` scores 1.00 against `"has no Kubernetes experience"` both before and after my fix. The PR should not claim to reduce false positives.