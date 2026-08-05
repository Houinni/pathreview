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

Checked in the sense the assignment defines for a codebase with pre-existing failures — **these changes introduce no new failures**. This repository passes neither command on an unmodified tree. Both columns below were measured in the same environment (project venv, Python 3.12), by checking out `84dd3b8` detached, running each command, then returning to the branch:

| Command | Baseline `84dd3b8` | This branch | Delta |
|---|---|---|---|
| `make lint` | 182 errors | 181 errors | −1 (an `I001` in the file I touched) |
| `make typecheck` | aborts in numpy's bundled stubs | aborts in numpy's bundled stubs | unchanged |
| `make test-unit` | 55 failed, 378 passed, 2 xfailed | 50 failed, 428 passed, 1 xfailed | −5 failures, +50 passes |

The −5 failures are the #152 bug itself. The +50 passes are the parametrized cases added in `fb8cc3f`. The xfail count moves 2 → 1 because this branch *removes* two markers — the contested threshold tests now pass for real — and adds one, on the unsatisfiable test described in Check-in 1.

Three notes on method, so the numbers can be reproduced:

- **`make typecheck` never reaches this code.** It fails inside `.venv/.../numpy/__init__.pyi` with *"Type statement is only supported in Python 3.12 and greater"* — the pinned mypy is too old to parse numpy's stubs — and reports "errors prevented further checking". It aborts identically before and after. Run directly against the changed file, `mypy rag/evaluator/faithfulness_checker.py --ignore-missing-imports --follow-imports=skip` reports **Success: no issues found**.
- **`make check` never reaches `make format`.** `check` depends on `lint` first, and make halts on the first failing prerequisite, so `black .` does not run. This matters because `format` rewrites in place rather than checking: it would reformat 52 files repo-wide, burying a ~90-line fix in thousands of lines of unrelated reflow. Both files I touched were already failing `black --check` at baseline and still are — not a regression.
- The one remaining ruff error inside the files I touched is a pre-existing `F841` in the maintainer's `test_common_words_filtered_in_overlap`, which calls `_is_supported` and never asserts on the result. It is present at `84dd3b8` and is the same category of test bug as the `xfail`ed one — left alone deliberately rather than widening this PR.

**Draft PR feedback received from:** <!-- FILL IN: name or Slack handle, or "none" -->
