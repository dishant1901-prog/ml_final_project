"""Single local worker for the durable analysis queue.

The queue is intentionally one-worker for the internal showcase: satellite runs
are memory-heavy, and a bounded FIFO is safer than competing analyses.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.operations import configure_logging, runtime_store
from backend.app.settings import Settings
from himaroad.pipeline import run

LOG = logging.getLogger("himaroad.worker")


def _path(value, *, root: Path, optional: bool = False) -> str | None:
    if value in (None, "") and optional:
        return None
    path = Path(str(value)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("queued path is outside its allowed root")
    return str(path)


def execute(payload: dict, config: Settings) -> str:
    provider = payload.get("provider")
    detector = payload.get("detector")
    if provider not in {"cdse", "local", "gee"} or detector not in {"baseline", "unet"}:
        raise ValueError("unrecognised queued analysis mode")
    bbox = payload.get("bbox")
    if bbox is not None and (
        not isinstance(bbox, list)
        or len(bbox) != 4
        or any(not isinstance(x, (int, float)) for x in bbox)
    ):
        raise ValueError("queued bounding box is invalid")
    output = _path(payload.get("output"), root=config.himaroad_data_dir / "outputs")
    polygon = _path(
        payload.get("polygon"), root=config.himaroad_data_dir, optional=True
    )
    manifest = _path(
        payload.get("manifest"), root=config.himaroad_data_dir, optional=True
    )
    model_config = _path(
        payload.get("model_config"), root=ROOT / "configs", optional=True
    )
    result = run(
        provider=provider,
        manifest=manifest,
        bbox=bbox,
        polygon=polygon,
        event_date=str(payload.get("event_date")),
        cutoff=payload.get("cutoff") or None,
        detector=detector,
        output=output,
        project=payload.get("project") or None,
        model_config=model_config,
    )
    return str(result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process the local durable analysis queue"
    )
    parser.add_argument(
        "--once", action="store_true", help="Process at most one job and exit"
    )
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if not 0.2 <= args.poll_seconds <= 60:
        parser.error("--poll-seconds must be between 0.2 and 60")
    configure_logging()
    config = Settings()
    store = runtime_store(config)
    recovered = store.recover_stale()
    if recovered:
        LOG.warning(
            "marked interrupted jobs failed", extra={"fields": {"jobs": recovered}}
        )
    while True:
        claimed = store.claim()
        if claimed is None:
            if args.once:
                return
            time.sleep(args.poll_seconds)
            continue
        identifier, payload = claimed
        LOG.info("analysis started", extra={"fields": {"job_id": identifier}})
        try:
            result = execute(payload, config)
            store.finish(identifier, result=result)
            LOG.info("analysis complete", extra={"fields": {"job_id": identifier}})
        except (ValueError, RuntimeError, OSError) as exc:
            # Fixed class only: provider/path details can contain local information.
            store.finish(identifier, error=type(exc).__name__.lower())
            LOG.exception("analysis failed", extra={"fields": {"job_id": identifier}})
        if args.once:
            return


if __name__ == "__main__":
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    main()
