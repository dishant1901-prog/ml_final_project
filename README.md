# HimaRoad Flood Copilot

HimaRoad is an educational machine-learning and geospatial decision-support
prototype for flood mapping, road-access screening, and evidence-grounded
bilingual situation reporting in mountainous terrain.

## Course project

- Institution: IIT Jodhpur
- Course: Machine Learning
- Instructor: Richa Singh
- Dishant Kaushik — M24MA2003
- Arushi Gandhi — M24MA2001
- Aditya Sharma — P25AI0201
- Palak Jat — M26MAC006

The final eight-page CVPR-format paper is available at
[`course-report/HimaRoad_Flood_Copilot_CVPR.pdf`](course-report/HimaRoad_Flood_Copilot_CVPR.pdf).

## What the system does

Given an area and flood date, the pipeline combines Sentinel-1 radar,
Sentinel-2 optical observations when usable, Copernicus DEM terrain, and
historical OpenStreetMap infrastructure. It produces:

- candidate flood and debris-like change layers with explicit unknown regions;
- potentially exposed roads and buildings, without claiming confirmed damage;
- settlement-to-town and settlement-to-hospital access scenarios;
- evidence bundles, interactive maps, GeoJSON/KML exports, and PDF reports;
- cited English and Nepali answers whose numbers are resolved from saved facts.

The repository includes a deterministic rule baseline and optional registered
UNet inference. The registered checkpoint is not distributed in this checkout;
its expected SHA-256 and the resulting limitation are documented in
[`CHECKPOINTS.md`](CHECKPOINTS.md) and [`MODEL_CARD.md`](MODEL_CARD.md).

## Repository structure

| Path | Purpose |
|---|---|
| `src/himaroad/` | Acquisition, preprocessing, flood evidence, terrain, exposure, and connectivity engine |
| `backend/app/` | Evidence-grounded API, authentication, reports, and operations |
| `web/` | Responsive browser dashboard |
| `ui/`, `views/`, `app.py` | Streamlit analysis workbench |
| `configs/` | Versioned scientific and event configuration |
| `tests/` | Offline, API, security, queue, and worker tests |
| `results/` | Compact evaluation summaries and example bilingual reports |
| `course-report/` | CVPR source, official style files, figures, and final PDF |
| `artifacts/reproducibility/` | Machine-readable course-report build receipt |

Raw satellite imagery, generated runs, credentials, and large model weights are
excluded from Git. See [`DATASETS.md`](DATASETS.md).

## Requirements

- Linux or macOS
- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Pango/Harfbuzz libraries for PDF generation

On Ubuntu:

```bash
sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
```

## Install

```bash
git clone https://github.com/dishant1901-prog/ml_final_project.git
cd ml_final_project
uv sync --locked
cp .env.example .env
```

The base installation runs the deterministic pipeline and interfaces. Optional
UNet dependencies can be installed with:

```bash
uv sync --locked --extra unet
```

## Verify

Run the complete local quality, security, and compatibility gate:

```bash
bash scripts/ci_local.sh
```

Run the course-deliverable verifier:

```bash
uv run python scripts/verify_course_submission.py --strict-authors --no-write
```

The tests use synthetic fixtures and do not require provider credentials or raw
satellite downloads. Detailed reproduction instructions are in
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

## Run locally

```bash
./scripts/start.sh
```

Open `http://127.0.0.1:8000`. The service is designed for a localhost course
demonstration; it is not certified for operational disaster response. Local
authentication, backup/restore, readiness checks, and worker operation are
documented in [`docs/INTERNAL_OPERATIONS.md`](docs/INTERNAL_OPERATIONS.md).

## Rebuild the report

The report builder uses the official CVPR 2026 author kit and Tectonic. After
the compiler is available at the documented path, run:

```bash
uv run python scripts/build_course_report.py
```

The verifier requires exactly eight US-letter pages and checks that the final
metadata, environment files, checkpoint identity, and repository structure are
present.

## Scientific boundaries

- A mapped overlap is potential exposure, not confirmed damage or closure.
- Radar layover, shadow, speckle, mixed pixels, and observation gaps remain
  explicit limitations.
- The registered UNet achieved zero recall on the retained Himalayan transfer
  evaluation; the result is preserved rather than replaced by an unsupported
  accuracy claim.
- The saved case study is a reproducible screening demonstration, not field
  validation or an emergency routing authority.

## License and data terms

Project code is released under the Apache License 2.0. Satellite, terrain,
OpenStreetMap, font, model, and reference products retain their respective
licenses and terms. See [`DATASETS.md`](DATASETS.md) and the paper bibliography
for provenance.
