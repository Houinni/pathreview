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

## Week 9 — Solution building & PR submission

### Check-in 1 (mid-week)

**Current progress:**
All of PLAN.md Tier 1 is implemented, one commit per sub-task, plus one sub-task the plan did not originally contain.

- Step 1 — shared `_tokenize` helper (`777b5b2`). Applied identically to claim and context, stripping *edge* punctuation only, so `Python.` normalizes to `python` while `C++`, `C#`, `Node.js`, `CI/CD` and `3.11` survive intact. Stop words hoisted to a module constant.
- Step 2 — claim filter changed from character count to word count (`3328f5f`). `len(s) > 10` selected on how long a word is spelled: it dropped `"Uses Rust"` (9 chars) but kept `"Great at Go"` (11).
- Step 3 (**added during implementation**) — proportional support threshold (`068ae6e`). PLAN.md Risk 1 deferred this because "no maintainer test demands it". That premise was wrong: `test_multiple_claims_varying_support` expects two of three claims supported, and both supported claims overlap the context on exactly one token, so `>= 2` leaves it red no matter how good the tokenizer is. My 10-case table had mislabelled it. The window of ratios satisfying every test is `(0.17, 0.33]`; I took `0.3` and recorded the window in a comment and a test. PLAN.md Risk 1 has been rewritten to show the reversal rather than quietly edited.
- Step 4 — extraction logging (`f50f903`). `claims_count` was logged *after* the `claims[:10]` slice, so it saturated at 10 and hid both discarded fragments and the unscored tail.
- Step 5 — verification against the maintainer's tests, not just my own (below).

One test I predicted would go green cannot (`8eaf645`). `test_partial_support_returns_middle_score` asserts `0.2 < score < 0.8` on a single-sentence fixture — `check()` scores exactly one claim there, so the result is 0.0 or 1.0 and can never land inside that interval. Partial credit would not rescue it either: the claim overlaps on 1 of 6 meaningful tokens, so a ratio-valued score is 0.17. That is a test bug independent of #152, so I marked it `xfail` with the arithmetic in the reason rather than rewrite a maintainer's assertion to make my own PR green.

Result: 5 previously failing tests now pass. Still failing is `test_none_context_chunk_text` — a genuine `TypeError` on `{"text": None}`, scoped out in PLAN.md as a separate robustness bug.

**Next steps:**
Open the draft PR, request peer review in Slack, address anything I agree with, mark ready for review, then submit the branch URL via the portal.

**Blockers:**
None blocking. Two things I want a reviewer's eye on, both flagged in the PR description: whether `0.3` is the ratio the maintainer actually wants (narrow window, small suite), and whether marking their test `xfail` was mine to do at all.

---

### Check-in 2 (end of week)

**PR link:** <!-- FILL IN: link to the submitted (not draft) PR -->

**Branch:** `fix/152-faithfulness-checker-can-never-mark-short-claims-as-supported`

**What you built:**
A fix for three independent causes of the same symptom in `rag/evaluator/faithfulness_checker.py`: punctuation-blind tokenization, an absolute overlap threshold that forced short claims to match 100% of themselves, and a character-count claim filter that silently discarded short claims and fell back to the 0.5 neutral default. Claim and context now pass through one shared tokenizer that strips edge punctuation while preserving interior punctuation, support scales with claim length instead of using a fixed token count, and claims are selected by word count. `"Knows Python"` against `"The candidate knows Python."` goes from 0.0 to 1.0; the public `check()` signature, return type and range are unchanged.

**Tests added or updated:**
`tests/unit/test_faithfulness_short_claims.py` — the Week 8 regression cases proved the bug was fixed but left the fix's own machinery unpinned, so `fb8cc3f` adds four classes: `TestTokenizer` (edge vs. interior punctuation, `C++` not colliding with `C#`, unicode quotes and dashes, the claim/context symmetry invariant), `TestProportionalThreshold` (one of two tokens is enough, one of six is not, and a guard that fails with an explanation if `_SUPPORT_RATIO` drifts outside the measured window), `TestClaimExtraction` (short technology claims survive, single-word fragments do not, the cap holds) and `TestExtractionLogging` (dropped and unscored counts, and that the 0.5 neutral default is distinguishable from a real 0.5 score). Also `tests/unit/test_faithfulness_checker.py` — one `xfail` marker on the unsatisfiable test described in Check-in 1; no maintainer assertion was rewritten.

**Self-review confirmation:** [x] make check passes  [x] make test-unit passes

Checked in the sense the assignment defines for a codebase with pre-existing failures — **these changes introduce no new failures**. This repository does not pass either command on an unmodified tree. Measured on the baseline commit `84dd3b8` and again on this branch:

| Command | Baseline `84dd3b8` | This branch | Delta |
|---|---|---|---|
| `ruff check .` | 182 errors | 181 errors | −1 (fixed an `I001` in the file I touched) |
| `black --check .` | 52 of 112 files | 52 of 112 files | unchanged |
| `mypy api/ core/ ingestion/ rag/ agent/ safety/` | identical output | identical output | unchanged; `faithfulness_checker.py` itself is clean |
| `pytest tests/unit -m unit` | 60 failed, 342 passed, 31 errors | 55 failed, 392 passed, 31 errors | −5 failures, +50 passes |

The −5 failures are the #152 bug itself. The +50 passes are the parametrized cases in `fb8cc3f`. The 31 collection errors are identical on both sides.

Two notes on method, so the numbers can be reproduced:

- I did not run `make format`. It executes `black .`, which rewrites in place rather than checking, and would reformat 52 files repo-wide — burying a ~90-line fix in thousands of lines of unrelated reflow. `black --check` is reported instead. Both files I touched were already in the failing set beforehand and still are, so this is not a regression.
- The suite was measured on Python 3.10 with a `datetime.UTC` shim, since three test modules (`test_rate_limiter`, `test_review_service`, `test_security`) need 3.11 to import. The shim was applied to disposable copies of *both* commits, never to the branch, so the comparison is like-for-like.

**Draft PR feedback received from:** <!-- FILL IN: name or Slack handle, or "none" -->
