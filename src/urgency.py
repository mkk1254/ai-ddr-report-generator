"""Urgency scoring (1–5) and reason per observation based on severity, issue type, and thermal anomalies."""

from typing import Any

# Severity keywords -> base score boost (added to issue-type base)
SEVERITY_KEYWORDS = {
    "critical": 2,
    "severe": 2,
    "immediate": 2,
    "urgent": 1,
    "high": 1,
    "significant": 1,
    "moderate": 0,
    "low": -1,
    "minor": -1,
    "cosmetic": -1,
}

# Issue type -> base urgency (1–5). Plumbing + moisture = structural risk -> 4.
ISSUE_TYPE_SCORE: dict[str, int] = {
    "moisture": 4,
    "water": 4,
    "mold": 4,
    "plumbing": 4,
    "electrical": 4,
    "structural": 4,
    "safety": 5,
    "heat loss": 3,
    "insulation": 3,
    "anomaly": 3,
    "thermal": 3,
    "damage": 3,
    "crack": 2,
    "leak": 4,
    "defect": 2,
    "cosmetic": 1,
    "staining": 2,
    "wear": 2,
}


def _normalize(s: str) -> str:
    return (s or "").strip().lower()


def _observation_urgency_from_severity(obs: dict[str, Any], severity_mentions: list[str]) -> int:
    """Score 0–2 from severity keywords in description or global severity_mentions."""
    desc = _normalize(obs.get("description", ""))
    score = 0
    for kw, boost in SEVERITY_KEYWORDS.items():
        if kw in desc:
            score = max(score, boost)
    for s in severity_mentions:
        s = _normalize(s)
        for kw, boost in SEVERITY_KEYWORDS.items():
            if kw in s:
                score = max(score, boost)
    return min(2, max(0, score))


def _observation_urgency_from_issue_type(obs: dict[str, Any]) -> int:
    """Base urgency 1–5 from issue_type or description keywords."""
    it = _normalize(obs.get("issue_type", ""))
    desc = _normalize(obs.get("description", ""))[:100]
    text = f"{it} {desc}"
    for keyword, base in ISSUE_TYPE_SCORE.items():
        if keyword in text:
            return base
    return 2  # default middle


def _location_matches_reading(location: str, area: str) -> bool:
    """True if temperature reading location likely matches observation area."""
    loc = _normalize(location)
    a = _normalize(area)
    if not loc or not a:
        return False
    return a in loc or loc in a


def _thermal_anomaly_boost(
    obs: dict[str, Any],
    temperature_analysis: dict[str, Any] | None,
) -> int:
    """Return 0 or 1 if observation area has a thermal anomaly."""
    if not temperature_analysis:
        return 0
    readings = temperature_analysis.get("readings") or []
    area = _normalize(obs.get("area", ""))
    for r in readings:
        if r.get("anomaly") and _location_matches_reading(r.get("location", ""), area):
            return 1
    return 0


def score_urgency(
    observations: list[dict[str, Any]],
    severity_mentions: list[str],
    temperature_analysis: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Set urgency_score (1–5) and urgency_reason on each observation.
    Returns new list of observations with fields added (does not mutate in place).
    """
    result = []
    for obs in observations:
        obs = dict(obs)
        base = _observation_urgency_from_issue_type(obs)
        sev = _observation_urgency_from_severity(obs, severity_mentions or [])
        thermal = _thermal_anomaly_boost(obs, temperature_analysis)
        score = min(5, max(1, base + sev + thermal))
        reasons = []
        if sev > 0:
            reasons.append("severity keywords in report")
        if thermal > 0:
            reasons.append("thermal anomaly in area")
        if base >= 4:
            reasons.append("high-impact issue type")
        obs["urgency_score"] = score
        obs["urgency_reason"] = "; ".join(reasons) if reasons else "routine finding"
        result.append(obs)
    return result
