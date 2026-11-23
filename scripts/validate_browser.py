import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.settings import Settings

parser = argparse.ArgumentParser(
    description="Validate saved-run dashboard in local Chrome"
)
parser.add_argument("--output", type=Path, default=Path("data/validation/browser"))
parser.add_argument(
    "--report-only", action="store_true", help="Focus on report and run-reset checks"
)
parser.add_argument(
    "--run", default="trishuli-2026-v3.0-r2", help="Bundle name to validate"
)
args = parser.parse_args()
root = Path.cwd()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
bundle = Path(os.environ.get("HIMAROAD_DATA_DIR", root / "data")) / "bundles" / args.run
report = json.loads((bundle / "report.json").read_text())
settlement_features = json.loads((bundle / "settlements.geojson").read_text())[
    "features"
]
expected_scenarios = {
    str(n): sum(
        f["properties"].get("baseline_accessible") is True
        and f["properties"].get(f"scenario{n}_accessible") is False
        for f in settlement_features
    )
    for n in range(1, 5)
}
s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
url = f"http://127.0.0.1:{port}"
log = (out / "server.log").open("w")
code = f'import resource; resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3)); import uvicorn; uvicorn.run("web.server:app",host="127.0.0.1",port={port},log_level="warning")'
env = {
    **os.environ,
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MPLCONFIGDIR": str(root / "data/cache/matplotlib"),
}
proc = subprocess.Popen(
    [str(root / ".venv/bin/python"), "-c", code], stdout=log, stderr=log, env=env
)
config = Settings()
service_token = (
    config.local_service_token.get_secret_value()
    if config.local_service_token
    else None
)
result = {
    "status": "running",
    "url": url,
    "page_errors": [],
    "failed_http": [],
    "phases": [],
    "requests": [],
}
start = time.monotonic()


def checkpoint(name):
    entry = {"phase": name, "seconds": round(time.monotonic() - start, 3)}
    result["phases"].append(entry)
    print(json.dumps(entry), flush=True)
    (out / "validation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )


try:
    for _ in range(100):
        try:
            urllib.request.urlopen(url + "/health", timeout=2).close()
            break
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError("Server exited; inspect server.log")
            time.sleep(0.2)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/opt/google/chrome/chrome",
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100},
            extra_http_headers=(
                {"X-HimaRoad-Service-Token": service_token} if service_token else {}
            ),
            # Validation-only: wait_for_function uses eval, which the real CSP forbids.
            bypass_csp=True,
        )
        page = context.new_page()
        page.on(
            "requestfailed",
            lambda r: result["requests"].append(
                {"path": r.url.split("?")[0], "failure": r.failure}
            ),
        )
        page.on(
            "response",
            lambda r: (
                result["requests"].append(
                    {
                        "path": r.url.split("?")[0],
                        "status": r.status,
                        "seconds": round(time.monotonic() - start, 3),
                    }
                )
                if "/api/report" in r.url
                else None
            ),
        )
        page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
        page.on(
            "response",
            lambda r: (
                result["failed_http"].append(
                    {"status": r.status, "path": r.url.split("?")[0]}
                )
                if r.status >= 400
                else None
            ),
        )
        page.goto(
            url + f"/?run={args.run}", wait_until="domcontentloaded", timeout=60000
        )
        page.wait_for_function(
            'document.querySelector("#cstatus").textContent.startsWith("Evidence verified")',
            timeout=240000,
        )
        checkpoint("evidence_loaded")
        result["metrics"] = {
            x: page.locator("#" + x).inner_text()
            for x in ["mCut", "mBld", "mLinks", "mCov"]
        }
        summary = report["summary"]
        initial = (
            "3"
            if args.run.startswith("live-validation-v2-")
            else str(report["primary_scenario"])
        )
        assert result["metrics"]["mCut"].startswith(str(expected_scenarios[initial])), (
            result["metrics"]
        )
        assert result["metrics"]["mBld"] == str(
            summary["potentially_exposed_buildings"]
        ), result["metrics"]
        assert result["metrics"]["mLinks"] == str(
            summary["suspected_affected_links"]
        ), result["metrics"]
        if not args.report_only:
            result["scenarios"] = {}
            for n in ("4", "3", "2", "1"):
                page.select_option("#scenario", n)
                value = page.locator("#mCut").inner_text()
                assert value.startswith(str(expected_scenarios[n])), value
                result["scenarios"][n] = value
            for lang in ["en", "ne"]:
                page.click(f'[data-lang="{lang}"]')
                before = page.locator("#chat .cite").count()
                page.click('#chips [data-q="summary"]')
                page.wait_for_function(
                    '(n)=>document.querySelectorAll("#chat .cite").length>n',
                    arg=before,
                    timeout=30000,
                )
                result["answer_" + lang] = page.locator("#chat .cite").last.inner_text()
                assert "passed" in result["answer_" + lang]
            citation = page.locator("#chat button[data-claims]").first
            assert citation.count() == 1
            citation.click()
            page.wait_for_function(
                'document.querySelector("#chat .claim-record pre")?.textContent.includes("sources")',
                timeout=30000,
            )
            result["citation_claim"] = page.locator(
                "#chat .claim-record b"
            ).inner_text()
            assert result["citation_claim"]
            # Selection must be scoped to the verified run, including its subject prefix.
            page.locator("#rows tr").first.click()
            selected = page.evaluate("state.selected")
            with page.expect_request("**/api/ask") as pending:
                page.click('#chips [data-q="isolation"]')
            assert (
                pending.value.post_data_json["selected_subject"]
                == "settlements:" + selected
            )
            page.wait_for_function(
                '!document.querySelector("#chat .msg:last-child").textContent.includes("Reading the cited")',
                timeout=30000,
            )
            result["selected_subject"] = pending.value.post_data_json[
                "selected_subject"
            ]
            page.evaluate('map.fire("click", {latlng:L.latLng(28.271,85.378)})')
            page.click("#traceBtn")
            page.wait_for_function(
                'document.querySelector("#flowOut").textContent.includes("downstream") || document.querySelector("#flowOut").textContent.includes("refused")',
                timeout=60000,
            )
            result["flow"] = page.locator("#flowOut").inner_text()
            assert "refused" not in result["flow"].lower(), result["flow"]
            page.screenshot(path=str(out / "overview.png"), full_page=True)
        page.click('[data-tab="report"]')
        page.click('[data-report="en"]')
        checkpoint("report_requested")
        page.wait_for_function(
            "["
            + '"ready","error"'
            + '].includes(document.querySelector("#reportStatus").dataset.state)',
            timeout=90000,
        )
        assert page.locator("#reportStatus").get_attribute("data-state") == "ready", (
            page.locator("#reportStatus").inner_text()
        )
        checkpoint("report_ready")
        result["report"] = page.locator("#reportStatus").inner_text()
        assert page.locator("#pdfDownload").get_attribute("href").startswith("blob:")
        # Hold an answer across a reload to reproduce the stale-response race.
        page.evaluate("""() => {
            const original = api;
            window.releaseOldAnswer = null;
            api = (path, opts) => path === '/api/ask'
                ? new Promise(resolve => { window.releaseOldAnswer = resolve; })
                : original(path, opts);
            ask('summary', 'Delayed old-run request');
            window.reloadRun = loadRun(state.run);
        }""")
        page.wait_for_function("state.token !== null", timeout=240000)
        page.evaluate("""async () => {
            await window.reloadRun;
            window.releaseOldAnswer({answer: {outcome: 'refused', text: 'STALE_ANSWER'}});
            await new Promise(resolve => setTimeout(resolve, 100));
        }""")
        assert "STALE_ANSWER" not in page.locator("#chat").inner_text()
        assert page.locator("#chat .msg.user").count() == 0
        assert page.locator("#pdfDownload").get_attribute("href") is None
        assert page.locator("#flowOut").inner_text() == ""
        assert page.evaluate("state.selected === null && state.pick === null")
        result["run_reset_and_stale_answer"] = "passed"
        browser.close()
    assert not result["page_errors"], result["page_errors"]
    assert not result["failed_http"], result["failed_http"]
    result["status"] = "passed"
except Exception as exc:
    result["status"] = "failed"
    try:
        result["report_status"] = page.locator("#reportStatus").inner_text(timeout=2000)
        result["report_state"] = page.locator("#reportStatus").get_attribute(
            "data-state", timeout=2000
        )
        page.screenshot(path=str(out / "failure.png"), timeout=5000)
    except (PlaywrightError, NameError) as capture_error:
        result["failure_capture_error"] = type(capture_error).__name__
    result["error"] = f"{type(exc).__name__}: {exc}"
    raise
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    log.close()
    result["seconds"] = round(time.monotonic() - start, 3)
    (out / "validation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    )
print(json.dumps(result, ensure_ascii=False))
