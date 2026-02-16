"""Deduplication, merge, and conflict handling for extracted data."""

from typing import Any


def normalize_area(area: str) -> str:
    """Normalize area string for comparison."""
    if not area or not str(area).strip():
        return "Area not specified"
    return str(area).strip().lower()


def observations_similar(obs1: dict, obs2: dict) -> bool:
    """Check if two observations are semantically similar (same area + same issue type)."""
    a1 = normalize_area(obs1.get("area", ""))
    a2 = normalize_area(obs2.get("area", ""))
    if a1 != a2:
        return False
    t1 = (obs1.get("issue_type") or obs1.get("description", ""))[:50].lower()
    t2 = (obs2.get("issue_type") or obs2.get("description", ""))[:50].lower()
    # Simple overlap check: same area and similar description/type
    if not t1 or not t2:
        return a1 == a2
    # Check for keyword overlap
    words1 = set(t1.split())
    words2 = set(t2.split())
    overlap = len(words1 & words2) / max(len(words1), len(words2)) if words1 and words2 else 0
    return overlap > 0.3 or t1 in t2 or t2 in t1


def _merge_observations(seen: dict, new: dict) -> None:
    """Merge new observation into seen in place. Combines description, issue_type, and source."""
    desc_seen = (seen.get("description") or "").strip()
    desc_new = (new.get("description") or "").strip()
    if desc_new and desc_new != desc_seen:
        if desc_seen:
            seen["description"] = f"{desc_seen}. Thermal/Inspection: {desc_new}"
        else:
            seen["description"] = desc_new
    it_seen = (seen.get("issue_type") or "").strip()
    it_new = (new.get("issue_type") or "").strip()
    if it_new:
        if it_seen and it_new.lower() != it_seen.lower():
            seen["issue_type"] = f"{it_seen}; {it_new}"
        elif not it_seen:
            seen["issue_type"] = it_new
    src_seen = (seen.get("source") or "").strip()
    src_new = (new.get("source") or "").strip()
    if src_new and src_new not in src_seen:
        seen["source"] = f"{src_seen}; {src_new}" if src_seen else src_new


def merge_extractions(
    inspection_data: dict[str, Any] | None,
    thermal_data: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """
    Merge extractions from inspection and thermal reports.
    Returns: (merged_data, conflicts, missing_list)
    """
    merged: dict[str, Any] = {
        "observations": [],
        "temperatures": [],
        "severity_mentions": [],
        "ambiguous": [],
        "missing": [],
    }
    conflicts: list[dict[str, Any]] = []
    seen_observations: list[dict] = []

    def add_observations(data: dict | None, source_label: str) -> None:
        if not data:
            return
        for obs in data.get("observations", []):
            obs = dict(obs)
            obs["source"] = source_label
            # Check for duplicates: merge similar non-conflicting, record conflicts
            merged_into = False
            for seen in seen_observations:
                if observations_similar(obs, seen):
                    if _has_conflict(obs, seen):
                        conflicts.append({
                            "type": "observation",
                            "observation_1": dict(seen),
                            "observation_2": obs,
                            "message": "Conflicting descriptions for same area — both recorded.",
                        })
                    else:
                        _merge_observations(seen, obs)
                    merged_into = True
                    break
            if not merged_into:
                seen_observations.append(obs)
                merged["observations"].append(obs)

    def _has_conflict(a: dict, b: dict) -> bool:
        """Check if two observations for same area have conflicting info."""
        desc_a = (a.get("description") or "").strip()
        desc_b = (b.get("description") or "").strip()
        if not desc_a or not desc_b:
            return False
        return desc_a != desc_b and len(set(desc_a.split()) & set(desc_b.split())) < 3

    add_observations(inspection_data, "Inspection Report")
    add_observations(thermal_data, "Thermal Report")

    # Merge temperatures (no dedup by location - different readings may exist)
    for data in (inspection_data, thermal_data):
        if data:
            for t in data.get("temperatures", []):
                merged["temperatures"].append(dict(t))

    # Merge severity mentions, check for conflicts
    severities: list[str] = []
    for data in (inspection_data, thermal_data):
        if data:
            for s in data.get("severity_mentions", []):
                s = str(s).strip()
                if s and s not in severities:
                    severities.append(s)
    merged["severity_mentions"] = severities

    # Merge ambiguous and missing
    for data in (inspection_data, thermal_data):
        if data:
            merged["ambiguous"].extend(data.get("ambiguous", []))
            merged["missing"].extend(data.get("missing", []))

    merged["ambiguous"] = list(dict.fromkeys(str(x) for x in merged["ambiguous"] if x))
    merged["missing"] = list(dict.fromkeys(str(x) for x in merged["missing"] if x))

    missing_list = merged["ambiguous"] + merged["missing"]
    return merged, conflicts, missing_list
