# Phase 2 validation report

Phase 2 was validation-only; no held-out test result was read or used for tuning.

The selected validation setting was alpha = 3 and PA3 threshold quantile = 0.5, chosen by scenario-averaged complete-basket-fill gain at matched inventory. Alpha = 3 is the upper edge of the Phase 2 grid and is therefore a boundary result, not an interior optimum. The edge construction retained 1,449,316 default edges; rewired, shuffled-basket, and stale graphs retained 1,449,316, 1,437,590, and 1,161,391 records. All buffers were scaled to total mass 255541.44 units in validation. Matching used the extended target grid and one linear interpolation replay between bracketing targets.

PA1 matched item-fill gain averaged 0.012803; the matched complete-basket gain averaged 0.078820. Mean matched item-fill gains by variant were: C2=0.007549, C3=0.007171, C4=0.020658, C5=0.006931, PA1=0.012803, PA2=0.016105, PA3=-0.001994.

An earlier validation implementation applied the Phase 1 safety multiplier a second time to the incremental graph buffer and was superseded in the run log. The current result uses uninflated residual risk for the incremental buffer and the corrected interpolation-based matching rule.

## Frozen test replay

The single guarded test replay used parent validation hash `677bfb9345b95983bf1fb63fee0e4dd8da3ac63b372530d6c76587aaf5482e44`, alpha = 3, tau = 0.5, the empirical-quantile forecast, 30 stochastic replications, and one deterministic lead-time path per deterministic scenario. Both deterministic-planning and stochastic-planning policy labels were evaluated on that same deterministic path; stochastic scenarios used 30 independent lead-time replications. It produced 3,822 policy rows and 3,822 matched-control rows. The largest absolute matched-inventory gap was 2.23% of basket-aware inventory (mean 1.08%), below the preregistered 5% tolerance.

Relative to the matched independent controls, the mean item-fill gains were C2 0.0202, C3 0.0217, C4 0.0770, C5 0.0045, PA1 0.0359, PA2 0.0673, and PA3 0.0037. Mean complete-basket-fill gains were C2 0.1331, C3 0.1211, C4 0.2404, C5 0.0896, PA1 0.1431, PA2 0.2366, and PA3 −0.0038. The corresponding mean total-cost differences were positive for every variant: 620,637; 613,800; 237,087; 728,798; 528,500; 304,999; and 732,869 cost units, respectively. These are descriptive test-window results, not causal estimates: the high C4 popularity-only performance and the weak PA3 result show that the observed gains cannot be attributed to graph topology alone.

The bootstrap, placebo interval construction, rolling-origin robustness checks, and broader sensitivity analyses remain Phase 3 work. Alpha remains a boundary-selected validation parameter and should not be interpreted as an interior cost optimum.

Files: `phase2_preregistration_addendum.md`, `phase2_validation_config.json`, `phase2_validation_tuning.csv`, `phase2_validation_results.csv`, `phase2_validation_matched.csv`, `phase2_validation_matched_summary.csv`, `phase2_test_config.json`, `phase2_test_results.csv`, `phase2_test_summary.csv`, `phase2_test_matched.csv`, `phase2_test_matched_summary.csv`, `phase_2_test_report.md`, and `run_log.csv`.
