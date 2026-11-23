#!/usr/bin/env python3
"""Create a small, checksummed course hand-in package from committed Git state."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "course-submission" / "course-project-ready"


def command(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-placeholders", action="store_true",
                        help="build a provisional package before group metadata is supplied")
    args = parser.parse_args()
    output = args.output.resolve()
    data_root = (ROOT / "data").resolve()
    if not output.is_relative_to(data_root):
        raise SystemExit("Output must remain inside the ignored data/ directory")

    verify = [sys.executable, "scripts/verify_course_submission.py", "--no-write"]
    if not args.allow_placeholders:
        verify.append("--strict-authors")
    subprocess.run(verify, cwd=ROOT, check=True)
    dirty = command("git", "status", "--porcelain")
    if dirty:
        raise SystemExit("Commit or stash source changes before packaging")

    report = ROOT / "course-report" / "HimaRoad_Flood_Copilot_CVPR.pdf"
    if len(PdfReader(str(report)).pages) != 8:
        raise SystemExit("Course report is not exactly eight pages")

    if output.exists():
        previous = output.with_name(output.name + "-previous")
        if previous.exists():
            shutil.rmtree(previous)
        output.rename(previous)
    output.mkdir(parents=True)
    shutil.copy2(report, output / report.name)

    with tempfile.TemporaryDirectory(dir=data_root) as temporary:
        archive_tar = Path(temporary) / "HimaRoad-source.tar"
        subprocess.run(
            ["git", "archive", "--format=tar", "--prefix=HimaRoad_flood-copilot/",
             "-o", str(archive_tar), "HEAD"], cwd=ROOT, check=True)
        source = output / "HimaRoad-source.tar.gz"
        with (
            tarfile.open(source, "w:gz", compresslevel=9) as target,
            tarfile.open(archive_tar, "r:") as origin,
        ):
            for member in origin:
                handle = origin.extractfile(member) if member.isfile() else None
                target.addfile(member, handle)

    history = command("git", "log", "--date=iso-strict",
                      "--pretty=format:%H\t%aI\t%an\t%s") + "\n"
    (output / "COMMIT_HISTORY.tsv").write_text(
        "commit\tauthor_timestamp\tauthor\tsubject\n" + history, encoding="utf-8")
    head = command("git", "rev-parse", "HEAD")
    author_source = (ROOT / "course-report" / "authors.tex").read_text(encoding="utf-8")
    repository_match = re.search(r"\\newcommand\{\\RepositoryURL\}\{(.+)\}", author_source)
    repository_url = "INSERT FINAL GITHUB URL"
    if repository_match and "\\Pending" not in repository_match.group(1):
        repository_url = repository_match.group(1)
        wrapped = re.fullmatch(r"\\url\{(.+)\}", repository_url)
        if wrapped:
            repository_url = wrapped.group(1)
        repository_url = repository_url.replace(r"\_", "_")
    readme = (
        "HimaRoad Flood Copilot — course hand-in\n"
        "=========================================\n\n"
        f"Source commit: {head}\n"
        f"Commit timestamp: {command('git', 'show', '-s', '--format=%cI', 'HEAD')}\n"
        f"Repository URL: {repository_url}\n\n"
        "The PDF is exactly eight pages in the official CVPR 2026 format.\n"
        "The source archive is produced from committed Git state and excludes ignored data,\n"
        "credentials and local tools. See COURSE_SUBMISSION.md after extraction.\n"
    )
    (output / "README.txt").write_text(readme, encoding="utf-8")

    files = []
    for path in sorted(output.iterdir()):
        if path.name == "SHA256SUMS.json" or not path.is_file():
            continue
        files.append({"path": path.name, "bytes": path.stat().st_size,
                      "sha256": sha256(path)})
    manifest = {
        "schema": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": head,
        "source_commit_timestamp": command("git", "show", "-s", "--format=%cI", "HEAD"),
        "provisional_metadata": bool(args.allow_placeholders),
        "files": files,
    }
    (output / "SHA256SUMS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "output": str(output),
                      "source_commit": head, "files": len(files)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
