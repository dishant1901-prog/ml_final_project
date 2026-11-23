# Internal showcase operations

This runbook is for a free, localhost-only showcase. It is not authorization to
expose HimaRoad to the public internet or use its outputs as confirmed road,
damage or evacuation information.

## Security boundary

- `scripts/start.sh` binds the evidence app and workbench to `127.0.0.1`.
- Without configured accounts the API rejects non-loopback clients.
- `scripts/configure_local_auth.py` creates separate administrator and viewer
  accounts. It stores only scrypt password hashes in `.env`; the one-time
  plaintext credentials are written to a mode-0600 file under ignored `data/`.
- Browser authentication creates an eight-hour, signed, HTTP-only, same-site
  cookie. Evidence bearer tokens remain separate and expire after one hour.
- Streamlit uses a dedicated local service token. Do not use that token in a
  browser, copy it into logs or share the `.env` file.
- Security headers, a global per-identity request limit and fixed body/file
  budgets are enabled. Authentication does not make plain HTTP safe outside the
  host; a future network deployment requires TLS and an external identity layer.

Rotate local accounts before each demonstration if credentials have been shared:

```bash
mv data/private/internal-credentials.txt data/private/internal-credentials.retired
.venv/bin/python scripts/configure_local_auth.py
```

## Start and stop

Install exactly the audited lock and start all three local processes:

```bash
uv sync --locked
scripts/start.sh
```

Open:

- evidence dashboard: `http://127.0.0.1:8000/`
- analysis workbench: `http://127.0.0.1:8501/`
- liveness: `http://127.0.0.1:8000/health`
- readiness: `http://127.0.0.1:8000/ready`

The terminal owns the web server, one durable analysis worker and Streamlit.
Press `Ctrl+C` once to stop all three. Do not close the terminal while an analysis
is running. A worker restart marks a stale interrupted job failed instead of
silently resuming into an uncertain output directory.

## Durable queue

The workbench submits analysis parameters to `DATA_ROOT/runtime.sqlite3`. One
worker claims jobs in FIFO order. The queue is capped by `MAX_QUEUED_JOBS`
(default 16); satellite processing remains single-worker because measured runs
are memory-heavy. Session capability digests are stored in the same runtime
database, separate from immutable evidence records.

An administrator can inspect bounded runtime state at `/api/admin/runtime`.
Structured request and worker logs are written to the launch terminal as one JSON
object per line. `/metrics` provides local Prometheus text when authenticated.

## Local container alternative

Docker is not required. If Docker or Podman becomes available, the checked-in
`Dockerfile` runs as UID 10001 with all Linux capabilities dropped, and
`compose.yaml` binds both published ports to loopback:

```bash
docker compose build
docker compose up
```

The code image excludes `.env`, provider data, caches, Git metadata and reports.
The host `data/` directory is mounted at `/data`.

## Verification gate

Run before an internal demonstration and after every dependency or code change:

```bash
scripts/ci_local.sh
```

It checks the lock, installed compatibility, byte-compilation, unit/integration
tests, offline readiness, whitespace, known dependency vulnerabilities and the
assembled submission when present. The equivalent free GitHub Actions workflow
is included but does not require publishing the repository for local use.

The full prepared-dashboard browser regression is deliberately separate because
it needs the retained case-study data and several minutes:

```bash
set -a; . ./.env; set +a
.venv/bin/python scripts/validate_browser.py --run live-validation-v2-2026-11-02
```

## Backup and recovery

The backup contains the runtime queue/sessions database and immutable evidence
database. It excludes provider credentials, account credentials and raw imagery.

```bash
.venv/bin/python scripts/local_backup.py create /safe/offline/himaroad-backup.zip
.venv/bin/python scripts/local_backup.py verify /safe/offline/himaroad-backup.zip
```

Restore is intentionally allowed only into an absent or empty directory. Verify
there first; replacing live databases is a later, explicit maintenance action:

```bash
mkdir /tmp/himaroad-restore-check
.venv/bin/python scripts/local_backup.py restore \
  /safe/offline/himaroad-backup.zip /tmp/himaroad-restore-check
```

## Demonstration acceptance checklist

1. `/ready` returns `ready`; the provider is not needed for a saved-run demo.
2. Sign in first as viewer and then as administrator; reject an incorrect password.
3. Open the fresh live-validation run and confirm the strict S3 headline is
   19 of 73, with 16 corroborated road links in the evidence page.
4. Switch all four hypothetical scenarios and confirm the UI never calls a route
   safe or a feature damaged/closed.
5. Open an English and Nepali cited answer and inspect an underlying claim.
6. Trace the example DEM flow path and confirm it is labelled a terrain trace.
7. Generate both one-page PDF reports.
8. Submit no paid provider job during the showcase; use retained saved evidence.
9. Stop/restart the app and confirm the runtime database remains healthy.
10. Record the reviewer, time, browser, failed steps and screenshots. Any failure
    blocks external deployment; it does not justify hiding a limitation.

## Remaining external production gates

This local hardening does not change the scientific measurements. The final flood
extent remains empty, held-out Himalayan UNet transfer is poor and EMSR927
landslide recall is low. A commercial deployment still requires multi-event
independent validation, responder acceptance, TLS/SSO, managed backups, external
monitoring, an incident owner and a clean published release.
