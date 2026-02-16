"""Temperature delta calculation and anomaly detection for merged readings."""

import re
from typing import Any

# Default threshold (°C) above which |delta| is flagged as anomaly
DEFAULT_ANOMALY_THRESHOLD_C = 5.0


def _parse_value(raw: Any) -> float | None:
    """Parse numeric value from string; handle '23.5', '23.5°C', '22–24' (midpoint)."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Remove degree symbols and trailing unit letters
    s = re.sub(r"°[CFcf]?\s*$", "", s)
    s = s.strip()
    # Range like "22-24" or "22–24"
    range_match = re.search(r"^(-?\d*\.?\d+)\s*[–\-]\s*(-?\d*\.?\d+)$", s)
    if range_match:
        lo = float(range_match.group(1))
        hi = float(range_match.group(2))
        return (lo + hi) / 2.0
    # Single number
    num_match = re.search(r"-?\d+\.?\d*", s)
    if num_match:
        return float(num_match.group(0))
    return None


def _normalize_to_celsius(value: float, unit: str) -> float:
    """Convert value to Celsius for consistent delta calculation."""
    u = (unit or "").strip().upper().replace("°", "")
    if "F" in u or "FAHRENHEIT" in u:
        return (value - 32.0) * 5.0 / 9.0
    return value


def _celsius_to_original(value_c: float, unit: str) -> float:
    """Convert Celsius back to original unit for delta display."""
    u = (unit or "").strip().upper().replace("°", "")
    if "F" in u or "FAHRENHEIT" in u:
        return value_c * 9.0 / 5.0 + 32.0
    return value_c


def compute_temperature_analysis(
    temperatures: list[dict[str, Any]],
    anomaly_threshold_c: float = DEFAULT_ANOMALY_THRESHOLD_C,
) -> dict[str, Any]:
    """
    Compute reference (median of readings), per-reading delta, and anomaly flags.
    Returns structure suitable for merged["temperature_analysis"].
    """
    if not temperatures:
        return {
            "reference_value": None,
            "reference_unit": None,
            "readings": [],
        }

    # Parse and normalize to Celsius for comparison
    parsed: list[dict[str, Any]] = []
    values_c: list[float] = []
    for t in temperatures:
        loc = t.get("location", "")
        unit = (t.get("unit") or "°C").strip() or "°C"
        val = _parse_value(t.get("value"))
        if val is None:
            continue
        val_c = _normalize_to_celsius(val, unit)
        parsed.append({
            "location": loc,
            "value": val,
            "unit": unit,
            "value_c": val_c,
        })
        values_c.append(val_c)

    if not values_c:
        return {
            "reference_value": None,
            "reference_unit": None,
            "readings": [],
        }

    # Reference = median (robust to outliers)
    values_sorted = sorted(values_c)
    n = len(values_sorted)
    if n % 2 == 1:
        reference_c = values_sorted[n // 2]
    else:
        reference_c = (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2.0

    # Use first reading's unit for reference display
    first_unit = parsed[0]["unit"] if parsed else "°C"
    reference_value = _celsius_to_original(reference_c, first_unit)

    readings: list[dict[str, Any]] = []
    for p in parsed:
        delta_c = p["value_c"] - reference_c
        unit = p["unit"]
        delta_display = _celsius_to_original(reference_c + delta_c, unit) - _celsius_to_original(reference_c, unit)
        anomaly = abs(delta_c) > anomaly_threshold_c
        readings.append({
            "location": p["location"],
            "value": p["value"],
            "unit": unit,
            "delta": round(delta_display, 2),
            "delta_c": round(delta_c, 2),
            "anomaly": anomaly,
        })

    return {
        "reference_value": round(reference_value, 2),
        "reference_unit": first_unit,
        "readings": readings,
    }
