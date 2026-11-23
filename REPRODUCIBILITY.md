# Reproducibility statement

This repository provides the source code, locked Python dependency graph,
environment exports, fixed scientific configuration, synthetic offline fixture,
automated tests, report sources and compact verification records needed to
reproduce the software-level results without paid services.

The repository does **not** contain provider imagery, third-party validation
products, historical human labels, or the registered UNet weights. Those assets
are excluded for size, licensing, or availability reasons. Consequently, a clean
checkout can reproduce the deterministic offline pipeline and application tests,
but cannot independently reproduce the historical UNet training metrics or the
authenticated Trishuli acquisition without obtaining the external inputs listed
in `DATASETS.md` and `CHECKPOINTS.md`. No replacement score is inferred when an
asset is missing.

## Supported environment

- Linux x86_64 (primary verified platform)
- Python 3.12
- CPU-only operation for the default detector and copilot
- Optional CUDA device for registered UNet training/inference
- `uv` with `uv.lock` (preferred), or Conda with `environment.yml`

The exact pip resolution is exported in `requirements.txt`. Optional model
packages are in `requirements-model.txt`.

## Clean installation

```bash
git clone https://github.com/dishant1901-prog/ml_final_project.git
cd ml_final_project
uv sync --locked
cp .env.example .env
uv run python scripts/check_credentials.py --help
```

Do not commit `.env`. Live credentials are optional for the offline checks.

## Deterministic offline reproduction

```bash
uv run pytest -q
uv run python scripts/validate_science.py \
  --output artifacts/reproducibility/scientific-validation.json
uv run python scripts/check_offline.py
uv run python scripts/verify_course_submission.py
```

The tests cover geospatial contracts, provenance, graph semantics, report
grounding, bilingual claim parity, refusal behavior, authentication and the web
API. The offline fixture under `data/validation/synthetic-baseline/` is generated
locally and ignored by Git; the tests can rebuild their own temporary fixtures.

## Local showcase

```bash
./scripts/start.sh
```

Then open `http://127.0.0.1:8000`. The default binding is localhost-only. Use the
credentials created by `scripts/configure_local_auth.py`; never publish the
generated credential file.

## Course report

The report uses the official CVPR 2026 author kit at commit
`12909ae437f6dbc7435069cfdb4ca44c18e6a02f`.

```bash
uv run python scripts/build_course_figures.py
uv run python scripts/build_course_report.py
```

The build script checks that the result is exactly eight pages and writes the
engine/version receipt to `artifacts/reproducibility/course-report-build.json`.

## Result boundaries

- Development model scores are model-selection evidence, not a blind estimate.
- The once-only Himalayan windows are small and valley-enriched.
- A zero water mask does not prove absence of flooding.
- Satellite overlap indicates potential exposure, not confirmed damage/closure.
- Cut-off results are graph scenarios, not verified safe routes.
- Copernicus EMS material is evaluation-only and never an inference input.
