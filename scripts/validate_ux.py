"""Validate responsive UX invariants against a running local dashboard."""

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.settings import Settings  # noqa: I001


VIEWPORTS = {
    "desktop": {"width": 1440, "height": 1000},
    "tablet": {"width": 820, "height": 1000},
    "mobile": {"width": 390, "height": 844},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("data/validation/ux"))
    parser.add_argument("--run", default="trishuli-2026-v3.0-r2")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    token = (
        settings.local_service_token.get_secret_value()
        if settings.local_service_token
        else None
    )
    result = {"status": "passed", "viewports": {}, "page_errors": [], "failed_http": []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/opt/google/chrome/chrome",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        for name, viewport in VIEWPORTS.items():
            context = browser.new_context(
                viewport=viewport,
                extra_http_headers=(
                    {"X-HimaRoad-Service-Token": token} if token else {}
                ),
                bypass_csp=True,
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on(
                "response",
                lambda response: result["failed_http"].append(
                    {"status": response.status, "path": response.url.split("?")[0]}
                )
                if response.status >= 400
                else None,
            )
            page.goto(
                f"{args.url}/?run={args.run}",
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            # The compact layout intentionally hides the header badge visually;
            # readiness remains available in its semantic status element.
            page.wait_for_function(
                "document.querySelector('#systemStatus')?.classList.contains('ready')",
                timeout=120_000,
            )
            measurements = page.evaluate(
                """() => {
                    const visible = (el) => {
                        const style = getComputedStyle(el);
                        const box = el.getBoundingClientRect();
                        return style.display !== 'none' && style.visibility !== 'hidden'
                            && box.width > 0 && box.height > 0;
                    };
                    const smallTargets = [...document.querySelectorAll('button, select')]
                        .filter(visible)
                        .map((el) => {
                            const box = el.getBoundingClientRect();
                            return {label: el.textContent.trim() || el.getAttribute('aria-label'),
                                width: Math.round(box.width), height: Math.round(box.height)};
                        })
                        .filter((item) => item.width < 24 || item.height < 24);
                    return {
                        viewport_width: innerWidth,
                        document_width: document.documentElement.scrollWidth,
                        horizontal_overflow: document.documentElement.scrollWidth > innerWidth + 1,
                        small_targets: smallTargets,
                        active_tab: document.querySelector('.nav.active')?.dataset.tab,
                        main_busy: document.querySelector('#mainContent')?.getAttribute('aria-busy'),
                    };
                }"""
            )
            page.screenshot(path=str(args.output / f"{name}.png"), full_page=False)
            result["viewports"][name] = measurements
            if measurements["horizontal_overflow"] or measurements["small_targets"]:
                result["status"] = "failed"
            context.close()
        browser.close()
    if result["page_errors"] or result["failed_http"]:
        result["status"] = "failed"
    (args.output / "validation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
