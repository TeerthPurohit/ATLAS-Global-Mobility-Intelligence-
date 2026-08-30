# Overnight Training Progress

Updated periodically. If the PC restarts, read this file first to know
exactly where things stand before doing anything else.

## DONE (as of 16:10 IST, 2026-08-30) -- ETA, congestion, fare all retrained on Kaggle GPU

All three shipped, verified against `tests/test_api.py` (40/40 passing),
committed and pushed to `main`:

- **ETA quantile models** (p10/p50/p90): full 113M rows, T4x2 GPU.
  Coverage 0.7946 (nominal 0.80). The row-count ladder (10M -> 113M) never
  found a break point -- the earlier "coverage collapses at 92M rows" bug
  was NOT a row-count threshold after all; root cause of that original
  failure was never isolated, but this rewrite is clean at every scale
  tested. See `models/eta/eta_gpu_ladder_report.json` for the full scan.
- **Congestion model**: full 113M rows, T4x2 GPU. test_rmse=0.4849,
  matches the original CPU run (0.4850) almost exactly -- faithful
  reproduction, just faster.
- **Fare model**: was stuck on a stale 3-month snapshot (~4.5M rows) from
  before the warehouse grew to ~113M rows -- built a new streaming path
  for it and retrained on the full current corpus. test_rmse rose from
  12.61 to 12.77, which is real (all 4 grid candidates agreed, not a
  bug) -- the fuller/more recent data is honestly harder to predict than
  the old narrow window.

Two real bugs were caught and fixed mid-session (both recorded in Claude's
memory, `project_kaggle_gpu_retrain_2026_08_30.md`, so they don't recur):
1. A Kaggle wrapper script called congestion's `train_and_save()` without
   `sample_rows=None`, silently taking the 300K-row in-memory default
   instead of the full streaming path -- caught by the suspiciously fast
   (~50s) runtime, fixed before those artifacts were ever committed.
2. Fare's new streaming categorical encoding used the wrong numpy dtype
   (int64 instead of int32 for zone ids), which XGBoost bakes into the
   saved model and rejects at predict time if it doesn't match the
   backend's own encoding -- broke `/api/mobility/fare` and 5 tests,
   fixed and reverified against the full test suite before shipping.

**Kaggle GPU accelerator gotcha** (also in memory,
`reference_kaggle_accelerator_enum.md`): `--accelerator` needs the exact
string `NvidiaTeslaT4` (or `NvidiaTeslaP100`/`Tpu1VmV38`) -- plausible
guesses like `gpuT4x1`/`gpuT4x2` are silently ignored and the session
just keeps whatever GPU it last had.

## Prior state (10:40 IST, 2026-08-30) -- GPU-ONLY DECISION, superseded by DONE above

**User decision: CPU training for ETA quantile models is OUT OF BOUNDS.
Kaggle GPU only, from here on.** All local CPU training (the 41%-done
p10 restart, PID 6202/27972; the CPU-30M diagnostic, PID 34220/22448) was
killed on request. Do not restart local CPU training for this model again
-- see memory `project_eta_gpu_only_decision_2026_08_30.md`.

**Run CANCELLED by user at 10:5x IST, 2026-08-30.** `models/eta/train_quantile_eta.py`
gained `train_gpu_row_ladder()` -- trains on GPU (`device="cuda"`) at
increasing row counts (10M, 20M, ..., 113M), stops at the first rung where
measured p10-p90 coverage collapses (the known GPU bug), then retrains the
last confirmed-good rung at full boosting rounds as the real production
model. Pushed to GitHub (commit `ce5b56c`) and pushed as Kaggle kernel
`teerthpurohit/nyc-eta-gpu-row-count-ladder`
(https://www.kaggle.com/code/teerthpurohit/nyc-eta-gpu-row-count-ladder) --
user stopped the run manually on kaggle.com before it produced any result
(status confirmed `CANCEL_ACKNOWLEDGED` via `kaggle kernels status`). No
ladder rungs completed, no new model artifacts produced, nothing to
download. **models/eta/eta_p10/p50/p90_model.json on disk are still the
stale broken-GPU-run artifacts from earlier tonight -- do not trust them.**

The `train_gpu_row_ladder()` code itself is committed and ready to re-run
(`kaggle kernels push -p .scratch_kaggle/`) whenever GPU training should
resume -- nothing about the code caused the stop, it was a user decision
mid-run.

**Relaunched several times chasing the right accelerator flag; CONFIRMED
running on T4x2 as of version 5 (~11:05 IST).** `gpuT4x1`/`gpuT4x2` (my
first guesses) were bogus strings the API silently ignored, silently
falling back to P100 -- user caught this from the Kaggle UI. The real enum
(found in `kaggle` venv's `kagglesdk/kernels/types/kernels_api_service.py`,
`machine_shape` field docstring) is `NvidiaTeslaT4` / `NvidiaTeslaP100` /
`Tpu1VmV38` -- no separate x1/x2 value; `NvidiaTeslaT4` alone gives Kaggle's
standard T4x2 shape. Pushed with `kaggle kernels push -p .scratch_kaggle/
--accelerator NvidiaTeslaT4` (version 5) and added an `nvidia-smi` print at
the top of `.scratch_kaggle/nyc-eta-gpu-ladder.py` to self-verify going
forward -- confirmed via live log: `Tesla T4, 15360 MiB, count 2`.

**RESULT (version 5, ~11:12 IST): ladder did NOT find a GPU accuracy bug --
it hit an OOM kill instead.**

| rung | coverage | mae p10/p50/p90 | elapsed |
|---|---|---|---|
| 10,000,000 | 0.7845 | 6.47/4.49/9.13 | 99s |
| 20,000,000 | 0.7817 | 6.51/4.50/8.97 | 167s |
| 30,000,000 | 0.7832 | 6.52/4.45/8.84 | 252s |
| 40,000,000 | -- | -- | process `Killed` (OOM) while `build_features()` was pulling 40M rows into pandas |

Notes:
- `kaggle kernels logs` crashes on Windows with a `charmap codec` error
  when the log contains Unicode (DuckDB's progress-bar characters) --
  fixed by prefixing `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` on the command.
- All three completed rungs are correct (coverage ~0.78-0.80, matching
  every earlier real-data test at 100K/1.38M/10.25M rows). Zero evidence
  of the "coverage collapses to 0.0055" bug anywhere tested so far --
  this ladder run only ever exercised the in-memory `build_features()`
  path, NOT the external-memory streaming path (`_train_and_save_streaming`
  / `TrainDataIter` + `QuantileDMatrix(iterator)`) that the ORIGINAL broken
  92M-row run actually used. So the original bug is still unexplained --
  it might be the streaming+GPU combination specifically, or something
  else under memory pressure, not a plain row-count threshold.
- Immediate blocker for going past ~30-40M rows on the in-memory path:
  Kaggle instance RAM, not xgboost/GPU. Options to go further: (a) a
  higher-memory Kaggle machine shape if one exists, (b) chunk
  `build_features()`'s pandas materialization, or (c) test the streaming
  iterator path specifically at a moderate row count (e.g. 30-50M) on GPU
  to see if IT is what breaks, isolating that variable from raw scale.
  User has not yet chosen a direction -- ask before picking one.

**Known limitation, told to the user:** `train_gpu_row_ladder()` calls
plain `xgb.train()` in a single process -- it only uses ONE of the two T4
GPUs. Requesting T4x2 does not speed this run up as-is; the second GPU
sits idle unless multi-GPU support (dask-xgboost or similar) is added.
User has not yet said whether that's worth doing.

## Prior state (04:50 IST, 2026-08-30) -- superseded by the GPU-only decision above

**Local p10:** PID 6202, alive. Round 125/300 (41.7%) at 09:35:53, pace ~102s/round this stretch (continuing to slow). 175 rounds still to go for p10 (~5hrs at current pace), then p50 and p90 after that (reuse the shared training matrix, so no repeat of the ~77min data-load cost, just the boosting time).

**GPU threshold investigation (in progress, exploratory):** pushed back on "GPU is fundamentally broken" and re-tested with REAL data at increasing scale. Result: GPU (`device="cuda"`) is actually CORRECT at 100K rows (coverage=0.795), 1.38M rows (coverage=0.800), and 10.25M rows (coverage=0.797) -- properly differentiated MAE at every scale tested. The full 92M-row Kaggle run was broken (coverage=0.0055). So the bug is scale-dependent, not a flat GPU/objective incompatibility as first concluded. A 30M-row test was killed mid-run because it was competing with the primary CPU training for CPU/RAM (data loading for GPU tests is still CPU/IO-bound). Threshold is somewhere between 10.25M and 92M rows -- not yet narrowed further. Waiting on user decision: resume narrowing this (will slow the primary training further) or deprioritize until primary training is done/further along.

**Backend API endpoints:** DONE. 6 FastAPI routes built (`/models/demand`, `/congestion`, `/fare`, `/eta`, `/demand/lstm`, `/demand/transformer`), 69 tests passing, real predictions verified. ETA endpoint will auto-pick-up corrected models once this training run finishes.



**IMPORTANT CORRECTION from earlier tonight:** GPU (`device="cuda"`) was
briefly believed fixed on xgboost 3.3.0 after a small synthetic smoke test
passed on a Kaggle T4. That was wrong. The real full-scale (21M-row) merge
afterward showed the same broken signature as the original 3.2.0/P100 bug:
`measured_p10_p90_coverage=0.0055` (should be ~0.8), MAE nearly identical
(~18) across all three quantiles regardless of alpha. A rigorous 5-way local
comparison at 200K rows proved the CPU code path is correct in every
configuration tested, and isolated the cause to `device="cuda"` itself --
not xgboost version, not the native API, not QuantileDMatrix, not DMatrix
sharing. **`reg:quantileerror` + GPU is broken in both 3.2.0 and 3.3.0. Do
not retry GPU for this objective.** Full details in Claude's memory
(`project_eta_lstm_training_saga_2026_08_30.md`).

**Local (p10/p50/p90) — CPU, restarted from round 0.**
- PID 27972, log `models/eta/logs/train_local_20260830_0420.log`
- Restarting from scratch was unavoidable: the checkpoint/partial-round
  files got wiped when the (broken) GPU results were merged in as if
  correct earlier tonight. Nothing was recoverable from that.
- This is the SAME CPU code that already validated correct at every scale
  tested (200K rows, 5 different API configurations, byte-identical
  results, coverage ~0.785). Trust this path.
- Realistic timeline: back to the original CPU pace, ~48-80s/round,
  trending slower as rounds accumulate. Full three-quantile run is a
  multi-hour job (likely 10+ hours), same as originally estimated before
  any of tonight's GPU detour.
- Round-level checkpointing (every 50 rounds) and progress logging (every
  25 rounds) are still in the code -- if this process dies, it resumes from
  the last checkpoint, not from scratch. Restart command below.

**LSTM** — DONE, unaffected by any of this (PyTorch, not XGBoost quantile
regression). `test_rmse=24.691`, `test_mae=14.136`.

**Backend API work** — in progress in parallel (separate subagent), building
one FastAPI endpoint per model (demand, congestion, fare, eta-range, lstm,
transformer). The eta-range endpoint loads whatever model files currently
exist at request time, so it will automatically pick up the corrected models
once this CPU run finishes -- no code change needed there when that happens.

## How to restart local training if it died

```bash
cd "C:\Users\teert\OneDrive\Documents\Teerth Projects\Uber nyc TLC Dataset"
nohup .venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, '.')
from models.eta.train_quantile_eta import train_and_save
meta = train_and_save(sample_rows=None)
print(meta)
" > models/eta/logs/train_local_RESTART.log 2>&1 &
```
Reads `models/eta/_streaming_checkpoint.json` automatically and resumes from
the last saved round-level checkpoint — do not delete that file, and do not
run any GPU/Kaggle variant of this training in parallel (two processes
racing to write the same `models/eta/eta_*.json` / `_streaming_checkpoint.json`
paths already clobbered progress once tonight).

## Known issues from tonight (don't repeat these)

- **`device="cuda"` + `reg:quantileerror` is broken in xgboost 3.2.0 AND
  3.3.0** — confirmed via full-scale real-data testing, not just a small
  synthetic smoke test (which can pass even when the bug is present at real
  scale/complexity). Do not use GPU for this specific objective again
  without independently re-verifying against a full held-out test set.
- Kaggle's free CPU tier is 4 cores; this machine has 12 — don't move
  CPU-bound work there expecting a speedup.
- A subagent's own spawned background processes can die at the subagent's
  turn boundary in this harness — don't trust "still running" from a
  subagent without a direct check.
- Don't declare an ML result correct from a handful of example predictions
  — always check the aggregate metric (coverage, MAE per quantile) on the
  real held-out test set before trusting it.
- Full saga details: see Claude's memory
  (`project_eta_lstm_training_saga_2026_08_30.md`) for the complete story.

## Once all three quantiles are done (for real this time)

Validate `models/eta/eta_metadata.json` shows meaningfully different `mae`
per quantile (NOT ~18 for all three — that's the broken-GPU signature) and
`prediction_interval_coverage.measured_p10_p90_coverage` reasonably close to
0.8 (not near-zero). The known-good reference numbers from the 200K-row CPU
validation: p10 mae=6.37, p50 mae=4.38, p90 mae=8.61, coverage=0.785.
