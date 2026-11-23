# Dataset and external-input register

Large or restricted inputs are not stored in Git. `data/` is ignored by design.
Every live run records provider item identifiers, acquisition times, processing
settings and checksums in its manifest.

| Asset | Role | Acquisition | Repository policy |
|---|---|---|---|
| Sentinel-1 GRD / CDSE gamma0 | pre/post radar evidence | Copernicus Data Space Ecosystem | download on demand; never commit |
| Sentinel-2 L2A | optical corroboration | Copernicus Data Space Ecosystem | download on demand; never commit |
| Copernicus DEM GLO-30 | terrain, HAND and flow path | Copernicus Data Space Ecosystem | download on demand; never commit |
| OpenStreetMap historical snapshot | roads, buildings and facilities | ohsome API | store derived small GeoJSON in a run; do not vendor planet data |
| Kuro Siwo | historical UNet training | dataset publisher | external; license and checksum must be accepted/verified |
| Himalayan human labels | once-only independent evaluation | original review workflow | unavailable in this checkout |
| Copernicus EMS EMSR927 | checking-only case-study reference | CEMS archive | external; prohibited from inference or tuning |

## Expected local layout

```text
data/
  datasets/himaroad/<dataset>/
  models/himaroad/unet/<model-version>/model.pt
  outputs/himaroad/<run-id>/
  bundles/<run-id>/
  private/
```

Training manifests must contain file size and SHA256 for every selected file.
`src/himaroad/datasets.py` refuses reference-map paths, Nepal/mountain training
events, duplicated event/region splits, unknown labels, and files outside the
registered dataset root.
