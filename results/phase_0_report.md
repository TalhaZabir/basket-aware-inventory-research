# Phase 0 audit and freeze report

Date: 2026-10-20

## Scope

This report records the audit of the existing results and manuscript before any new test-window evaluation. No new test-window run was launched. Observed transaction and demand data remain separate from simulated inventory, lead-time, shortage, and cost outcomes.

## Files audited

The audit covered `inventory_summary.csv`, `inventory_results_by_replication.csv`, `policy_contrasts_summary.csv`, `inventory_matched_baseline.csv`, `break_even_analysis.csv`, `sensitivity_results.csv`, `rolling_origin_summary.csv`, `forecast_validation_summary.csv`, `forecast_test_summary.csv`, the P0/P1 reports and configurations, `run_experiment.py`, `run_p0_analyses.py`, and the manuscript Markdown sources.

## Defect findings

1. The P4-versus-P2 count is 3 of 12, not 2 of 12. The cheaper scenarios are S03, S06, and S09. The manuscript and P0 report were corrected.

2. Graph sensitivity parameters are wired. `run_p0_analyses.py` passes minimum pair count and top-k to `network_scores`, and the current S05 sensitivity means change with both settings. P3 cost is 3,401,838 at top-k 3, 3,401,171 at top-k 5, and 3,401,950 at top-k 10. The prior repeated table was stale; no code change was required.

3. The S05 P1 values are from different analyses. The primary level table reports 3,427,295 as the mean of the 30-path primary run. The S05 sensitivity analysis reports a mean of 3,432,980 across ten sensitivity replications. They are not the same estimand and are now labelled accordingly.

4. Break-even p/h is scenario- and replication-specific. The current means are 37.79 for P3 versus P1 and 54.12 for P4 versus P2. S01 is a useful check: its actual p/h is 40, while its P3-versus-P1 break-even p/h is 76.49, so P3 remains costlier. The manuscript now reports the definition and this example.

5. Forecast selection wording was incorrect. The executed method generates candidate forecasts from training history, then selects the product-level candidate using validation MAE. Section 4.5 now says this directly.

6. Rolling-origin output already includes total cost and average inventory. The current file contains one earlier window, not the three-window evaluation required for a later robustness phase. Section 5 reports cost, inventory, and service and identifies the result as a one-window check.

7. Figure captions were reordered to match their appearance in Section 5. The detailed per-scenario level table was removed from the main results because the same evidence is retained in Appendix E.

8. `run_log.csv` is missing. This is an open reproducibility defect and must be created before any new test-window run, with configuration hash, date, seed, split, and output paths.

## Freeze status

The existing primary outputs are frozen for audit, but the new preregistration records the primary estimand as pending the user's choice between cost at matched service and service at matched inventory. Until that choice is made, no new test-window run will be treated as confirmatory. The primary contrast remains P4 minus P2; P3 minus P1 is secondary.

## Phase 0 decision

Editorial and traceability corrections pass. The broader research-engineering acceptance tests do not yet pass: the current experiment has 30 stochastic replications, one rolling-origin window, a score-shuffle rather than edge-topology placebo, and no run log. These are recorded as Phase 1–3 work rather than silently presented as completed evidence.
