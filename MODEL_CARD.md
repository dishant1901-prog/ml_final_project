# Existing UNet model: documented identity and limits

This card summarizes the shipped configuration and the course report. Historical
training and evaluation results below have **not** been independently reproduced
in the current local environment. No new model has been trained.

## Identity

- Model version: `unet-kuro-v2-w32-c4`.
- Architecture: UNet, four input channels (pre/post VV/VH), base width 32, depth 4.
- Preprocessing: `s1-db-four-channel-v2`; calibrated CDSE gamma0 on a north-up
  20 m UTM grid. Generic radar products must not be assumed interchangeable.
- Inference tiles: 128 pixels, overlap 16.
- Calibration: development-only temperature approximately 1.4940904 and operating
  threshold 0.57; the checkpoint metadata is authoritative at inference.
- Configured checkpoint SHA256:
  `3ed60130587f4c9562653d4cd9b389e41e4df21030d90eb85ea2d33f7a7098e5`.
- Configuration: `configs/model_unet.yaml`. Weights are external release data.

## Historical evidence

The project report records training from scratch on Kuro Siwo: 310 training chips
from Houston, Togo and Peru, and 134 development chips from Larkana and Illinois.
It records selection among four variants, then calibration on development data.

| Method | Development precision | Recall | IoU | F1 |
|---|---:|---:|---:|---:|
| Rule baseline | 0.8835 | 0.6629 | 0.6096 | 0.7575 |
| Selected UNet | 0.8008 | 0.9457 | 0.7656 | 0.8672 |

Development-selected scores are not independent generalization evidence.

The once-only blind Himalayan evaluation covered valley-enriched windows from
Teesta 2023, Melamchi 2021 and Chamoli 2021. The report records **zero of 1,298
labelled new-water pixels detected by the UNet**: recall and IoU zero, precision
undefined because there were no positive predictions. The baseline detected 24.
Reviewer agreement and the small, selected windows further limit interpretation.
Those test events are consumed; they must not be presented as a fresh test after
further development.

For the frozen Trishuli runs, the UNet water candidate was removed by later
filtering. The scored baseline and UNet outcomes are identical. Disturbance and
possible debris remain rule-derived; this model does not provide a validated
debris classifier.

## Intended use

Experimental evidence for an educational flood-screening prototype. Predictions
do not establish damage, road closure, water depth, casualties or safe travel.
Unknown observations must remain unknown. The situation-report copilot is an
evidence-grounded interface; a failed segmentation transfer must not be hidden
behind its citation-integrity checks.

## Reproduction gaps

The consolidated checkout does not contain the original training scripts, split
configuration, complete protocol, test registry or frozen human-label package.
The original pinned research repository returned GitHub 404 through the current
connection. Its visibility/existence has not otherwise been established. This
card is not a substitute for those missing artifacts or an invented protocol.

Any new scientific iteration should use a separately identified development
dataset and fresh held-out evaluation, following `docs/EVALUATION_PLAN.md`.
