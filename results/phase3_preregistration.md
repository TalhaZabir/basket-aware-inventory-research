# Phase 3 preregistration addendum

This addendum freezes the precision and external-validity extension before the Phase 3 test replay.

## Primary analysis

The primary estimand is item-fill and complete-basket-fill difference at matched average inventory. The primary policy is PA1 partner protection, compared with C1 independent control and C4 popularity-only control. PA2, PA3, C2, C3, and C5 are secondary controls. The alpha is selected on validation only from `[0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 4.00, 5.00]` by the lowest matched-cost difference among values that improve validation complete-basket fill by at least five percentage points over alpha zero. The selected value must be interior to the grid; otherwise the grid is extended before any test result is read.

Matching uses a 1% relative average-inventory band. A candidate independent service target is accepted only when `abs(I_ind - I_PA) / I_PA <= 0.01`; if no grid target satisfies the band, one interpolation replay is permitted. The test replay is not used to tune alpha, matching, graph, or controls.

## Uncertainty and robustness

Stochastic scenarios use 100 common-random-number replications. Deterministic scenarios use one fixed lead-time path and are shown separately. Test-week bootstrap uses 1,000 resamples per scenario; a second basket-level bootstrap uses 1,000 resamples per scenario. Three rolling-origin windows re-estimate the universe, forecast, graph, and alpha on their own training/validation periods.

Primary paired contrasts are PA1 minus C1, PA1 minus C4, and PA1 minus each placebo C2/C3/C5. Intervals are percentile intervals over the 100 replications and bootstrap intervals over the correctly pooled cluster-resampled draws; scenario-level intervals are reported separately. The graph-on-top-of-popularity test is positive only if PA1 beats C4 on the primary service outcome with an interval excluding zero and the result is not explained by the paired inventory gap.

## External dataset

The second dataset is dunnhumby The Complete Journey, downloaded from the documented public release mirror under DbCL-1.0, with source attribution and provenance recorded. The external replay uses the same chronological pipeline and policy definitions but reports the reduced universe and source-specific coverage explicitly.
