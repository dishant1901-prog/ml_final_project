# Proposed evaluation for future local improvements

Status: **planning only**. No dataset selection, labels, model improvement or
new accuracy claim is recorded here. This is a new local plan, not a recovered
historical protocol. All work remains local; no Git writes are needed to record
content hashes, manifests and fresh output directories.

## Separate software correctness from scientific performance

Synthetic regression fixtures establish known raster, graph, evidence and API
behavior. They cannot measure satellite detection accuracy, operational access
or Nepali language quality. Saved-run reproduction is a third distinct check:
it establishes reproducibility of an existing artifact, not independent accuracy.

## Before selecting an improved method

1. Inventory permitted raw inputs and their provenance: dataset version, event,
   acquisition time/orbit, processing domain, spatial grid, validity and checksums.
2. Recover original research sources if access becomes possible. Otherwise label
   the historical reproduction gaps explicitly; do not fabricate old splits.
3. Define development and fresh test events with geographic/event separation.
   Teesta 2023, Melamchi 2021 and Chamoli 2021 are already consumed tests.
4. Record candidate algorithms, development-only selection criteria, compute
   budget and the intended inference grid before examining new test labels.
5. Keep EMSR927 and other published damage products strictly in checking-only
   paths. Their existing disclosed results cannot become tuning targets while
   retaining an independent-test claim.

## Diagnose misses before adding model complexity

For development events, audit acquisition delays, orbit pairing, preprocessing,
grid alignment, pre-event permanent-water exclusion, slope and observability
masks, pixel size, and minimum mapping unit. Compare detector candidates on the
same supported observations. Analyze water separately from debris/landslide
change; neither raw SAR change nor optical corroboration proves debris.

## Independent labels and metrics

- Specify a window-selection rule and primary/secondary sample roles in advance;
  include positive, negative and unobservable cases. Record selection bias.
- Use independent image interpretation with reviewer IDs, uncertainty masks and
  adjudication where feasible. Do not invent labels where interpretation fails.
- Freeze code/config/input/prediction hashes before accessing the test labels.
  Store immutable local receipts and record every reference access.
- Report per-event TP/FP/FN, precision, recall, IoU/F1, valid coverage, acquisition
  lag and runtime. Undefined ratios remain unavailable, never zero-filled.
- Report pooled and event-level summaries; small event counts do not support
  strong generalization or stable confidence-interval claims.
- Keep the baseline and candidate grids, observation support and matching policy
  comparable. Show both common-support metrics and actual coverage when relevant.

## Infrastructure and connectivity

Use explicit matching units and tolerances for roads, bridges and buildings.
Record unmatched and unassessed features instead of treating them as negatives.
EMSR927 landslide-footprint agreement cannot establish floodwater IoU, building
damage or actual road closure. Closure/connectivity validation requires a suitable
independent source; without one, present only hypothetical graph functionality.

Test known bridge topology, oneway/access tags, destination classes, snapping and
network-boundary sensitivity separately. Baseline-unreachable settlements must
never be counted as newly disconnected. DEM flow checks concern terrain traces,
not depth, timing or inundation extent.

## Delivery gate

Do not promote a candidate based on a visually attractive case-study map alone.
Retain failures, provenance, coverage and limitations. Regenerate reports, deck
and demo only after the selected implementation has reproducible verification.
Changed Nepali wording requires human review before claiming reviewed templates.
Fresh scientific results remain blocked on suitable data and independent labels;
there is no guaranteed accuracy target or calendar completion date at this stage.
