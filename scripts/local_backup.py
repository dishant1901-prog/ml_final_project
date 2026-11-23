"""Create, verify and restore secret-free local runtime database backups."""

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.settings import Settings


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def sources(config: Settings) -> dict[str, Path]:
    return {
        "runtime.sqlite3": config.data_root / "runtime.sqlite3",
        "evidence.sqlite3": config.data_root / "outputs" / "copilot.sqlite3",
    }


def copy_database(source: Path, destination: Path) -> None:
    if source.is_symlink() or not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with (
        sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original,
        sqlite3.connect(destination) as copy,
    ):
        original.backup(copy)
        if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("database integrity check failed")


def create(output: Path, config: Settings) -> None:
    output = output.resolve()
    if output.exists():
        raise FileExistsError("backup output already exists")
    partial = output.with_suffix(output.suffix + ".partial")
    if partial.exists():
        raise FileExistsError("partial backup already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="himaroad-backup-") as temporary:
        root = Path(temporary)
        records = []
        for name, source in sources(config).items():
            destination = root / "databases" / name
            copy_database(source, destination)
            if destination.exists():
                records.append(
                    {
                        "path": f"databases/{name}",
                        "bytes": destination.stat().st_size,
                        "sha256": digest(destination),
                    }
                )
        if not records:
            raise ValueError("no runtime databases are available to back up")
        manifest = {
            "schema": "himaroad-local-backup-v1",
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": records,
            "excludes": [
                "provider credentials",
                "local account credentials",
                "raw satellite cache",
            ],
        }
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        with zipfile.ZipFile(
            partial, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1
        ) as archive:
            archive.write(root / "manifest.json", "manifest.json")
            for record in records:
                archive.write(root / record["path"], record["path"])
    partial.chmod(0o600)
    partial.replace(output)


def inspect(archive_path: Path) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise ValueError("backup members are invalid")
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise ValueError("unsafe backup member")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("schema") != "himaroad-local-backup-v1":
            raise ValueError("unknown backup schema")
        expected = {"manifest.json", *(record["path"] for record in manifest["files"])}
        if set(names) != expected:
            raise ValueError("backup membership differs from manifest")
        for record in manifest["files"]:
            content = archive.read(record["path"])
            if (
                len(content) != record["bytes"]
                or hashlib.sha256(content).hexdigest() != record["sha256"]
            ):
                raise ValueError("backup checksum mismatch")
    return manifest


def restore(archive_path: Path, target: Path) -> None:
    manifest = inspect(archive_path)
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise FileExistsError("restore target must be absent or empty")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        for record in manifest["files"]:
            name = Path(record["path"]).name
            destination = target / name
            with destination.open("xb") as handle:
                handle.write(archive.read(record["path"]))
            destination.chmod(0o600)
            with sqlite3.connect(
                destination.as_uri() + "?mode=ro", uri=True
            ) as connection:
                if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("restored database integrity check failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="HimaRoad local database backup")
    sub = parser.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("output", type=Path)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("archive", type=Path)
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("archive", type=Path)
    restore_parser.add_argument("target", type=Path)
    args = parser.parse_args()
    if args.command == "create":
        create(args.output, Settings())
        print(f"Created verified backup: {args.output.resolve()}")
    elif args.command == "verify":
        manifest = inspect(args.archive)
        print(
            json.dumps({"status": "passed", "files": len(manifest["files"])}, indent=2)
        )
    else:
        restore(args.archive, args.target)
        print(f"Restored and checked databases under: {args.target.resolve()}")


if __name__ == "__main__":
    main()
