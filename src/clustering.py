"""Issue clustering: group observations by area + issue_type and assign cluster_id."""

from typing import Any


def _normalize(s: str) -> str:
    """Normalize for clustering key."""
    if not s or not str(s).strip():
        return "unspecified"
    return str(s).strip().lower()


def cluster_observations(observations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Group observations by normalized area + issue_type. Assign cluster_id and cluster_label to each.
    Returns (observations_with_cluster_ids, clusters_list).
    """
    if not observations:
        return [], []

    # key -> list of indices into observations
    key_to_indices: dict[str, list[int]] = {}
    for i, obs in enumerate(observations):
        area = _normalize(obs.get("area", ""))
        issue_type = _normalize(obs.get("issue_type") or obs.get("description", "")[:50])
        key = f"{area}|{issue_type}"
        if key not in key_to_indices:
            key_to_indices[key] = []
        key_to_indices[key].append(i)

    # Build cluster_id and cluster_label; assign to each observation
    clusters: list[dict[str, Any]] = []
    key_to_cluster_id: dict[str, str] = {}
    cluster_counter = 0
    for key, indices in key_to_indices.items():
        cluster_counter += 1
        cid = f"cluster_{cluster_counter}"
        key_to_cluster_id[key] = cid
        area_raw = observations[indices[0]].get("area", "Unknown") if indices else "Unknown"
        issue_raw = observations[indices[0]].get("issue_type") or "finding"
        label = f"{area_raw} – {issue_raw}"
        clusters.append({
            "cluster_id": cid,
            "label": label,
            "observation_indices": indices,
        })

    # Attach cluster_id and cluster_label to each observation
    result = [dict(obs) for obs in observations]
    for key, indices in key_to_indices.items():
        cid = key_to_cluster_id[key]
        label = next((c["label"] for c in clusters if c["cluster_id"] == cid), cid)
        for i in indices:
            result[i]["cluster_id"] = cid
            result[i]["cluster_label"] = label

    return result, clusters
