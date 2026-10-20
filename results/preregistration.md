# Preregistration for the next test-window analysis

Status: frozen after user decision

Date drafted: 2026-10-20

## Evidence boundary

UCI transaction and demand fields are observed or directly derived. Inventory, lead times, supplier performance, stockouts, unmet demand, and cost parameters are simulated. The next analysis will not describe simulated values as historical retailer outcomes.

## Primary estimand

The primary estimand is **service at matched inventory**: compare item fill and complete-basket fill after matching the independent control's average inventory to the basket-aware policy. The primary summary is the paired difference in item fill and complete-basket fill for P4 minus P2; P3 minus P1 is secondary. Secondary outcomes are total cost, average inventory, unmet units, and stockout frequency. Cost at matched service is not the primary estimand.

## Contrasts and hypotheses

The primary policy contrast is P4 minus P2, comparing stochastic-lead-time basket-aware and independent policies under the same forecast, seeds, lead-time draws, and scenario. P3 minus P1 is secondary for deterministic lead time. The confirmatory hypothesis is that the basket-aware policy improves the selected primary estimand relative to the matched independent control. A null or adverse result will be reported without retuning toward a preferred direction.

The policy will also be compared with edge-aware and popularity-only controls in the later control phase. A graph effect will not be claimed unless it survives the pre-registered matched-inventory comparison and the placebo/control comparisons.

## Data and split

The current frozen split is training through 2011-06-27, validation from 2011-07-04 through 2011-08-29, and test from 2011-09-05 through 2011-12-05. Forecast, universe, graph, and policy tuning use training and validation only. The test window is evaluated once per frozen configuration. A future rolling-origin extension will define additional windows before looking at their outcomes.

## Forecast and policy settings

The Phase 1 forecast ladder is fixed before the next test-window evaluation: recent-four-week mean, recent-eight-week mean, seasonal-naive demand from 52 weeks earlier, Croston, SBA, TSB, a prior-year seasonal-ratio forecast, and an empirical-quantile forecast whose point prediction is the historical median. Croston/SBA/TSB smoothing constants are fixed at 0.1; the seasonal-ratio is clipped to [0.25, 4]; the empirical distribution uses the most recent 26 training observations. Candidate selection and any bias correction use training-only rolling-origin pseudo-validation; the held-out validation window is used to select the final candidate and safety-stock calibration, never the test window. Forecast evaluation reports MAE, WAPE, bias, 90% coverage and width, pinball loss at 0.5/0.9/0.95/0.975, and an empirical CRPS-style score.

The current basket score is the mean of the top five directed training-period conditional co-purchase probabilities, with alpha candidates 0, 0.25, 0.5, 1, 1.5, 2, and 3. Alpha 1.5 is the existing validation-selected primary value. Any new forecast or pair-aware policy grid must be written here, hashed, and logged before test evaluation.

The primary cost formula is holding cost plus shortage penalty plus normalized ordering cost plus normalized purchase cost. The current replay uses weekly review, two-week protection, lost sales as the primary stockout treatment, and backorders as a sensitivity condition. Partial item fills consume available stock; mixed baskets are projected onto the in-universe products, while baskets with no in-universe products are omitted.

For Phase 1 calibration, the independent policy uses the scenario critical-fractile target and multiplies the internally estimated residual scale by one of the fixed safety-stock multipliers [0.5, 1, 1.5, 2, 3, 4, 6]. The multiplier is chosen using validation-only realised item fill, selecting the closest value to the nominal target. The acceptance rule is realised validation item fill within 0.03 of the nominal target for the independent policy, or an explicit quantified failure explanation if the rule is not met.

### Phase 1 freeze addendum

The validation-only run froze `empirical_quantile` as the test forecast by lowest aggregate validation WAPE and froze safety multiplier 6.0 because it was the closest value to the nominal target on every scenario-policy calibration row. The validation configuration hash is `5f8b31cc1ff8384ee8f9f02beb559e82055601c8093c4827d1a7061a12133bd6`. The held-out test rerun may now use this configuration; no test metric may be used to revise the forecast, multiplier, alpha, or policy parameters.

## Replication and uncertainty plan

The existing run uses one deterministic path and 30 paired stochastic paths per scenario. The next analysis must log every run in `run_log.csv`. The planned extension is at least 100 common-random-number stochastic replications, block bootstrap over test weeks and baskets with at least 1,000 resamples, and scenario-clustered pooled estimates. Deterministic scenarios will not be counted as independent stochastic replications.

## Decision rule

Benefit will be established only if the pre-registered paired interval excludes zero in the beneficial direction for P4 minus P2 on the matched-inventory service estimand and the result is not contradicted by the matched-inventory control and placebo/control checks. Otherwise the conclusion will be a null or boundary-condition result. No decision will be based only on an unadjusted pooled cost difference across scenarios with different h and p.

## Run-control requirement

Before the next test-window run, create `results/run_log.csv` with configuration hash, source revision, date/time, random seed, split dates, scenario, policy, replication, and output paths. Record failures and excluded runs as well as successful runs.

## Execution exception

The frozen Phase 1 test command was invoked twice under the same configuration hash. The first invocation is the primary replay; the second is recorded as `duplicate_invocation_ignored` in `run_log.csv` and is not counted as an independent replication. No additional test-window run is permitted under this configuration.
