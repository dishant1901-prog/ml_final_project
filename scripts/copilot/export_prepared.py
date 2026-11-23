"""Export a verified prepared run, including full citation records, without reimport."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import time

from backend.app.copilot.tools import open_context
from backend.app.preparation import prepared_run
from backend.app.reports.exports import export_csv, export_json
from backend.app.reports.facts import build_report
from backend.app.reports.pdf import map_claims, pdf_bytes
from backend.app.settings import Settings


def write_products(facts, output, font):
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}

    def write(name, data):
        path = output / name
        path.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()

    # Write each product before constructing the next one to bound peak memory.
    write('report-facts.json', export_json(facts))
    write('report-claims.csv', export_csv(facts))
    mapped = json.dumps([claim.model_dump(mode='json') for claim in map_claims(facts)],
                        ensure_ascii=False, sort_keys=True, indent=2,
                        allow_nan=False).encode() + b'\n'
    write('map-claims.json', mapped)
    del mapped
    for language in ('en', 'ne'):
        write(f'report-{language}.pdf', pdf_bytes(facts, language, font))
    (output / 'sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
    return hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-memory-gib', type=float, default=6)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output directory')
    if not 3 <= args.max_memory_gib <= 12:
        parser.error('memory ceiling must be between 3 and 12 GiB')
    limit = int(args.max_memory_gib * 1024**3)
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    started = time.monotonic()
    settings = Settings()
    saved = prepared_run(args.run, settings, verify_evidence=False)
    if saved is None:
        raise ValueError('Run must be prepared before export')
    identifier, _ = saved
    context = open_context(identifier, frozenset({identifier}), settings)
    facts = build_report(context, frozenset({identifier}))
    hashes = write_products(facts, args.output, settings.report_font)
    record = dict(status='passed', evidence_id=identifier, claim_count=len(context.claims),
        output=str(args.output), memory_ceiling_gib=args.max_memory_gib,
        sha256=hashes, seconds=round(time.monotonic()-started,3),
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (args.output / 'export-validation.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
