#!/usr/bin/env python3
"""Build and validate the pinned CVPR-format course report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "course-report"
BUILD = REPORT / "build"
FINAL = REPORT / "HimaRoad_Flood_Copilot_CVPR.pdf"
EXPECTED_KIT_COMMIT = "12909ae437f6dbc7435069cfdb4ca44c18e6a02f"
SOURCE_DATE_EPOCH = "1767225600"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run(command: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=cwd, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-authors", action="store_true",
                        help="fail if group/course/repository placeholders remain")
    args = parser.parse_args()

    authors = (REPORT / "authors.tex").read_text(encoding="utf-8")
    placeholders = sorted(set(re.findall(r"\\Pending\{([^}]+)\}", authors)))
    if placeholders and args.strict_authors:
        raise SystemExit("Unresolved author metadata: " + ", ".join(placeholders))
    if placeholders:
        print("NOTICE: author metadata is intentionally pending:", ", ".join(placeholders))

    run([sys.executable, "scripts/build_course_figures.py"])
    BUILD.mkdir(parents=True, exist_ok=True)
    tectonic = ROOT / ".tools" / "tectonic"
    if not tectonic.is_file():
        raise SystemExit("Missing .tools/tectonic; see REPRODUCIBILITY.md")
    env = os.environ.copy()
    env["XDG_CACHE_HOME"] = str(ROOT / ".cache" / "tectonic")
    env["SOURCE_DATE_EPOCH"] = SOURCE_DATE_EPOCH
    run([str(tectonic), "-X", "compile", "main.tex", "--outdir", str(BUILD),
         "--keep-logs", "--keep-intermediates"], cwd=REPORT, env=env)

    built = BUILD / "main.pdf"
    if not built.is_file():
        raise SystemExit("Tectonic did not produce main.pdf")
    log = (BUILD / "main.log").read_text(encoding="utf-8", errors="replace")
    bad = [line for line in log.splitlines()
           if re.search(r"(Citation .* undefined|Reference .* undefined|There were undefined references)", line)]
    if bad:
        raise SystemExit("Unresolved report references:\n" + "\n".join(bad[:20]))
    pages = len(PdfReader(str(built)).pages)
    if pages != 8:
        raise SystemExit(f"Course report must be exactly 8 pages; built {pages}")
    shutil.copyfile(built, FINAL)

    receipt_dir = ROOT / "artifacts" / "reproducibility"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": 1,
        "author_kit_commit": EXPECTED_KIT_COMMIT,
        "source_date_epoch": int(SOURCE_DATE_EPOCH),
        "engine": subprocess.check_output([str(tectonic), "--version"], text=True).strip(),
        "source": "course-report/main.tex",
        "source_sha256": sha256(REPORT / "main.tex"),
        "pdf": str(FINAL.relative_to(ROOT)),
        "pdf_sha256": sha256(FINAL),
        "pages": pages,
        "author_placeholders_remaining": placeholders,
    }
    (receipt_dir / "course-report-build.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Built {FINAL} ({pages} pages, SHA256 {receipt['pdf_sha256']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
