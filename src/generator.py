"""DDR generation from merged data."""

import json
from pathlib import Path
from typing import Any

import yaml


def load_generation_prompt(**kwargs: str) -> str:
    """Load and fill the DDR generation prompt."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    with open(prompts_dir / "generation.yaml") as f:
        data = yaml.safe_load(f)
    template = data["ddr_generation"]
    return template.format(**kwargs)


def call_llm(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Call Gemini API."""
    from .llm import call_llm as _call_llm
    return _call_llm(prompt, model=model)


def _format_merged_for_prompt(merged: dict[str, Any]) -> str:
    """Format merged data for inclusion in prompt (observations, temps, deltas, clusters, urgency, root cause, confidence)."""
    parts = []
    if merged.get("observations"):
        parts.append("Observations (with cluster, urgency, root cause, confidence):")
        for o in merged["observations"]:
            area = o.get("area", "Unknown")
            desc = o.get("description", "")
            src = o.get("source", "")
            cluster = o.get("cluster_id", "")
            cluster_label = o.get("cluster_label", "")
            urgency = o.get("urgency_score", "")
            urgency_reason = o.get("urgency_reason", "")
            root_cause = o.get("root_cause", "")
            evidence = o.get("evidence", [])
            confidence = o.get("confidence", "")
            confidence_reason = o.get("confidence_reason", "")
            line = f"  - [{area}] ({src}): {desc}"
            if cluster:
                line += f" | Cluster: {cluster_label or cluster}"
            if urgency:
                line += f" | Urgency: {urgency}/5"
            if urgency_reason:
                line += f" ({urgency_reason})"
            if root_cause:
                line += f" | Root cause: {root_cause}"
            if evidence:
                line += f" | Evidence: {'; '.join(evidence)}"
            if confidence != "":
                line += f" | Confidence: {confidence}"
            if confidence_reason:
                line += f" ({confidence_reason})"
            parts.append(line)
    if merged.get("temperatures"):
        parts.append("Temperature readings (raw):")
        for t in merged["temperatures"]:
            loc = t.get("location", "")
            val = t.get("value", "")
            unit = t.get("unit", "")
            parts.append(f"  - {loc}: {val} {unit}")
    if merged.get("temperature_analysis") and merged["temperature_analysis"].get("readings"):
        ta = merged["temperature_analysis"]
        ref = ta.get("reference_value")
        ref_u = ta.get("reference_unit", "")
        parts.append(f"Temperature deltas (reference: {ref} {ref_u}):")
        for r in ta["readings"]:
            loc = r.get("location", "")
            delta = r.get("delta")
            anomaly = " [ANOMALY]" if r.get("anomaly") else ""
            parts.append(f"  - {loc}: delta {delta} {ref_u}{anomaly}")
    if merged.get("clusters"):
        parts.append("Issue clusters:")
        for c in merged["clusters"]:
            parts.append(f"  - {c.get('cluster_id', '')}: {c.get('label', '')}")
    if merged.get("severity_mentions"):
        parts.append("Severity mentions: " + ", ".join(merged["severity_mentions"]))
    return "\n".join(parts) if parts else "No data extracted."


def _format_conflicts_for_prompt(conflicts: list[dict[str, Any]]) -> str:
    """Format conflicts for inclusion in prompt."""
    if not conflicts:
        return "None"
    parts = []
    for c in conflicts:
        msg = c.get("message", "Conflict")
        parts.append(f"- {msg}")
        for k in ("observation_1", "observation_2"):
            if k in c:
                parts.append(f"  {k}: {json.dumps(c[k], default=str)}")
    return "\n".join(parts)


def generate_ddr(
    merged_data: dict[str, Any],
    conflicts: list[dict[str, Any]],
    missing_list: list[str],
    model: str = "gemini-2.0-flash",
) -> str:
    """Generate the final DDR report in Markdown."""
    merged_str = _format_merged_for_prompt(merged_data)
    conflicts_str = _format_conflicts_for_prompt(conflicts)
    missing_str = "\n".join(f"- {m}" for m in missing_list) if missing_list else "None"

    prompt = load_generation_prompt(
        merged_data=merged_str,
        conflicts=conflicts_str,
        missing=missing_str,
    )
    return call_llm(prompt, model=model)


def format_output(report_md: str, output_format: str) -> str:
    """Convert report to requested format (markdown, json, html)."""
    if output_format == "markdown":
        return report_md
    if output_format == "json":
        # Parse markdown sections into JSON-like structure
        sections = {}
        current = None
        buf = []
        for line in report_md.splitlines():
            if line.startswith("## "):
                if current:
                    sections[current] = "\n".join(buf).strip()
                current = line[3:].strip()
                buf = []
            else:
                buf.append(line)
        if current:
            sections[current] = "\n".join(buf).strip()
        return json.dumps(sections, indent=2)
    if output_format == "html":
        import html
        lines = []
        for line in report_md.splitlines():
            if line.startswith("## "):
                lines.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
            elif line.startswith("- "):
                lines.append(f"<li>{html.escape(line[2:])}</li>")
            elif line.strip():
                lines.append(f"<p>{html.escape(line)}</p>")
            else:
                lines.append("<br/>")
        body = "\n".join(lines)
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Detailed Diagnostic Report</title></head>
<body>{body}</body>
</html>"""
    raise ValueError(f"Unsupported format: {output_format}")
