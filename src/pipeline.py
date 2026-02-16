"""Orchestrates the full DDR generation pipeline."""

from pathlib import Path
from typing import Literal

from .clustering import cluster_observations
from .confidence import score_confidence
from .extractor import extract_from_document
from .generator import format_output, generate_ddr
from .merger import merge_extractions
from .parser import parse_document
from .root_cause import infer_root_causes
from .temperature_analysis import compute_temperature_analysis
from .urgency import score_urgency


def run_pipeline(
    inspection_path: Path | None = None,
    thermal_path: Path | None = None,
    output_path: Path | None = None,
    output_format: Literal["markdown", "json", "html"] = "markdown",
    model: str = "gemini-2.0-flash",
    verbose: bool = False,
) -> str:
    """Run the full pipeline and return the generated report."""
    inspection_text = ""
    thermal_text = ""

    if inspection_path:
        try:
            inspection_text = parse_document(Path(inspection_path))
        except Exception as e:
            if verbose:
                print(f"Warning: Could not parse inspection document: {e}")
            inspection_text = ""

    if thermal_path:
        try:
            thermal_text = parse_document(Path(thermal_path))
        except Exception as e:
            if verbose:
                print(f"Warning: Could not parse thermal document: {e}")
            thermal_text = ""

    if not inspection_text and not thermal_text:
        raise ValueError("At least one valid document (inspection or thermal) is required.")

    # Extract
    inspection_data = None
    thermal_data = None
    if inspection_text:
        inspection_data = extract_from_document(inspection_text, "inspection", model=model)
        if verbose:
            print("Inspection extraction complete.")
    if thermal_text:
        thermal_data = extract_from_document(thermal_text, "thermal", model=model)
        if verbose:
            print("Thermal extraction complete.")

    # Merge
    merged, conflicts, missing_list = merge_extractions(inspection_data, thermal_data)
    if verbose:
        print(f"Merged {len(merged['observations'])} observations, {len(conflicts)} conflicts.")

    # Temperature deltas
    merged["temperature_analysis"] = compute_temperature_analysis(merged["temperatures"])
    if verbose:
        print("Temperature analysis complete.")

    # Clustering
    merged["observations"], merged["clusters"] = cluster_observations(merged["observations"])
    if verbose:
        print(f"Clustered into {len(merged['clusters'])} issue clusters.")

    # Urgency scoring
    merged["observations"] = score_urgency(
        merged["observations"],
        merged.get("severity_mentions", []),
        merged.get("temperature_analysis"),
    )
    if verbose:
        print("Urgency scoring complete.")

    # Root cause inference
    merged["observations"] = infer_root_causes(
        merged["observations"],
        merged.get("temperature_analysis"),
        model=model,
    )
    if verbose:
        print("Root cause inference complete.")

    # Confidence scoring
    merged["observations"] = score_confidence(merged["observations"], conflicts)
    if verbose:
        print("Confidence scoring complete.")

    # Generate DDR
    report_md = generate_ddr(merged, conflicts, missing_list, model=model)
    report = format_output(report_md, output_format)

    # Write output
    if output_path:
        Path(output_path).write_text(report, encoding="utf-8")

    return report
