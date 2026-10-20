# Phase 1 validation calibration report

The phase was validation-only; the held-out test window was not read for scoring or tuning.

The validation winner by aggregate WAPE was `empirical_quantile` (MAE 18.5805, WAPE 0.6865, bias -9.2342, 90% coverage 0.8982). Forecast metrics are in `phase1_forecast_validation.csv`; the ladder includes moving averages, seasonal-naive, Croston, SBA, TSB, a prior-year seasonal-ratio forecast, and an empirical-quantile point forecast. The winning point forecast is negatively biased, so it should not be interpreted as calibrated without its separately reported safety-stock adjustment.

Independent service calibration selected the closest realised item-fill target per scenario and policy by multiplying the internal residual scale by one of [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]. The selected multiplier was 6.0 in all 24 scenario-policy rows, so the grid boundary is itself a limitation. Realised item fill was within 0.03 of the nominal critical-fractile target in every row; the maximum absolute gap was 0.0283. The within-three-percentage-point acceptance result was `True` across 24 scenario-policy rows.

The calibration is not a test result. If the acceptance test fails, the failure and its magnitude must be reported and the forecast/policy must not be declared operationally calibrated.

## Frozen test replay

The validation-selected configuration was then replayed once as the primary test analysis. For P4 minus P2 at matched inventory, the mean item-fill difference was 0.002004 with an empirical interval of [0.000744, 0.004254], and the mean complete-basket-fill difference was 0.004349 with interval [0.000881, 0.010015]. The mean cost difference was -6,115 normalized units, with interval [-52,899, 44,749]. These intervals are based on 273 matched paths for the stochastic comparison and are not the Phase 3 bootstrap or 100-replication analysis.

The same frozen test command was inadvertently invoked twice. Both invocations used the same configuration hash; the first is the primary replay and the second is marked `duplicate_invocation_ignored` in `run_log.csv`. The output files were overwritten by the second invocation, so the second is not independent evidence. The execution-control defect has now been fixed: `run_phase1_test.py` refuses to run when a primary replay for the frozen Phase 1 test exists. The original clean-run gate cannot be retroactively restored, so this remains a documented execution exception rather than a second evidence set. No further test-window run is permitted under this configuration.

Files: `phase1_forecast_validation.csv`, `phase1_policy_validation_calibration.csv`, `phase1_validation_config.json`, `phase1_forecast_test.csv`, `phase1_inventory_summary.csv`, `phase1_inventory_results_by_replication.csv`, `phase1_inventory_matched.csv`, `phase1_inventory_matched_summary.csv`, and `run_log.csv`.
