# MATACS-TH-2026-02 — AI Proposal Triage Design

**Candidate:** Huzaifa Asif  
**Reference:** MATACS-TH-2026-02  
**Time spent:** ~55 minutes  
**Submission date:** 2026-10-30

---

## Repository contents

| File / folder | Purpose |
|---------------|---------|
| `README.md` | This file |
| `WRITEUP.md` | Answers to the five assessment questions |
| `PROMPTS.md` | The AI prompt(s) used for extraction and scoring |
| `ranking.json` | Expected ranking of proposals A–E |
| `diagram/flow.png` | Process-flow diagram (upload → ranked output) |
| `prototype/score.py` | Scoring engine that produces `ranking.json` |
| `.env.example` | Template for API keys (none committed) |

---

## AI tools used

I used an AI assistant during the assessment for two things: generating the initial repository scaffolding (directory layout, `.gitignore`, `.env.example`) and drafting the prototype scoring script with a first-pass implementation of the rules. I then reviewed, corrected, and finalised every file myself — I verified the mandatory criteria logic, adjusted the scoring formulas to match the brief's weights, and rewrote the extraction prompts so they handle injection detection separately from field extraction. One specific correction: the first draft of the prompt system included all five proposal texts inline, which would have violated the brief's instruction not to reproduce the proposals. I removed that and restructured the prompts to accept the text as input only, without embedding it.

---

## Quick run

```bash
python prototype/score.py
```

This writes `ranking.json` with the final scores and reasons. No external API calls are made — all scoring is deterministic and rule-based, matching the design decision to keep critical evaluation on-rules, off-LLM.
