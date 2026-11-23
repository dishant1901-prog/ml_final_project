"""Read-only offline readiness check. Does not download, call providers or prepare runs."""

import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []

    def add(name, status, detail):
        checks.append(dict(check=name, status=status, detail=detail))

    supported = (3, 12) <= sys.version_info[:2] < (3, 14)
    add("python", "pass" if supported else "fail", sys.version.split()[0])
    for package in ("numpy", "rasterio", "geopandas", "fastapi", "weasyprint", "pypdf"):
        try:
            add(package, "pass", importlib.metadata.version(package))
        except importlib.metadata.PackageNotFoundError:
            add(package, "fail", "not installed")
    font_config = json.loads((ROOT / "backend/app/reports/font.json").read_text())
    font = ROOT / "data/copilot/cache/fonts/NotoSansDevanagari.ttf"
    if font.is_file():
        digest = hashlib.sha256(font.read_bytes()).hexdigest()
        add("report_font", "pass" if digest == font_config["sha256"] else "fail", "SHA256 comparison")
    else:
        add("report_font", "warn", "pinned font not downloaded at the default location")
    add("offline_settings", "pass" if (ROOT / ".env").is_file() else "warn",
        ".env presence only; no secret values read")
    add("saved_runs", "pass" if any((ROOT / "data/bundles").glob("*/bundle.json")) else "warn",
        "presence only; use himaroad verify-bundle to verify contents")
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        fields = {line.split(":", 1)[0]: int(line.split()[1]) for line in meminfo.read_text().splitlines()}
        available = fields.get("MemAvailable", 0) / 1024**2
        add("large_run_memory", "pass" if available >= 6 else "warn",
            f"{available:.1f} GiB available; final complete evidence export uses a 6 GiB address-space ceiling")
    add("scope", "pass", "offline only; credentials, live acquisition, GPU and accuracy not checked")
    print(json.dumps({"checks": checks}, indent=2))
    return int(any(c["status"] == "fail" for c in checks))


if __name__ == "__main__":
    raise SystemExit(main())
