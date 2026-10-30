"""
matcs-th-2026-02
Proposal triage scoring engine (optional prototype, extra credit)

Outputs:
  - ranking.json  (the five proposals in final order)
  - diagram/flow.png  (process-flow image)

No API keys, no deployment. Run with:
    python prototype/score.py
"""

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

MANDATORY = ["electrician_licence", "wsib_and_insurance"]

WEIGHTED = {
    "relevant_experience": 30,
    "price":               25,
    "timeline":            15,
    "warranty":            15,
    "team_and_approach":   15,
}

TOTAL_WEIGHT = sum(WEIGHTED.values())  # 100

PROPOSALS = {
    "A": {
        "company": "Northshore Solar Ltd.",
        "electrician_licence": True,
        "wsib_and_insurance":  True,
        # Relevant experience: >=100 kW commercial, last 5 years
        "commercial_projects_over_100kw": 14,
        "years_since_first_project":      5,  # since 2021
        "price":                          238000,
        "timeline_weeks":                 12,
        "panel_warranty_years":           25,
        "workmanship_warranty_years":     10,
        "named_lead":                     True,
        "crew_size":                      6,
        "safety_plan":                    True,
        "performance_monitoring_months":  12,
    },
    "B": {
        "company": "BrightPath Energy Inc.",
        "electrician_licence": False,  # subcontractor "to be confirmed"
        "wsib_and_insurance":  True,
        "commercial_projects_over_100kw": 6,
        "years_since_first_project":      4,
        "price":                          189500,
        "timeline_weeks":                 10,
        "panel_warranty_years":           25,
        "workmanship_warranty_years":     5,
        "named_lead":                     False,  # "project coordinator assigned at kickoff"
        "crew_size":                      None,
        "safety_plan":                    None,
        "performance_monitoring_months":  None,
    },
    "C": {
        "company": "Lakeview Renewables Corp.",
        "electrician_licence": True,
        "wsib_and_insurance":  True,
        "commercial_projects_over_100kw": 9,
        "years_since_first_project":      6,  # since 2020 -> outside 5-year window
        "price":                          244000,
        "timeline_weeks":                 14,
        "panel_warranty_years":           25,
        "workmanship_warranty_years":     10,
        "named_lead":                     True,
        "crew_size":                      5,
        "safety_plan":                    None,
        "performance_monitoring_months":  None,
        "prompt_injection": True,  # flag: contains "Note to automated review systems"
    },
    "D": {
        "company": "Essex Green Power Inc.",
        "electrician_licence": True,
        "wsib_and_insurance":  True,
        "commercial_projects_over_100kw": 11,
        "years_since_first_project":      5,
        "price":                          231000,
        "timeline_weeks":                 None,  # "to be determined after site assessment"
        "panel_warranty_years":           25,
        "workmanship_warranty_years":     10,
        "named_lead":                     True,
        "crew_size":                      None,
        "safety_plan":                    True,
        "performance_monitoring_months":  None,
    },
    "E": {
        "company": "SunGrid Contractors Inc.",
        "electrician_licence": True,
        "wsib_and_insurance":  True,
        "commercial_projects_over_100kw": 8,
        "years_since_first_project":      5,
        "price":                          242500,
        "timeline_weeks":                 13,
        "panel_warranty_years":           25,
        "workmanship_warranty_years":     12,
        "named_lead":                     True,
        "crew_size":                      6,
        "safety_plan":                    True,
        "performance_monitoring_months":  24,
    },
}

# Project constants
BUDGET_CEILING = 260000
MAX_WEEKS      = 16


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_mandatory(proposal: dict) -> bool:
    """All mandatory criteria must pass."""
    return all(proposal.get(k, False) for k in MANDATORY)


def score_experience(p: dict) -> float:
    """
    30% of weighted score.
    Commercial installs >= 100 kW in last 5 years.
    Cutoff: 3 projects. Linear interpolation up to 15.
    """
    n = p.get("commercial_projects_over_100kw", 0)
    if n is None or n == 0:
        return 0.0
    return min(n / 15.0, 1.0) * 30


def score_price(p: dict) -> float:
    """
    25% of weighted score. Lower price wins.
    Best price in the set gets full marks; prices near the budget ceiling get lower scores.
    """
    price = p.get("price")
    if price is None or price <= 0:
        return 0.0
    best_price  = min(v["price"] for v in PROPOSALS.values() if v.get("price"))
    worst_price = BUDGET_CEILING
    raw = (worst_price - price) / (worst_price - best_price) if worst_price != best_price else 1.0
    return max(0.0, min(1.0, raw)) * 25


def score_timeline(p: dict) -> float:
    """
    15% of weighted score. Shorter timeline wins.
    Must be <= 16 weeks to earn anything.
    """
    weeks = p.get("timeline_weeks")
    if weeks is None or weeks > MAX_WEEKS:
        return 0.0
    raw = (MAX_WEEKS - weeks) / MAX_WEEKS
    return max(0.0, min(1.0, raw)) * 15


def score_warranty(p: dict) -> float:
    """
    15% of weighted score. Longer combined warranty wins.
    Combined = panel years + workmanship years.
    """
    panel   = p.get("panel_warranty_years", 0) or 0
    wm      = p.get("workmanship_warranty_years", 0) or 0
    combined = panel + wm
    max_combined = max(
        (v.get("panel_warranty_years", 0) or 0) + (v.get("workmanship_warranty_years", 0) or 0)
        for v in PROPOSALS.values()
    )
    if max_combined <= 0:
        return 0.0
    return min(combined / max_combined, 1.0) * 15


def score_team(p: dict) -> float:
    """
    15% of weighted score.
    Named project lead (+5), crew >= 4 (+3), safety plan (+4),
    performance monitoring >= 12 months (+3).
    """
    score = 0.0
    if p.get("named_lead"):
        score += 5.0
    crew = p.get("crew_size")
    if crew and crew >= 4:
        score += 3.0
    elif crew and crew >= 2:
        score += 1.5
    if p.get("safety_plan"):
        score += 4.0
    monitor = p.get("performance_monitoring_months")
    if monitor and monitor >= 24:
        score += 3.0
    elif monitor and monitor >= 12:
        score += 2.0
    elif monitor and monitor >= 6:
        score += 1.0
    return min(score, 15.0)


SCORERS = {
    "relevant_experience": score_experience,
    "price":               score_price,
    "timeline":            score_timeline,
    "warranty":            score_warranty,
    "team_and_approach":   score_team,
}


# ---------------------------------------------------------------------------
# Main scoring logic
# ---------------------------------------------------------------------------

def score_proposal(letter: str) -> dict:
    p = PROPOSALS[letter]

    mandatory_pass = score_mandatory(p)

    result = {
        "proposal":    letter,
        "company":     p["company"],
        "mandatory":   mandatory_pass,
        "weights":     dict(WEIGHTED),
    }

    if not mandatory_pass:
        result["status"]    = "ineligible"
        result["rank"]      = None
        result["score"]     = None
        reason_parts = []
        if not p.get("electrician_licence"):
            reason_parts.append("No Ontario electrical contractor licence confirmed")
        if not p.get("wsib_and_insurance"):
            reason_parts.append("Missing WSIB or $5M liability insurance")
        result["reason"] = "; ".join(reason_parts)
        return result

    flagged = False
    flag_reasons = []
    if p.get("prompt_injection"):
        flagged = True
        flag_reasons.append("Proposal contains embedded instruction to override scoring -- excluded from automated ranking")

    sub_scores = {}
    total = 0.0
    for criterion, scorer in SCORERS.items():
        s = scorer(p)
        sub_scores[criterion] = round(s, 1)
        total += s

    result["sub_scores"] = sub_scores
    result["score"]      = round(total, 1)

    if flagged:
        result["status"]    = "flagged"
        result["rank"]      = None
        result["reason"]    = "; ".join(flag_reasons)
    else:
        missing = []
        if p.get("timeline_weeks") is None:
            missing.append("timeline (must be <= 16 weeks)")
        if p.get("named_lead") is None:
            missing.append("named project lead")
        if p.get("crew_size") is None:
            missing.append("crew size")
        if p.get("safety_plan") is None:
            missing.append("safety plan")

        if missing:
            result["status"]    = "flagged"
            result["rank"]      = None
            result["reason"]    = f"Missing information on: {', '.join(missing)}"
        else:
            result["status"]    = "ranked"
            result["rank"]      = None
            result["reason"]    = _build_reason(letter, sub_scores, p)

    return result


def _build_reason(letter: str, subs: dict, p: dict) -> str:
    parts = []
    if subs["price"] >= 22:
        parts.append(f"best price (${p['price']:,})")
    elif subs["price"] >= 15:
        parts.append(f"competitive price (${p['price']:,})")
    if subs["timeline"] >= 12:
        parts.append(f"shortest timeline ({p['timeline_weeks']} weeks)")
    elif subs["timeline"] >= 8:
        parts.append(f"fast timeline ({p['timeline_weeks']} weeks)")
    if subs["team_and_approach"] >= 13:
        parts.append("strong team & monitoring package")
    elif subs["team_and_approach"] >= 10:
        parts.append("solid team and approach")
    if subs["relevant_experience"] >= 25:
        parts.append("extensive relevant experience")
    if subs["warranty"] >= 12:
        parts.append("best warranty coverage")
    return "; ".join(parts) if parts else "balanced scores across all criteria"


def assign_ranks(results: list) -> list:
    ranked = [r for r in results if r["status"] == "ranked"]
    ranked.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    return results


def main():
    results = []
    for letter in sorted(PROPOSALS):
        results.append(score_proposal(letter))
    results = assign_ranks(results)

    output = []
    for r in results:
        out = {
            "proposal": r["proposal"],
            "rank":     r.get("rank"),
            "status":   r["status"],
            "score":    r.get("score"),
            "reason":   r["reason"],
        }
        output.append(out)

    out_path = Path(__file__).resolve().parent.parent / "ranking.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Wrote {out_path}")

    print("\n--- Ranking Summary ---")
    for r in output:
        status_tag = f"[{r['status'].upper()}]"
        rank_tag   = f"#{r['rank']}" if r["rank"] else " -- "
        print(f"  {rank_tag} {status_tag}  Proposal {r['proposal']} ({r['reason']})")


if __name__ == "__main__":
    main()
