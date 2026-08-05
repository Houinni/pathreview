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

## Week 9 — Check-in 1 (Wednesday)

**Commits:** `777b5b2` tokenizer · `3328f5f` claim filter · `068ae6e` threshold · `8eaf645` xfail · `f50f903` logging · `d798e96` plan corrections · `fb8cc3f` tests

**Status:** implementation complete, tests written, self-review done. Remaining: open the draft PR, get peer review, submit.

**What I built:**
Four commits, one per root cause plus one for observability. A shared `_tokenize` helper applied identically to claim and context, stripping *edge* punctuation only so `C++`, `C#`, `Node.js`, `CI/CD` and `3.11` survive intact while `Python.` normalizes to `python`. The claim filter moved from `len(s) > 10` characters to `>= 2` words. The overlap threshold moved from an absolute `>= 2` to a proportional `0.3` of claim tokens. Extraction now logs `extracted_count` / `dropped_count` / `unscored_count` before truncation, so the `claims[:10]` slice is no longer invisible.

**Where I departed from the plan, and why:**
The plan deferred the threshold change on the grounds that no maintainer test demanded it. Working through the failures, that premise was wrong. `test_multiple_claims_varying_support` expects two of three claims supported, and both supported claims (`"Python expert"`, `"Skilled with Docker"`) overlap the context on exactly one token — under `>= 2` it stays red however good the tokenizer is. My 10-case table had mislabelled it. The real choice was therefore not "adopt my opinion or wait for the maintainer" but "satisfy a maintainer test or ship a red one". Re-measured, the window of ratios satisfying every test is `(0.17, 0.33]`; `0.3` sits inside it with margin at both ends, so I adopted it and dropped the two `xfail` markers that were waiting on this exact decision. The ratio is a named constant with the window recorded in a comment, because a narrow window derived from a small suite is still a small-sample number.

**A test that cannot pass:**
The plan also predicted `test_partial_support_returns_middle_score` would go green. It cannot. Its fixture is a single sentence, so `check()` scores one claim and returns exactly 0.0 or 1.0 — never a value strictly inside the asserted `(0.2, 0.8)`. Partial credit wouldn't save it either; the claim overlaps on 1 of 6 meaningful tokens, so a ratio-valued score is 0.17. That's a test bug independent of #152, so I marked it `xfail` with the arithmetic in the reason rather than rewriting a maintainer's assertion to make my own PR look green.

**Verification:** `test_faithfulness_checker.py` and `test_faithfulness_short_claims.py` are green apart from `test_none_context_chunk_text`, the `{"text": None}` `TypeError` the plan scoped out. Every edge case in the plan's regression table still holds — empty inputs, missing `text` key, punctuation-only and stop-word-only claims, determinism. `test_relevance_scorer.py::test_query_with_partial_overlap` also fails, but it fails identically at `84dd3b8` and lives in a file I never touched.

**Tests added:** `fb8cc3f` adds four classes to `test_faithfulness_short_claims.py`. The Week 8 regression cases proved the bug was fixed but left the fix's own machinery unpinned. `TestTokenizer` covers edge vs. interior punctuation (including that `C++` and `C#` do not collide), unicode quotes and dashes, and the symmetry invariant. `TestProportionalThreshold` covers 1-of-2 supported, 1-of-6 not, and guards `_SUPPORT_RATIO` against drifting outside `(0.17, 0.33]` so a bad value fails with an explanation instead of as a bare assert in a maintainer test. `TestClaimExtraction` and `TestExtractionLogging` cover the word-count filter and the new counters.

**Blockers or open questions:**
Nothing blocking. Two things I want a reviewer's eye on: whether `0.3` is the ratio the maintainer wants (the window is narrow and the suite it was derived from is small), and whether `test_partial_support_returns_middle_score` should be `xfail`ed by me at all or left red for the maintainer to fix.

**Still open:** the three negation cases still score 1.00 (Risk 2) — the PR must not claim to reduce false positives. `claims[:10]`, `{"text": None}` and the threshold confirmation all want follow-up issues.

## Week 9 — Check-in 2 (Sunday, submission)

**PR link:** <!-- FILL IN after opening the PR -->

**Peer/mentor review:** <!-- FILL IN: who reviewed, and what you changed in response -->

**Self-review:**

- [x] Branch name follows `<type>/<issue-number>-<short-description>` — `fix/152-faithfulness-checker-can-never-mark-short-claims-as-supported`
- [x] Commit messages follow Conventional Commits with a valid scope — all seven are `fix|test|docs(rag):` with a `Refs #152` footer
- [x] Docstrings are Google-style on everything I added (`_tokenize`, and every new test class)
- [x] PR template filled in completely
- [x] New/updated tests cover the changes — `fb8cc3f`
- [x] `make lint` — introduces no new failures (see baseline below)
- [x] `make typecheck` — introduces no new failures
- [x] `make test-unit` — introduces no new failures; 5 previously failing tests now pass

**Pre-existing failures (measured before I started, at `84dd3b8`):**

This repo does not pass `make check` or `make test-unit` on an unmodified tree. Measured on the baseline commit and again on my final branch:

| Command | Baseline `84dd3b8` | My branch | Delta |
|---|---|---|---|
| `ruff check .` | 182 errors | 181 errors | −1 (fixed an `I001` in the file I touched) |
| `black --check .` | 52 of 112 files | 52 of 112 files | unchanged |
| `pytest tests/unit -m unit` | 40 failed, 299 passed, 31 errors | 35 failed, 349 passed, 31 errors | −5 failures, +50 passes |

My changes introduce no new failures in any of the three. The 5 newly passing tests are the #152 bug itself; the +50 passes are the parametrized cases in `fb8cc3f`.

Two caveats on how these were measured, so the numbers can be reproduced:

- The 31 errors are collection errors in `test_semantic_chunker.py` and `test_structural_chunker.py`, identical before and after.
- `test_rate_limiter.py`, `test_review_service.py` and `test_security.py` are excluded from both columns — they need Python 3.11 (`datetime.UTC`) and the environment I measured in runs 3.10. They are excluded from *both* sides, so the comparison is like-for-like, but I have not run them.

**Notes:** I did not run `make format`. It executes `black .`, which rewrites in place rather than checking, and would reformat 52 files across the repo — burying a ~90-line fix in several thousand lines of unrelated reflow. `black --check` is reported above instead. The two files I touched were already in the failing set before my changes and still are, so this is not a regression.