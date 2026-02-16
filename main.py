#!/usr/bin/env python3
"""CLI entry point for the AI DDR Report Generator."""

import argparse
from pathlib import Path

# Load .env from project root (same folder as main.py)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from src.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Detailed Diagnostic Report (DDR) from inspection and thermal documents."
    )
    parser.add_argument(
        "--inspection",
        type=Path,
        help="Path to the inspection report (PDF, DOCX, or TXT)",
    )
    parser.add_argument(
        "--thermal",
        type=Path,
        help="Path to the thermal report (PDF, DOCX, or TXT)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path for the DDR report",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "json", "html"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="gemini-2.0-flash",
        help="Gemini model (default: gemini-2.0-flash)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print intermediate progress",
    )

    args = parser.parse_args()

    if not args.inspection and not args.thermal:
        parser.error("At least one of --inspection or --thermal is required.")

    try:
        report = run_pipeline(
            inspection_path=args.inspection,
            thermal_path=args.thermal,
            output_path=args.output,
            output_format=args.format,
            model=args.model,
            verbose=args.verbose,
        )
        if not args.output:
            print(report)
    except Exception as e:
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
