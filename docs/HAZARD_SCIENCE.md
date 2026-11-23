# Hazard-science rationale and validation boundary

This note documents the frozen `hazard-v2` rules in `configs/default.yaml`. It is
not an accuracy certificate. The thresholds were not changed after opening the
EMSR927 reference products on 2 November 2026.

## Physical and algorithmic rationale

The default detector uses calibrated Sentinel-1 gamma0 from same-relative-orbit
pre/post acquisitions. It requires both a dark post-event return (`post_db =
-16`) and a decrease from the multi-date pre-event median (`decrease_db = 3`)
for a new-water candidate. A very dark pre-event return (`permanent_water_db =
-20`) is treated as persistent-water evidence and excluded. A 3×3 majority
filter and a four-pixel (1,600 m² at 20 m) minimum mapping unit suppress isolated
speckle-scale detections.

Terrain is not treated as ordinary missing data. The run combines provider masks
with DEM-derived radar layover/shadow geometry. Slope above 12 degrees excludes a
new-water candidate; height above nearest drainage (HAND) above 20 m is a soft
quality flag rather than a hard flood veto. Multiple Sentinel-1 tracks are
processed separately and fused only after their individual validity masks have
been applied.

`disturbance_db = 5` is a two-sided radar-change screen. Brightening inside the
valley-bottom corridor becomes `possible_debris`; it is not a trained landslide
or debris classifier. Sentinel-2 L2A contributes separate water and
vegetation/bare-ground change evidence only where both dates are clear. Optical
evidence can corroborate a radar signal, but optical-only change never enters
the observed-change or corroborated road-removal scenarios.

These choices follow established operational patterns: multi-temporal
backscatter comparison, terrain and permanent-water masking, spatial filtering,
and HAND constraints. They are consistent with Roth et al. (2025), the 2023
Sentinel-1 flood-method intercomparison, and the large-area operational workflow
of Twele et al. (2019). Consistency with published methods is not evidence that
these fixed thresholds are optimal for every Himalayan valley.

## Frozen settings

| Setting | Value | Role |
|---|---:|---|
| `post_db` | -16 dB | Dark post-event new-water condition |
| `decrease_db` | 3 dB | Minimum pre/post radar decrease |
| `permanent_water_db` | -20 dB | Very-dark pre-event water exclusion |
| `max_slope_deg` | 12° | New-water terrain exclusion |
| `max_hand_m` | 20 m | Valley-bottom quality flag |
| `disturbance_db` | 5 dB | Two-sided radar-change screen |
| `neighborhood_size` | 3 | Majority-filter window |
| minimum mapping unit | 4 pixels / 1,600 m² | Remove isolated detections |
| `mndwi_post`, `mndwi_increase` | 0, 0.20 | Optical water support |
| `ndvi_decrease`, `ndbi_increase` | 0.25, 0.20 | Optical exposed-ground support |

## 2 November 2026 validation

The complete live event run for 26 August 2026 and a pre-event control dated 10
August used the same AOI, detector, thresholds and hazard settings. Every control
observation precedes the event boundary. The broad single-modality scenario was
weakly discriminative: 22 event cutoffs versus 19 control cutoffs. It is therefore
a sensitivity bound, not the headline result.

The stricter radar-plus-optical scenario found 16 corroborated road links and 19
modelled cutoffs in the event run, versus 0 links and 0 cutoffs in the control.
This is event/control discrimination for one AOI; it does not establish damage,
closure, a universal false-positive rate, or safe travel. The optical pair spans
about 50 days, so seasonal and land-use change remain plausible confounders.

Official EMSR927 GRA products were downloaded only after the run was frozen and
kept outside the run and bundle directories. A source scan found no reference
leakage into inference. The fresh evaluator exactly reproduced the retained
AOI01/AOI02 results: pooled landslide positive-area recall 122/4,991 = 0.02444
and affected-transport recall 13/32 = 0.40625. EMSR927 grades landslides, not
floodwater, so water IoU is unavailable. Agreement is low and must remain visible.

Machine-readable records are `data/validation/scientific-validation-v2.json` and
`data/validation/emsr927-live-v2-reproduction.json` in the local working package.

## References

- Roth, F. et al. (2025), multi-event Bayesian Sentinel-1 flood mapping,
  *Science of Remote Sensing* 12, 100210.
  <https://doi.org/10.1016/j.srs.2025.100210>
- *Intercomparison of Sentinel-1 Flood Detection Algorithms* (2023),
  *Remote Sensing* 15(5), 1200. <https://doi.org/10.3390/rs15051200>
- Twele, A. et al. (2019), large-scale operational Sentinel-1 flood detection,
  *Water* 11(4), 786. <https://doi.org/10.3390/w11040786>
