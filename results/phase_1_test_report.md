# Phase 1 frozen test report

The validation-selected empirical-quantile forecast and safety multiplier 6.0 were frozen before this test-window replay. No test result was used to tune the configuration.

The test forecast row is in `phase1_forecast_test.csv`. The four-policy level results are in `phase1_inventory_summary.csv`; replication rows are in `phase1_inventory_results_by_replication.csv`.

For the primary P4-versus-P2 matched-inventory comparison, the mean item-fill difference was 0.002004 with a percentile interval [0.000744, 0.004254], and the mean complete-basket-fill difference was 0.004349 with interval [0.000881, 0.010015].

These are Phase 1 results under 30 stochastic replications and one deterministic path per deterministic scenario. They are not the final uncertainty analysis specified for Phase 3. The frozen test command was invoked twice accidentally under the same configuration hash; only the first invocation is the primary replay, and the duplicate is marked and excluded in `run_log.csv`. The output files were overwritten by the second invocation, so it is not counted as independent evidence. The script now refuses any further replay under this configuration; the incident remains an execution exception, not an additional evidence set.

Files: `phase1_test_config.json`, `phase1_forecast_test.csv`, `phase1_inventory_summary.csv`, `phase1_inventory_results_by_replication.csv`, `phase1_inventory_matched.csv`, `phase1_inventory_matched_summary.csv`, and `run_log.csv`.
