"""LLM extraction of structured data from inspection and thermal reports."""

import json
import re
from pathlib import Path
from typing import Any, Literal

import yaml

DocumentType = Literal["inspection", "thermal"]


def load_prompt(template_name: str, **kwargs: str) -> str:
    """Load and fill a prompt template from prompts/*.yaml."""
    prompts_dir = Path(__file__).parent.parent / "prompts"
    if template_name == "inspection_report":
        with open(prompts_dir / "extraction.yaml") as f:
            data = yaml.safe_load(f)
        template = data["inspection_report"]
    elif template_name == "thermal_report":
        with open(prompts_dir / "extraction.yaml") as f:
            data = yaml.safe_load(f)
        template = data["thermal_report"]
    else:
        raise ValueError(f"Unknown template: {template_name}")
    return template.format(**kwargs)


def call_llm(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """Call Gemini API."""
    from .llm import call_llm as _call_llm
    return _call_llm(prompt, model=model)


def extract_json_from_response(response: str) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    text = response.strip()
    # Remove markdown code blocks if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1)
    return json.loads(text)


def extract_from_document(
    content: str,
    document_type: DocumentType,
    model: str = "gemini-2.0-flash",
) -> dict[str, Any]:
    """Extract structured data from a document using the appropriate prompt."""
    template_name = "inspection_report" if document_type == "inspection" else "thermal_report"
    prompt = load_prompt(template_name, content=content)
    response = call_llm(prompt, model=model)

    try:
        data = extract_json_from_response(response)
    except json.JSONDecodeError:
        return {
            "observations": [],
            "temperatures": [],
            "severity_mentions": [],
            "ambiguous": [f"Could not parse LLM response as JSON: {response[:200]}..."],
            "missing": [],
        }

    # Ensure required keys exist
    result: dict[str, Any] = {
        "observations": data.get("observations", []),
        "temperatures": data.get("temperatures", []),
        "severity_mentions": data.get("severity_mentions", []),
        "ambiguous": data.get("ambiguous", []),
        "missing": data.get("missing", []),
    }

    # Add source to observations
    source = "inspection" if document_type == "inspection" else "thermal"
    for obs in result["observations"]:
        obs["source"] = obs.get("source", source)

    return result
