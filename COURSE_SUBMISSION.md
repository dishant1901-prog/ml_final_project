# HimaRoad Flood Copilot — course submission guide

Submission deadline: **24 November 2026, 12:00 noon IST**.

## Items to submit

1. Repository URL: **https://github.com/dishant1901-prog/ml_final_project.git**
2. Eight-page CVPR-format report: `course-report/HimaRoad_Flood_Copilot_CVPR.pdf`

The report metadata identifies all four group members, their roll numbers,
IIT Jodhpur, the Machine Learning course, instructor Richa Singh and the final
repository URL. Rebuild and run the strict verifier after any later correction.

## Repository map

| Path | Purpose |
|---|---|
| `src/himaroad/` | acquisition, preprocessing, hazard, graph and export engine |
| `backend/app/` | evidence-grounded copilot API and report generation |
| `web/`, `ui/`, `views/` | polished browser and Streamlit interfaces |
| `configs/` | versioned scientific and event configuration |
| `tests/` | unit, contract, security and integration tests |
| `scripts/` | validation, packaging and local operation commands |
| `course-report/` | official CVPR 2026 LaTeX source, figures and final PDF |
| `artifacts/reproducibility/` | compact machine-readable verification records |

Raw provider data and large generated run products are intentionally excluded
from Git. See `DATASETS.md`. The registered UNet weights are also not in this
checkout; their exact expected identity and the resulting limitation are in
`CHECKPOINTS.md` and `MODEL_CARD.md`.

## Fast reproduction

```bash
uv sync --locked
cp .env.example .env
uv run pytest -q
uv run python scripts/verify_course_submission.py
./scripts/start.sh
```

Open `http://127.0.0.1:8000`. For a deterministic offline scientific smoke
test, follow `REPRODUCIBILITY.md`.

## Final checklist

- [x] Replace all author/course placeholders.
- [x] Insert the final repository URL above and in `course-report/authors.tex`.
- [x] Run `uv run python scripts/build_course_report.py`.
- [x] Run `uv run python scripts/verify_course_submission.py --strict-authors`.
- [x] Confirm the PDF has exactly eight pages.
- [x] Confirm `.env`, `data/private/`, raw datasets and local credentials are absent from Git.
- [x] Confirm the final commit hash and timestamp with `git log --show-signature -n 10`.
- [x] Build the final checksummed hand-in folder after the metadata commit.
- [x] Push the metadata-complete project to the confirmed repository.
