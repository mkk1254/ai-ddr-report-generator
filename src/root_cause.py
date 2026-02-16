"""Root cause inference: LLM-based root_cause and evidence per observation."""

import json
import re
from pathlib import Path
from typing import Any

import yaml


def _build_summary(
    observations: list[dict[str, Any]],
    temperature_analysis: dict[str, Any] | None,
) -> str:
    """Build a text summary for the root-cause prompt."""
    lines = []
    for i, obs in enumerate(observations):
        area = obs.get("area", "Unknown")
        desc = obs.get("description", "")
        issue_type = obs.get("issue_type", "")
        cluster = obs.get("cluster_id", "")
        urgency = obs.get("urgency_score", "")
        line = f"[{i}] Area: {area}. Issue type: {issue_type}. Description: {desc}. Cluster: {cluster}. Urgency: {urgency}."
        lines.append(line)
    if temperature_analysis and temperature_analysis.get("readings"):
        lines.append("Temperature deltas (vs reference):")
        ref = temperature_analysis.get("reference_value")
        ref_u = temperature_analysis.get("reference_unit", "")
        lines.append(f"  Reference: {ref} {ref_u}")
        for r in temperature_analysis["readings"]:
            loc = r.get("location", "")
            delta = r.get("delta")
            anomaly = " (ANOMALY)" if r.get("anomaly") else ""
            lines.append(f"  - {loc}: delta {delta} {ref_u}{anomaly}")
    return "\n".join(lines)


def _load_prompt(summary: str) -> str:
    """Load and fill root_cause prompt."""
    prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
    with open(prompts_dir / "root_cause.yaml") as f:
        data = yaml.safe_load(f)
    return data["root_cause"].format(summary=summary)


def _parse_inferences(response: str) -> list[dict[str, Any]]:
    """Parse JSON inferences from LLM response."""
    text = response.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1)
    data = json.loads(text)
    return data.get("inferences", [])


def infer_root_causes(
    observations: list[dict[str, Any]],
    temperature_analysis: dict[str, Any] | None,
    model: str = "gemini-2.0-flash",
) -> list[dict[str, Any]]:
    """
    Call LLM to infer root_cause and evidence per observation; attach to each and return.
    """
    if not observations:
        return []

    from .llm import call_llm

    summary = _build_summary(observations, temperature_analysis)
    prompt = _load_prompt(summary)
    response = call_llm(prompt, model=model)

    try:
        inferences = _parse_inferences(response)
    except (json.JSONDecodeError, KeyError):
        inferences = []

    # Build index -> inference map
    by_index: dict[int, dict] = {inf.get("index", i): inf for i, inf in enumerate(inferences)}

    result = []
    for i, obs in enumerate(observations):
        obs = dict(obs)
        inf = by_index.get(i, {})
        rc = inf.get("root_cause") or "Insufficient diagnostic detail available to determine root cause. Further inspection recommended."
        if "not determinable" in (rc or "").lower() or rc == "Not determinable from data":
            rc = "Insufficient diagnostic detail available to determine root cause. Further inspection recommended."
        obs["root_cause"] = rc
        obs["evidence"] = inf.get("evidence") or []
        result.append(obs)
    return result
