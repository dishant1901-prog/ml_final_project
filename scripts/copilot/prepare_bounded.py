"""Prepare a saved run with an enforced per-process memory ceiling (Linux)."""

import argparse
import json
import os
import resource
import time
from pathlib import Path


# The address-space ceiling also constrains native BLAS thread stacks.  Force the
# bounded verifier to one numerical worker before scipy/numpy are imported.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-memory-gib", type=float, default=3.0)
    args = parser.parse_args()
    if not 1 <= args.max_memory_gib <= 24:
        parser.error("memory ceiling must be between 1 and 24 GiB")
    if args.output.exists():
        parser.error("output already exists; choose a fresh result path")
    fields = {line.split(":", 1)[0]: int(line.split()[1])
              for line in Path("/proc/meminfo").read_text().splitlines()}
    available = fields["MemAvailable"] / 1024**2
    if available < args.max_memory_gib + 2:
        parser.error("insufficient available host memory for this ceiling plus 2 GiB headroom")
    limit = int(args.max_memory_gib * 1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    started = time.perf_counter()
    result = {"memory_ceiling_gib": args.max_memory_gib, "status": "failed"}
    print("Starting bounded saved-run preparation", flush=True)
    try:
        from backend.app.preparation import prepare
        from backend.app.settings import Settings

        # Relative run names are intentionally resolved by the admission layer
        # beneath HIMAROAD_DATA_DIR; resolving against the repository would
        # bypass that configured root and refuse an otherwise valid bundle.
        result.update(prepare(args.run, Settings()), status="passed")
    except MemoryError:
        result["reason"] = "per-process memory ceiling reached; preparation not admitted"
    except (ValueError, OSError) as exc:
        result["reason"] = "run preparation refused: " + type(exc).__name__
    result["seconds"] = round(time.perf_counter() - started, 3)
    result["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2), flush=True)
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
