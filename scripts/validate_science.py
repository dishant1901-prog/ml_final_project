#!/usr/bin/env python3
"""Validate event/control discrimination and the fresh EMSR927 reproduction."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd


def load(path):
    return json.loads(Path(path).read_text())


def close(a, b, tolerance=1e-12):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tolerance


def road_counts(run):
    roads = gpd.read_file(Path(run) / "roads.geojson")
    return {str(k): int(v) for k, v in roads["evidence_category"].value_counts().items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True, type=Path)
    parser.add_argument("--control", required=True, type=Path)
    parser.add_argument("--emsr", required=True, type=Path)
    parser.add_argument("--historical", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    event, control, emsr = (
        load(args.event / "report.json"),
        load(args.control / "report.json"),
        load(args.emsr),
    )
    event_roads, control_roads = road_counts(args.event), road_counts(args.control)
    checks = {}

    def check(name, condition, detail):
        checks[name] = {"passed": bool(condition), "detail": detail}

    check(
        "complete_real_runs",
        event["status"] == control["status"] == "complete"
        and not event["synthetic"] and not control["synthetic"],
        {"event": event["status"], "control": control["status"]},
    )
    check("same_aoi", event["bbox"] == control["bbox"], event["bbox"])
    check(
        "same_detector_and_thresholds",
        event["detector"] == control["detector"]
        and event["thresholds"] == control["thresholds"]
        and event["hazard"]["settings"] == control["hazard"]["settings"],
        {"detector": event["detector"], "thresholds": event["thresholds"]},
    )
    event_boundary = datetime.fromisoformat(event["event_date"] + "T00:00:00+00:00")
    control_sources = [
        datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
        for item in control["evidence_sources"]
    ]
    check(
        "control_precedes_event",
        all(stamp < event_boundary for stamp in control_sources),
        {"latest_control_source": max(control_sources).isoformat(), "event": event_boundary.isoformat()},
    )
    check(
        "corroborated_link_discrimination",
        event_roads.get("likely_impact", 0) > 0 and control_roads.get("likely_impact", 0) == 0,
        {"event": event_roads.get("likely_impact", 0), "control": control_roads.get("likely_impact", 0)},
    )
    check(
        "corroborated_cutoff_discrimination",
        event["summary"]["corroborated_road_cut"] > 0
        and control["summary"]["corroborated_road_cut"] == 0,
        {"event": event["summary"]["corroborated_road_cut"], "control": control["summary"]["corroborated_road_cut"]},
    )
    check(
        "reference_leakage_scan",
        emsr["purpose"] == "checking_only_no_tuning"
        and emsr["inference_leakage_scan"]["passed"],
        emsr["inference_leakage_scan"],
    )

    comparisons = {}
    for aoi in ("AOI01", "AOI02"):
        fresh = emsr["aois"][aoi]
        old = load(args.historical / f"trishuli-2026-v3.0-r2.{aoi}.json")
        rows = {
            "landslide_area_recall": [fresh["landslide"]["area_recall"], old["disturbance"]["area_recall"]],
            "affected_road_recall": [fresh["roads"]["affected_road_recall"], old["infrastructure"]["affected_road_recall"]],
            "reference_features": [fresh["roads"]["reference_features"], old["infrastructure"]["reference_features"]],
            "matched_reference_features": [fresh["roads"]["matched_reference_features"], old["infrastructure"]["matched_reference_features"]],
            "reliable_negative_features": [fresh["roads"]["reliable_negative_features"], old["infrastructure"]["reliable_negative_features"]],
        }
        comparisons[aoi] = {
            key: {"fresh": values[0], "historical": values[1], "match": close(*values) if isinstance(values[0], float) else values[0] == values[1]}
            for key, values in rows.items()
        }
    exact = all(item["match"] for rows in comparisons.values() for item in rows.values())
    check("historical_metric_reproduction", exact, comparisons)
    broad = {
        "event_potentially_road_cut": event["summary"]["potentially_road_cut"],
        "control_potentially_road_cut": control["summary"]["potentially_road_cut"],
        "interpretation": "single-track observed-change scenario is a sensitivity bound, not the headline",
    }
    result = {
        "schema": "himaroad-scientific-validation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if all(item["passed"] for item in checks.values()) else "failed",
        "checks": checks,
        "event": {
            "hazard_pixels": event["hazard"]["pixels"],
            "road_categories": event_roads,
            "summary": event["summary"],
        },
        "pre_event_control": {
            "hazard_pixels": control["hazard"]["pixels"],
            "road_categories": control_roads,
            "summary": control["summary"],
        },
        "broad_scenario_warning": broad,
        "emsr927_reproduction": comparisons,
        "interpretation": [
            "The strict result is event/control discrimination, not field-verified damage accuracy.",
            "EMSR927 agreement remains low and is reported unchanged; it grades landslides, not floodwater.",
            "A zero control result for corroborated links does not establish a universal false-positive rate.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "status": result["status"], "checks": checks}, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
