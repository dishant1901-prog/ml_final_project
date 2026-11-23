# Model checkpoint register

## Registered historical checkpoint

| Field | Value |
|---|---|
| Model | `unet-kuro-v2-w32-c4` |
| Architecture | UNet, four channels, width 32, depth 4 |
| Preprocessing | `s1-db-four-channel-v2` |
| Expected path | `data/models/himaroad/unet/unet-kuro-v2-w32-c4/model.pt` |
| Expected SHA256 | `3ed60130587f4c9562653d4cd9b389e41e4df21030d90eb85ea2d33f7a7098e5` |
| Operating threshold | 0.57 (development calibrated) |
| Temperature | 1.4940904 (development calibrated) |
| License/distribution | not established in this checkout; do not redistribute |

The checkpoint is **not present locally or in the public repository**, and no
download URL is known. The frozen v2 split file, protocol document, source labels
and complete historical training entry point are also absent. Therefore this
submission does not claim that the historical training run was reproduced.

`src/himaroad/unet.py` will reject a missing file, a hash mismatch, incompatible
preprocessing, incomplete metadata, a synthetic checkpoint without explicit
permission, or deployment tiling that differs from the calibrated checkpoint.
The production showcase uses the deterministic rule detector unless an authentic
registered checkpoint is supplied.

No new fine-tuned checkpoint is included. Training or calibration without the
frozen split, labels and provenance would make the reported score scientifically
invalid and is deliberately refused.
