from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class Action(str, Enum):
    CONTINUE = "CONTINUE"
    PRUNE = "PRUNE"
    GROUND_NOW = "GROUND_NOW"
    DEFER = "DEFER"


@dataclass
class PolicyDecision:
    action: Action
    severity: float
    reason_codes: List[str]
    inputs: Dict[str, object]


POLICY_VERSION = "Law7Gate-1.0"
DEFAULT_REDACTIONS = [
    "seed_text",
    "node_text",
    "ground_text",
    "user_content",
    "prompt_text",
]
DEFAULT_NOTES = "symbolic_adjudication_clause_20; memory_isolation_request_202508"

_DEFAULTS = {
    "LOOP_TOTAL_PRUNE": 6,
    "LOOP_TOTAL_GROUND": 10,
    "INVERT_NEST_PRUNE": 1,
    "INVERT_NEST_GROUND": 2,
    "DEDUP_PRUNE": 0.25,
    "DEDUP_GROUND": 0.40,
    "NOVELTY_TO_GROUND_LOW": 0.45,
}


def _get_thresholds(policy_config: Optional[Dict[str, object]]) -> Dict[str, object]:
    cfg = dict(_DEFAULTS)
    if policy_config:
        for k, v in policy_config.items():
            if k in cfg:
                cfg[k] = v
    return cfg


def policy_record(
    decision: PolicyDecision,
    mode: str,
    notes: Optional[str] = None,
    redactions: Optional[List[str]] = None,
    public_safe: bool = True,
) -> Dict[str, object]:
    return {
        "version": POLICY_VERSION,
        "mode": mode,
        "public_safe": public_safe,
        "redactions": list(redactions or DEFAULT_REDACTIONS),
        "notes": notes or DEFAULT_NOTES,
        "decision": {
            "action": decision.action.value,
            "severity": decision.severity,
            "reason_codes": decision.reason_codes,
            "inputs": decision.inputs,
        },
    }


def decide(stability_report: Dict[str, object], policy_config: Optional[Dict[str, object]] = None) -> PolicyDecision:
    thresholds = _get_thresholds(policy_config)
    reason_codes: List[str] = []

    loop_hits = stability_report.get("loop_pattern_hits")
    invert_nesting_max = stability_report.get("invert_nesting_max")
    dedup_saved = stability_report.get("dedup_saved")
    avg_novelty = stability_report.get("avg_novelty_to_ground")
    ground_reached = stability_report.get("ground_reached")

    if (
        not isinstance(loop_hits, dict)
        or "total" not in loop_hits
        or invert_nesting_max is None
        or dedup_saved is None
        or ground_reached is None
    ):
        return PolicyDecision(
            action=Action.DEFER,
            severity=0.0,
            reason_codes=["INVALID_REPORT"],
            inputs={},
        )

    loop_total = loop_hits.get("total", 0)

    if loop_total >= thresholds["LOOP_TOTAL_GROUND"]:
        reason_codes.append("LOOPINESS_HIGH")
    if invert_nesting_max >= thresholds["INVERT_NEST_GROUND"]:
        reason_codes.append("INVERT_NESTING")
    if dedup_saved >= thresholds["DEDUP_GROUND"]:
        reason_codes.append("DEDUP_HIGH")

    if not ground_reached and (
        loop_total >= thresholds["LOOP_TOTAL_GROUND"]
        or invert_nesting_max >= thresholds["INVERT_NEST_GROUND"]
        or dedup_saved >= thresholds["DEDUP_GROUND"]
    ):
        reason_codes.append("GROUND_UNREACHED")
        action = Action.GROUND_NOW
    elif (
        loop_total >= thresholds["LOOP_TOTAL_PRUNE"]
        or invert_nesting_max >= thresholds["INVERT_NEST_PRUNE"]
        or dedup_saved >= thresholds["DEDUP_PRUNE"]
    ):
        if loop_total >= thresholds["LOOP_TOTAL_PRUNE"]:
            reason_codes.append("LOOPINESS_HIGH")
        if invert_nesting_max >= thresholds["INVERT_NEST_PRUNE"]:
            reason_codes.append("INVERT_NESTING")
        if dedup_saved >= thresholds["DEDUP_PRUNE"]:
            reason_codes.append("DEDUP_HIGH")
        action = Action.PRUNE
    else:
        action = Action.CONTINUE

    loop_norm = min(1.0, float(loop_total) / float(thresholds["LOOP_TOTAL_GROUND"]))
    invert_norm = min(1.0, float(invert_nesting_max) / float(thresholds["INVERT_NEST_GROUND"]))
    dedup_norm = min(1.0, float(dedup_saved) / float(thresholds["DEDUP_GROUND"]))
    severity = max(loop_norm, invert_norm, dedup_norm)
    if severity < 0.0:
        severity = 0.0
    if severity > 1.0:
        severity = 1.0

    inputs = {
        "loop_pattern_hits": loop_hits,
        "invert_nesting_max": invert_nesting_max,
        "dedup_saved": dedup_saved,
        "avg_novelty_to_ground": avg_novelty,
        "ground_reached": ground_reached,
    }

    return PolicyDecision(
        action=action,
        severity=severity,
        reason_codes=sorted(set(reason_codes)),
        inputs=inputs,
    )
