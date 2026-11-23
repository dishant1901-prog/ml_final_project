"""Exercise a prepared local run through ASGI; no server sockets or provider calls."""

import argparse
import asyncio
import io
import json
import resource
import time
from pathlib import Path

from pypdf import PdfReader

from backend.app.api import create_app
from backend.app.copilot.offline import QUESTIONS
from backend.app.settings import Settings
from tests.helpers import asgi_request


async def validate(path: Path, output: Path, memory_gib: float):
    if output.exists():
        raise ValueError("output already exists; choose a fresh validation directory")
    fields = {line.split(":", 1)[0]: int(line.split()[1])
              for line in Path("/proc/meminfo").read_text().splitlines()}
    if fields["MemAvailable"] / 1024**2 < memory_gib + 2:
        raise ValueError("insufficient host memory headroom")
    limit = int(memory_gib * 1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    app = create_app(Settings())
    started = time.perf_counter()
    output.mkdir(parents=True, exist_ok=False)

    async def call(method, route, **kwargs):
        status, data = await asgi_request(app, method, route, timeout=600, **kwargs)
        if status != 200:
            raise ValueError(f"{route}: HTTP {status}")
        return data

    loaded = json.loads(await call("POST", "/api/runs/load", body={"path": str(path.resolve())}))
    token = loaded["session_token"]
    record = {"evidence_id": loaded["evidence_id"], "answers": [], "reports": []}
    print("Prepared evidence loaded and verified", flush=True)
    for question in QUESTIONS:
        ids = None
        for language in ("en", "ne"):
            before = time.perf_counter()
            response = json.loads(await call("POST", "/api/ask", token=token,
                body={"question_id": question, "language": language}))
            answer = response["answer"]
            if answer.get("validation_result") != "passed":
                raise ValueError("answer validation did not pass")
            if ids is not None and ids != answer["claim_ids"]:
                raise ValueError("English/Nepali citation mismatch")
            ids = answer["claim_ids"]
            item = dict(question=question, language=language, claim_count=len(ids),
                        seconds=round(time.perf_counter() - before, 3))
            record["answers"].append(item)
            print(json.dumps(item), flush=True)
    for language in ("en", "ne"):
        before = time.perf_counter()
        pdf = await call("GET", "/api/report", token=token,
                         query=f"language={language}&format=pdf".encode())
        reader = PdfReader(io.BytesIO(pdf))
        if len(reader.pages) != 1 or "OpenStreetMap" not in reader.pages[0].extract_text():
            raise ValueError("PDF page count or credits check failed")
        (output / f"report-{language}.pdf").write_bytes(pdf)
        item = dict(language=language, pages=1, bytes=len(pdf),
                    seconds=round(time.perf_counter() - before, 3))
        record["reports"].append(item)
        print(json.dumps(item), flush=True)
    status, _ = await asgi_request(app, "DELETE", "/api/session", token=token)
    if status != 204:
        raise ValueError("session revocation failed")
    record.update(status="passed", seconds=round(time.perf_counter() - started, 3),
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (output / "validation.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("status", "seconds", "peak_rss_kib")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-memory-gib", type=float, default=3)
    args = parser.parse_args()
    if not 1 <= args.max_memory_gib <= 24:
        parser.error("memory ceiling must be between 1 and 24 GiB")
    asyncio.run(validate(args.run, args.output, args.max_memory_gib))


if __name__ == "__main__":
    main()
