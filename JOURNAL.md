## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/152

**Issue title:** Faithfulness checker can never mark short claims as supported

**Tier:** [x] Tier 1  [ ] Tier 2  [ ] Tier 3

**Problem summary:**
The bug is in the faithfulness checker used by the RAG evaluator. Its current logic requires too much overlap between a claim and the supporting context, so short but fully grounded claims such as “Knows Python” are incorrectly scored as unsupported even when the context clearly matches them. This causes feedback that contains short, valid claims to receive a score of 0.0 instead of being treated as supported. A successful fix would make the checker handle short claims more gracefully while preserving correct behavior for unsupported or weakly supported statements.

**Branch name:** fix/152-faithfulness-checker-can-never-mark-short-claims-as-supported

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger