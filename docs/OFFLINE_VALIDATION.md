# Offline validation

Run commands from the repository root. Core checks require the locked Python
environment but do not need satellite/OSM credentials, torch or a GPU.

```sh
UV_CACHE_DIR=.cache/uv uv sync --locked --python 3.12
.venv/bin/python scripts/check_offline.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=data/cache/matplotlib .venv/bin/python -m unittest discover -s tests -v
```

For the PDF checks, first fetch the pinned font and license:

```sh
.venv/bin/python scripts/copilot/fetch_font.py --output data/copilot/cache/fonts
```

The tests use small synthetic raster/OSM fixtures and the real analysis pipeline,
bundle creation, schema validation, evidence database and API middleware.
Both radar-only and radar/optical cases are checked. Each executes eight questions
in English and Nepali and compares citations. With the font present, each also
renders both PDFs and checks one-page layout and OSM credit text. Tests reject
modified bundles, unpaired optical support, unauthorized claims and revoked API
sessions. Synthetic results do not establish real-event accuracy or fluent Nepali.

In-process API checks use the actual ASGI middleware without opening listening
sockets. Some execution sandboxes prevent AnyIO worker-thread callbacks; this
can appear as a request timeout even when asynchronous routes work. If that
occurs, rerun the same suite in the ordinary local shell before diagnosing the
application. Do not weaken session or evidence checks to bypass the sandbox.

## Verified sample

The original public Trishuli baseline archive was downloaded to `data/release/`.
Its release SHA256 is
`abfa80a8585c17bd0f47705d27357c9d6fc2c952bce57c5b56207960165d9879`.
The archive contains 86 indexed bundle files (about 402 MB unpacked). It was
extracted to `data/bundles/trishuli-2026-v3.0-r2` and verified with:

```sh
.venv/bin/himaroad verify-bundle data/bundles/trishuli-2026-v3.0-r2
```

Saved-run input/schema validation passed on 30 October 2026: 84 recorded run/input
hashes, 15.843 seconds, 407,648 KiB peak RSS. The record is in the ignored local
file `data/validation/trishuli-metadata.json`. This is not full evidence preparation,
model inference or an independent accuracy evaluation.

Unrestricted case-study preparation is deferred while the shared host has low
available RAM and full swap. Check current resources before starting it;
the README recommends about 24 GB RAM. Do not change other users' workloads.

For a deliberately bounded Linux preparation measurement, use a fresh result path:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m scripts.copilot.prepare_bounded data/bundles/trishuli-2026-v3.0-r2 --output data/validation/trishuli-preparation.json --max-memory-gib 3
```

This limits virtual address space for that process and requires another 2 GiB of
available host memory before starting. A memory-limit failure is recorded as a
failed preparation, not admitted evidence. It is not a replacement for adequate
host resources, nor a guarantee of end-to-end completion.

The first bounded Trishuli preparation passed: 62,263 claims with passing
integrity, 1,002.921 seconds, 1,478,544 KiB peak RSS. The actual record is
`data/validation/trishuli-bounded-preparation.json`. These timings apply to this
shared host and do not establish a service-level target.

The real-case API validation also passed under the 3 GiB process ceiling:
16 answers across eight questions and two languages had passing validation and
matching bilingual claim IDs. Both PDFs were one page with attribution text.
Total time was 130.478 seconds, peak RSS 2,449,364 KiB; answers took 0.628–0.909
seconds and each PDF about 24 seconds. Artifacts are retained in
`data/validation/trishuli-api/`. To repeat with a fresh output directory:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=data/cache/matplotlib .venv/bin/python -m scripts.copilot.validate_saved data/bundles/trishuli-2026-v3.0-r2 --output data/validation/trishuli-api-repeat --max-memory-gib 3
```

Retained synthetic report artifacts are in
`data/validation/synthetic-baseline/reports/`. That explicitly synthetic pipeline
run completed in 24.099 seconds with 355,800 KiB peak RSS and 446 claims. Its
`validation.json` and report `sha256.json` record results and artifact hashes.

## Initial verified corrections

- Radar-only schema 3.0 runs can enter the companion without invented optical
  metadata. Absent pairs must have no finite optical raster observations, even
  zero-valued ones. Runs with paired optical observations retain strict metadata
  validation. Historical bundle files are unchanged.
- Runtime package version agrees with project metadata (1.0.0).
- Browser flow output reads the producer's `along_m`, retains compatibility with
  `distance_along_m`, and uses `settlement_id` for unnamed-feature fallback.

The scientific thresholds and reviewed English/Nepali template sources have not
been changed. Prepared-run software fingerprints will correctly become stale
after changes to the importer; prepare affected runs again before using them.

## Browser regression

With the verified/prepared Trishuli bundle, optional Playwright package and local
Chrome installed, run:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=data/cache/matplotlib .venv/bin/python scripts/validate_browser.py
```

The script opens a temporary localhost-only server with a 4 GiB address-space
ceiling and closes it afterward. Chrome currently uses
`/opt/google/chrome/chrome`; it is not bundled with the repository. The host must
permit localhost sockets/browser processes. Results and a screenshot are saved
under `data/validation/browser/`. Checks cover scenario/asset counts, bilingual
answers, selection request scope, DEM tracing, PDF preview, run reset and a
held stale answer. Browser tests use the saved bundle and do not measure live
acquisition reliability or scientific accuracy.
