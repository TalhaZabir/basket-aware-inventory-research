# P0 robustness analysis report

## Evidence boundary

The UCI transaction, basket, weekly-demand, and training-period graph files are observed or directly derived. Inventory, lead times, costs, stockouts, unmet demand, and policy outcomes are synthetic or simulated. M5 remains a separate forecasting benchmark.

## Primary cost-responsive run

The primary policies use the critical fractile `p/(p+h)`, where `p` is the shortage penalty and `h` is the holding cost. The product universe contains 2,731 products, the test window contains 14 weeks, and stochastic scenarios use 30 paired replications. The alpha grid was extended to `[0, 0.25, 0.5, 1, 1.5, 2, 3]`; matched-inventory validation selected the interior value alpha = 1.5, subject to a one-percentage-point complete-basket-fill improvement over alpha zero.

P3 was cheaper than P1 in 7 of 12 unadjusted scenario contrasts; P4 was cheaper than P2 in 3 of 12 (S03, S06, and S09). Basket-aware policies improved pooled item and complete-basket service, but carried more average inventory.

## Inventory-matched independent baseline

The independent service target was selected from 0.80, 0.85, 0.90, 0.95, 0.975, 0.99, and 0.995 to minimize the difference in average inventory from the basket-aware policy. Across 93 matched replication paths per comparison, P3 cost 22,620 normalized units more than matched P1 on average while improving item fill by 1.01 percentage points and complete-basket fill by 1.90 points. P4 cost 46,681 more than matched P2 and improved item fill by 0.19 points and complete-basket fill by 0.21 points. The 93 paths comprise three deterministic scenarios with one path and nine stochastic scenarios with ten paths; they are not 93 independent stochastic replications.

## Frontier and placebo

The frontier covers service targets 0.80 through 0.99 and alpha values 0 through 3.0 across representative deterministic, low-variance, high-variance, and right-skewed scenarios. The dependency-free frontier plot is `frontier_plot.svg`.

The placebo randomly shuffles the product-level basket-score vector using seed 20261020 while preserving its marginal distribution. It does not rewire edges and therefore does not test graph topology. The paired comparison contains 93 paths per policy. P3 real-minus-placebo cost was -493 (95% interval -6,623 to 8,834) and P4 was -5,626 (-13,923 to 2,372); the corresponding item-fill differences were approximately zero. The similarity indicates that the tested score-only policy may be responding mainly to extra buffer magnitude rather than graph topology. Full intervals are in `placebo_comparison_summary.csv`.

## Cost break-even

The analytical break-even rule compares the non-shortage cost premium with the reduction in unmet units. The observed scenario p/h ratios averaged 35.56. The mean break-even p/h was 37.79 for P3 versus P1 and 54.12 for P4 versus P2, computed row-by-row across scenario and replication paths. These are not universal thresholds: S01 has an actual p/h of 40, while its P3-versus-P1 break-even p/h is 76.49, so P3 remains more expensive there. The scenario-specific rule shows why an unadjusted cost advantage can disappear after inventory matching: the service improvement must be worth the added holding and ordering exposure.

## Sensitivity and RQ3

The sensitivity file covers minimum pair thresholds, top-k graph density, product-universe support thresholds, service-target frontiers, lost sales versus backorders, all-units versus all-distinct-items basket definitions, holding-cost variation, basket-concentration strata, and edge-stability strata.

In the S05 concentration split, P3 segment item fill was 0.824 for high-concentration products and 0.840 for low-concentration products, compared with 0.775 and 0.814 for P1. In the edge-stability split, P3 improved segment item fill over P1 by about 3.5 percentage points for high-stability products and 4.0 points for low-stability products. The present score-only policy therefore suggests a concentration gradient but no larger stable-edge benefit. Under holding-cost variation, P3 was more expensive than P1 in S04 by about 66,928 and cheaper in S06 by about 205,740, conditional on the synthetic cost pairs.

## Audit findings and open items

- The graph minimum-pair and top-k parameters are wired through `run_p0_analyses.py` into `network_scores`. Their S05 sensitivity means are not identical: P3 cost is 3,401,838 at top-k 3, 3,401,171 at top-k 5, and 3,401,950 at top-k 10. The old repeated table was stale, not evidence of a no-effect-by-construction implementation.
- The S05 primary level value for P1 (3,427,295) is the mean of the 30-path primary run. The sensitivity value (3,432,980) is the mean of ten S05 sensitivity replications under a separate analysis configuration; these estimands are not interchangeable. Both are retained with their source labels.
- Section 4.5 wording was corrected to say that validation forecasts were generated from training history and validation MAE was used for model selection.
- `rolling_origin_summary.csv` already contains cost and inventory. The current check has one earlier window, with policy means ranging from cost 2,072,599 and inventory 244,587 (P1) to cost 2,183,818 and inventory 318,241 (P4); the manuscript now reports these fields and identifies the check as a single window.
- Figure order and the duplicated per-scenario table in the main results are being corrected; the full per-scenario table remains in Appendix E.
- `run_log.csv` is absent. It must be created and populated with configuration hashes, dates, and seeds before any new test-window run.

Phase 0 is an audit/editorial pass, not a new test-window analysis. The selected-per-product test row is present in `forecast_test_summary.csv` (MAE 28.5766, WAPE 0.7352, bias -1.8986), but it is not evidence that the realised inventory service target was met.

## Files

- `frontier_results.csv` and `frontier_plot.svg`
- `placebo_results.csv` and `placebo_summary.csv`
- `inventory_matched_baseline.csv`
- `break_even_analysis.csv`
- `sensitivity_results.csv`
- `p0_analysis_config.json`
