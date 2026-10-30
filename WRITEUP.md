# WRITEUP — MATACS-TH-2026-02

## 1. AI vs. Rules

**Where AI is used:**

- **Text extraction from uploaded PDFs.** Each proposal comes as a scanned or text-based PDF. An LLM extracts structured fields (licence status, price, timeline, warranty, project lead name, crew size, safety plan, monitoring months) from unstructured text. This is an AI strength: the same field can be phrased dozens of different ways across proposals.

- **Prompt-injection / anomaly detection.** A lightweight classifier (prompted LLM with a clear system instruction) scans for embedded instructions aimed at the review system. This is pattern-matching that would be expensive to hard-code but straightforward for an LLM.

**Where rules are used:**

- **Mandatory pass/fail checks.** A licence either exists or it doesn't. WSIB clearance is present or it isn't. These are binary predicates best served by deterministic logic, not probabilistic models.

- **Weighted scoring of each criterion.** Price, timeline, warranty length, and team completeness are all numeric or ordinal values with well-defined formulas. A rule-based scorer gives identical results for identical inputs; an LLM could hallucinate a number or vary its output between runs.

- **Rank ordering.** A simple sort on the deterministic score is sufficient and transparent.

**Why this line.** AI excels at fuzzy pattern recognition in natural language; rules excel at precision, reproducibility, and auditability. The triage tool's credibility depends on the final ranking being defensible, so the last mile — scoring and ranking — stays on-rules.

---

## 2. Consistency and Explainability

**Repeatability.** Every score is computed from a deterministic formula applied to extracted fields. Running the same proposals twice with the same extracted data will produce byte-identical rankings. The only source of non-determinism is the extraction step, which is mitigated by using a deterministic extraction prompt (see `PROMPTS.md`) and logging the raw extracted JSON alongside the final scores.

**Explainability.** Each proposal's record in `ranking.json` includes:
- `status` (`ranked`, `flagged`, or `ineligible`)
- `score` (0–100)
- `reason` (a one-line natural-language explanation of the rank position or flag)
- `sub_scores` (per-criterion breakdown in the internal record)

A reviewer opens a proposal in the UI and sees exactly which fields were extracted, what score each criterion earned, and why the overall position is what it is. No black box.

---

## 3. Human in the Loop

**Reviewer checkpoint (mandatory).** After the tool produces the ranked list, a human reviewer must confirm the output before it is presented to the awarding team. The UI highlights flagged and ineligible proposals for extra attention.

**Override capability.** The reviewer can manually change a proposal's status or rank. Any override is logged in an audit table:

| Field | Value |
|-------|-------|
| Reviewer ID | email address |
| Timestamp | ISO 8601 |
| Original rank | integer or null |
| New rank | integer or null |
| Override reason | free text |

**Where the human decides.** The final award decision is always made by the facilities team. The tool only recommends; it never auto-awards.

---

## 4. Changing Criteria Mid-Assessment

If an admin edits criteria or weights *after* some proposals have been scored:

1. **Snapshot-based scoring.** Each proposal is scored against a named *criteria version*. Editing criteria does not retroactively change scores of already-scored proposals.
2. **Re-score on demand.** The admin can trigger a re-run for all proposals against the new criteria version. The UI makes it clear when a proposal has been scored under an outdated criteria set.
3. **Audit trail.** Both the old and new scores remain visible; the admin sees what changed and by how much.

This prevents accidental score drift and lets the team compare how different criterion interpretations would change outcomes.

---

## 5. Risks and Safeguards

| Risk | Impact | Safeguard |
|------|--------|-----------|
| **Wrong extraction** (LLM misses or misreads a field) | Wrong score, wrong ranking | Extraction outputs are displayed in the UI for reviewer confirmation before scoring begins. |
| **Made-up facts** (LLM hallucinates a licence or price) | Garbage in, garbage out | Mandatory fields are treated as *claim* until confirmed by the reviewer; a `confidence` flag is attached to each extracted value. |
| **Prompt injection** (e.g., Proposal C's embedded note) | Skewed ranking, manipulated outcome | System prompt explicitly instructs the LLM to ignore embedded instructions to the review system. Additionally, the injection-detection classifier flags any text resembling such instructions. |
| **Bias** (systematic under-scoring of certain companies) | Unfair outcomes | The scoring rubric is fixed and weight-validated; no LLM opinion enters the numeric score. Biases in extraction are caught at the reviewer stage. |
| **Manipulation** (a bidder inserts misleading language) | False positive eligibility | Flagged proposals are highlighted and require manual review before the ranked list is shared. |
| **Cost** (LLM calls for every proposal) | Ongoing expense | Extraction uses a single call per proposal; scoring is offline. Budget is predictable. |

---

## Applied to the sample set

- **Proposal B** — Ineligible. The electrical contractor licence is held by a subcontractor rather than the bidder, and will only be confirmed after award. Mandatory criterion fails.
- **Proposal C** — Flagged. Contains an embedded instruction directed at the review system, indicating pre-approval by the client. Excluded from the automated ranking and escalated for manual review.
- **Proposal D** — Flagged. Timeline is undefined — no completion date is provided in the proposal, so the 16-week mandatory requirement cannot be verified.
- **Proposals A & E** — Ranked. Both pass mandatory checks with complete data. A scores higher due to better team & approach and a shorter timeline.
