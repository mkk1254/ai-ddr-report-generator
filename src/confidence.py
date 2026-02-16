"""Confidence score (0–1) per observation: heuristic from source agreement, conflicts, and content."""

from typing import Any


def _sources(obs: dict[str, Any]) -> set[str]:
    """Extract source labels from observation (may be 'Inspection Report; Thermal Report')."""
    src = (obs.get("source") or "").strip()
    if not src:
        return set()
    return {s.strip() for s in src.split(";") if s.strip()}


def _content_based_confidence(obs: dict[str, Any]) -> tuple[float, str] | None:
    """
    Return (confidence, reason) when observation content suggests a specific level;
    otherwise None so caller uses source-based logic.
    """
    area = (obs.get("area") or "").strip().lower()
    desc = (obs.get("description") or "").strip().lower()
    it = (obs.get("issue_type") or "").strip().lower()
    text = f"{area} {desc} {it}"

    # Clear visible + repeated issues -> 0.85
    if ("visible" in text or "repeated" in text) and ("damp" in text or "moisture" in text or "leak" in text or "damage" in text):
        return (0.85, "Clear visible or repeated finding")
    # Skirting dampness -> 0.85
    if "skirting" in text and ("damp" in text or "dampness" in text or "moisture" in text):
        return (0.85, "Skirting-level dampness clearly reported")
    # Parking ceiling leakage -> 0.85
    if "parking" in text and "ceiling" in text and ("leak" in text or "leakage" in text or "water" in text):
        return (0.85, "Parking ceiling leakage clearly reported")

    # Moderate evidence -> 0.65
    if "moderate" in text and ("evidence" in text or "sign" in text or "damage" in text):
        return (0.65, "Moderate evidence")
    # Tile hollowness -> 0.65
    if "tile" in text and ("hollow" in text or "hollowness" in text):
        return (0.65, "Tile hollowness noted")

    # Unclear / vague -> 0.45
    if "unclear" in text or "vague" in text:
        return (0.45, "Unclear or vague finding")
    # Vague "Damage – [room]" (e.g. "Damage – Master bedroom bathroom") -> 0.45
    if ("damage" in text and not any(x in text for x in ["moisture", "leak", "crack", "structural", "water"])) and (
        "bedroom" in text or "bathroom" in text or "room" in text or "ceiling" in text or "wall" in text
    ):
        return (0.45, "Insufficient diagnostic detail for generic damage")

    return None


def score_confidence(
    observations: list[dict[str, Any]],
    conflicts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Set confidence (0–1) and confidence_reason on each observation.
    Uses content-based overrides (clear/repeated/skirting/leakage -> 0.85; moderate/tile -> 0.65; vague/generic damage -> 0.45),
    then source-based: conflict -> 0.5, two sources -> 0.9, single -> 0.7.
    """
    conflict_obs: set[tuple[str, str]] = set()
    if conflicts:
        for c in conflicts:
            for key in ("observation_1", "observation_2"):
                o = c.get(key)
                if isinstance(o, dict):
                    area = (o.get("area") or "").strip()
                    desc = (o.get("description") or "").strip()[:80]
                    conflict_obs.add((area, desc))

    result = []
    for obs in observations:
        obs = dict(obs)
        area = (obs.get("area") or "").strip()
        desc = (obs.get("description") or "").strip()[:80]
        in_conflict = (area, desc) in conflict_obs

        content_override = _content_based_confidence(obs)
        if content_override is not None:
            confidence, reason = content_override
        elif in_conflict:
            confidence = 0.5
            reason = "Conflicting reports for this finding"
        else:
            sources = _sources(obs)
            if len(sources) >= 2:
                confidence = 0.9
                reason = "Multiple sources agree (inspection and thermal)"
            else:
                confidence = 0.7
                reason = "Single source"

        obs["confidence"] = round(confidence, 2)
        obs["confidence_reason"] = reason
        result.append(obs)
    return result
