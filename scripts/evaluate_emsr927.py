#!/usr/bin/env python3
"""Reproduce the EMSR927 checking-only comparison from official GRA products.

The official products are never inference inputs.  This command hashes and
freezes the HimaRoad outputs before opening the reference files, scans inference
source for reference leakage, evaluates only overlapping official AOIs, and
writes the result outside the run directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import rasterio
from rasterio.features import rasterize
from shapely.geometry import box


REPO = Path(__file__).resolve().parents[1]
SOURCE_URL = (
    "https://rapidmapping.emergency.copernicus.eu/backend/EMSR927/"
    "{aoi}/GRA_PRODUCT/EMSR927_{aoi}_GRA_PRODUCT_v1.zip"
)
OBSERVATIONS = {
    "AOI01": "2026-08-27T05:05:00Z",
    "AOI02": "2026-08-27T05:05:00Z",
    "AOI03": "2026-08-27T12:09:00Z",
    "AOI05": "2026-08-31T05:01:00Z",
}
# EMS grades "Possibly damaged" as uncertainty, not a confirmed affected label.
AFFECTED = {"Destroyed", "Damaged"}
UNAFFECTED = {"No visible damage"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def freeze(run: Path) -> dict[str, str]:
    names = (
        "manifest.json",
        "report.json",
        "disturbance.tif",
        "unobservable.tif",
        "roads.geojson",
    )
    return {name: sha256(run / name) for name in names}


def leakage_scan() -> dict:
    pattern = re.compile(r"EMSR927|rapidmapping\.emergency\.copernicus", re.I)
    hits = []
    protective = []
    for root in (REPO / "src" / "himaroad",):
        for path in sorted(root.rglob("*.py")):
            # Evaluation is checking-only and cannot be imported by inference.
            if path.name == "evaluate.py":
                continue
            lines = path.read_text(errors="replace").splitlines()
            for number, line in enumerate(lines, 1):
                if pattern.search(line):
                    location = f"{path.relative_to(REPO)}:{number}"
                    context = "\n".join(lines[max(0, number - 7):number + 6]).casefold()
                    if "refus" in context and "inference" in context:
                        protective.append(location)
                    else:
                        hits.append(location)
    return {
        "scope": ["src/himaroad/**/*.py", "excluding evaluate.py"],
        "protective_deny_list_hits": protective,
        "forbidden_reference_hits": hits,
        "passed": not hits,
    }


def truthy(series):
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def reference_rows(gpkg: Path, run_bbox, target_crs):
    layers = {str(item[0]) for item in pyogrio.list_layers(gpkg)}
    frames = []
    for layer in ("transportationL_v1", "transportationP_v1"):
        if layer not in layers:
            continue
        frame = gpd.read_file(gpkg, layer=layer).to_crs(4326)
        frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty]
        frame = frame[frame.geometry.intersects(run_bbox)].copy()
        frame["reference_layer"] = layer
        frame["reference_row"] = frame.index.astype(int)
        frames.append(frame)
    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=target_crs)
    return gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), crs=4326
    ).to_crs(target_crs)


def match_roads(refs, roads, tolerance=20.0):
    predicted = set(
        roads.loc[truthy(roads["potentially_exposed"]), "id"].astype(str)
    )
    matches = []
    for i, row in refs.iterrows():
        candidates = roads[roads.geometry.intersects(row.geometry.buffer(tolerance))]
        identifiers = []
        for _, road in candidates.iterrows():
            geometry = row.geometry
            if geometry.geom_type in {"Point", "MultiPoint"}:
                if str(road.get("bridge", "no")).lower() not in {
                    "", "no", "none", "nan", "false", "0"
                }:
                    identifiers.append(str(road["id"]))
                continue
            overlap = road.geometry.intersection(geometry.buffer(tolerance)).length
            if overlap > 0 and overlap >= min(road.geometry.length, geometry.length) * 0.5:
                identifiers.append(str(road["id"]))
        grade = str(row.get("damage_gra", "Not Analysed"))
        assessment = (
            "affected" if grade in AFFECTED
            else "unaffected" if grade in UNAFFECTED
            else "unknown"
        )
        identifiers = sorted(set(identifiers))
        matches.append(
            {
                "reference_id": (
                    f"EMSR927_{row['reference_layer']}/{int(row['reference_row'])}"
                ),
                "grade": grade,
                "assessment": assessment,
                "link_ids": identifiers,
                "flagged": bool(predicted.intersection(identifiers)),
            }
        )
    affected = [row for row in matches if row["assessment"] == "affected" and row["link_ids"]]
    negative = [row for row in matches if row["assessment"] == "unaffected" and row["link_ids"]]
    return {
        "reference_features": len(refs),
        "matched_reference_features": sum(bool(row["link_ids"]) for row in matches),
        "unmatched_reference_features": sum(not row["link_ids"] for row in matches),
        "affected_matched_features": len(affected),
        "affected_recalled": sum(row["flagged"] for row in affected),
        "affected_road_recall": (
            sum(row["flagged"] for row in affected) / len(affected) if affected else None
        ),
        "reliable_negative_features": len(negative),
        "false_alarm_reference_features": sum(row["flagged"] for row in negative),
        "matches": matches,
    }


def evaluate_aoi(aoi, gpkg, profile, disturbance, roads, run_bbox):
    layers = {str(item[0]) for item in pyogrio.list_layers(gpkg)}
    observed = gpd.read_file(gpkg, layer="observedEventA_v1")
    landslide = observed[
        observed["obj_desc"].astype(str).str.casefold() == "landslide"
    ].to_crs(profile["crs"])
    reference = rasterize(
        ((geometry, 1) for geometry in landslide.geometry if not geometry.is_empty),
        out_shape=(profile["height"], profile["width"]),
        transform=profile["transform"],
        fill=0,
        dtype="uint8",
    ).astype(bool)
    observable = np.isfinite(disturbance)
    assessed = reference & observable
    overlap = assessed & (disturbance > 0)
    pixel_area = abs(profile["transform"].a * profile["transform"].e)
    refs = reference_rows(gpkg, run_bbox, profile["crs"])
    road = match_roads(refs, roads)
    road["unobservable_road_fraction"] = float(
        (roads["evidence_category"] == "unobservable").sum() / max(1, len(roads))
    )
    return {
        "status": "evaluated",
        "reference_source": SOURCE_URL.format(aoi=aoi),
        "reference_observation_timestamp": OBSERVATIONS[aoi],
        "official_gpkg_sha256": sha256(gpkg),
        "landslide_features": len(landslide),
        "landslide": {
            "interpretation": "positive-only footprint agreement; not floodwater accuracy",
            "reference_pixels": int(reference.sum()),
            "observable_reference_pixels": int(assessed.sum()),
            "overlap_pixels": int(overlap.sum()),
            "area_recall": float(overlap.sum() / assessed.sum()) if assessed.any() else None,
            "observed_reference_fraction": float(assessed.sum() / reference.sum()) if reference.any() else None,
            "reference_area_m2": float(reference.sum() * pixel_area),
            "observable_reference_area_m2": float(assessed.sum() * pixel_area),
            "overlap_area_m2": float(overlap.sum() * pixel_area),
            "precision": None,
            "iou": None,
            "f1": None,
        },
        "roads": road,
        "available_layers": sorted(layers),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--reference-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run = args.run.resolve()
    reference_root = args.reference_root.resolve()
    output = args.output.resolve()
    if output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {output}")
    if reference_root == run or reference_root.is_relative_to(run):
        raise SystemExit("reference products must remain outside the inference run")
    before = freeze(run)
    scan = leakage_scan()
    if not scan["passed"]:
        raise SystemExit(f"reference leakage detected: {scan['forbidden_reference_hits']}")
    report = json.loads((run / "report.json").read_text())
    run_bbox = box(*report["bbox"])
    roads = gpd.read_file(run / "roads.geojson")
    with rasterio.open(run / "disturbance.tif") as source:
        profile = source.profile
        disturbance = source.read(1)
    roads = roads.to_crs(profile["crs"])
    aois = {}
    for number in range(1, 7):
        aoi = f"AOI{number:02d}"
        candidates = list((reference_root / aoi).glob("*.gpkg"))
        if not candidates:
            aois[aoi] = {
                "status": "unavailable",
                "reason": "official GRA product unavailable (AOI04/AOI06 return HTTP 404)",
            }
            continue
        if aoi not in OBSERVATIONS:
            raise SystemExit(f"missing registered observation timestamp for {aoi}")
        aois[aoi] = evaluate_aoi(
            aoi, candidates[0], profile, disturbance, roads, run_bbox
        )
    evaluated = [value for value in aois.values() if value["status"] == "evaluated"]
    area_num = sum(value["landslide"]["overlap_pixels"] for value in evaluated)
    area_den = sum(value["landslide"]["observable_reference_pixels"] for value in evaluated)
    road_num = sum(value["roads"]["affected_recalled"] for value in evaluated)
    road_den = sum(value["roads"]["affected_matched_features"] for value in evaluated)
    after = freeze(run)
    if after != before:
        raise SystemExit("run changed while reference products were open")
    result = {
        "schema": "himaroad-emsr927-reproduction-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "checking_only_no_tuning",
        "run": str(args.run),
        "run_freeze_sha256": before,
        "reference_root": str(args.reference_root),
        "inference_leakage_scan": scan,
        "aois": aois,
        "pooled_overlapping_aois": {
            "landslide_positive_area_recall": area_num / area_den if area_den else None,
            "affected_road_recall": road_num / road_den if road_den else None,
            "overlap_pixels": area_num,
            "observable_reference_pixels": area_den,
            "affected_roads_recalled": road_num,
            "affected_roads_matched": road_den,
        },
        "not_scored": {
            "water_iou": "EMSR927 grades landslide, not floodwater",
            "connectivity": "independent confirmed road closures are required",
            "building_accuracy": "no registered building comparison in this evaluator",
        },
        "limitations": [
            "EMSR927 is independent very-high-resolution image interpretation, not field truth.",
            "Only positive landslide footprint is evaluated; precision, IoU and F1 are unavailable without explicit negative assessment coverage.",
            "Road matching is geometry agreement within 20 m, not confirmation of physical closure.",
            "Unobservable pixels, unassessed assets and AOIs outside the run remain unknown.",
            "Official products are opened only after the HimaRoad run is frozen and are never inference inputs.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), **result["pooled_overlapping_aois"]}, indent=2))


if __name__ == "__main__":
    main()
