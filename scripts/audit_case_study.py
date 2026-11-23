"""Audit available frozen products without retuning or consuming new test labels."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def audit(bundle, evaluations):
    report = json.loads((bundle / 'report.json').read_text())
    output = {'scope': 'Frozen-product audit; no independent accuracy evaluation or threshold tuning',
              'bundle': str(bundle), 'summary': report.get('summary'), 'rasters': {},
              'evaluations': [], 'limitations': [
                  'Raw historical labels and original evaluation scripts are not supplied here.',
                  'Published damage references are checking-only, never inference inputs.',
                  'Empty water output does not establish absence of flooding.',
                  'Raster positive counts have layer-specific meanings; unknown is not negative.']}
    for name in ('aoi', 'valid', 'flood_extent', 'ephemeral_water', 'permanent_water',
                 'disturbance', 'possible_debris', 'unobservable', 'layover', 'radar_shadow'):
        path = bundle / f'{name}.tif'
        if not path.is_file():
            output['rasters'][name] = {'status': 'unavailable'}
            continue
        with rasterio.open(path) as src:
            valid_count = positive = total = 0
            for _, window in src.block_windows(1):
                values = src.read(1, window=window, masked=True)
                usable = ~np.ma.getmaskarray(values) & np.isfinite(values.data)
                total += values.size
                valid_count += int(usable.sum())
                positive += int((usable & (values.data > 0)).sum())
            output['rasters'][name] = dict(sha256=sha256(path), shape=[src.height, src.width],
                crs=str(src.crs), transform=list(src.transform)[:6], total_pixels=total,
                finite_unmasked_pixels=valid_count, positive_pixels=positive)
    roads = json.loads((bundle / 'roads.geojson').read_text())['features']
    output['road_categories'] = dict(Counter(f['properties'].get('evidence_category', 'unknown') for f in roads))
    output['bridge_links'] = sum(str(f['properties'].get('bridge', '')).lower() not in ('', 'none', 'no', 'false', '0') for f in roads)
    for path in sorted(evaluations.glob(bundle.name + '.AOI*.json')):
        data = json.loads(path.read_text())
        hashes = data.get('source_hashes', {})
        checked = {name: sha256(bundle / name) == expected for name, expected in hashes.items()
                   if (bundle / name).is_file()}
        output['evaluations'].append(dict(file=str(path), sha256=sha256(path),
            available_source_hash_checks=checked,
            missing_source_files=sorted(name for name in hashes if not (bundle / name).is_file()),
            reference_files_available={name: (bundle.parent.parent / name).is_file()
                                       for name in data.get('reference_hashes', {})},
            water=data.get('water'), disturbance=data.get('disturbance'),
            infrastructure={key: value for key, value in data.get('infrastructure', {}).items() if key != 'matches'},
            connectivity=data.get('connectivity'), status=data.get('status'), reason=data.get('reason')))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--evaluations', type=Path, default=Path('results/emsr927'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = audit(args.bundle, args.evaluations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(args.output), 'evaluations': len(output['evaluations']),
        'mismatches': {item['file']: [k for k,v in item['available_source_hash_checks'].items() if not v]
                       for item in output['evaluations']}}))


if __name__ == '__main__':
    main()
