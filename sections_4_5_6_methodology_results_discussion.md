# 4. Research methodology

## 4.1 Research design and analytical logic

This chronological simulation compares independent item-level replenishment with a basket-aware policy under demand and supplier lead-time uncertainty. Both policies share forecasts, universe, review schedule, costs, initial conditions, seeds, and lead-time draws; only the use of training-period basket relationships differs. UCI identifies completed baskets but not stock, purchase orders, supplier delivery, stockouts, lost sales, or inventory costs, so those quantities are simulation assumptions.

The study follows four stages: (1) construct clean transaction-line and invoice-basket data; (2) estimate product forecasts and training-period co-purchase features; (3) replay held-out demand through competing policies under controlled lead-time and cost scenarios; and (4) evaluate forecast accuracy, inventory cost, item service, and complete-basket fulfilment together.

## 4.2 Data sources and units of analysis

### Primary empirical source: UCI Online Retail II

The primary source is Online Retail II from the UCI Machine Learning Repository (Chen, 2019, [DOI](https://doi.org/10.24432/C5CG6D)). It contains transaction-line records from a UK-based, registered, non-store online retailer covering 1 December 2009 to 9 December 2011. The source fields include invoice identifier, stock code, product description, quantity, transaction timestamp, unit price, customer identifier, and country. The UCI landing page currently displays 2012 in its citation widget, but records the dataset donation in 2019; this manuscript uses 2019 as the repository release year and retains the DOI as the stable identifier.

The main units of analysis are:

- a transaction line, identified by invoice, product, timestamp, quantity, and unit price;
- an invoice-level basket, identified by `invoice_id`;
- a product-week observation, identified by `stock_code` and Monday-start `week_start`; and
- an unordered product pair, identified by `stock_code_a` and `stock_code_b`.

The validated package contains 1,067,371 raw UCI rows. After cleaning, it contains 1,036,877 retained positive merchandise lines, 39,516 retained invoice baskets, and 4,707 retained products. The dense weekly panel contains 498,942 product-week rows. These counts describe the prepared data and are not inventory or demand estimates for transactions that were never completed.

The retained basket-size distribution has a mean of 26.2 lines, median 16, interquartile range 6 to 29, and a long upper tail, consistent with wholesale-type buying but without a reliable segment label. Customer IDs are missing for 22.6% of retained lines overall and 20.9% of test-period lines, so customer panels are not required.

Over 83 training weeks, the 2,731-product universe has median ADI 1.77 weeks and median positive-demand CV-squared 1.40; every series has ADI above one and 66.2% have CV-squared above one. The panel is therefore intermittent and heterogeneous.

The training-only graph contains 1,576,291 unordered pairs among 3,279 supported products, or 29.3% of 5,374,281 possible pairs. Its weights are frozen scores, not evidence of causal complementarity.

Coverage of the executed test universe is reported explicitly. Of 7,192 held-out test baskets, 6,810 (94.7%) contain at least one product in the 2,731-product universe and therefore enter the basket proxy. Of 211,207 test transaction lines, 144,929 (68.6%) are in-universe, representing 1,486,135 of 2,197,903 units (67.6%). The test window contains 3,167 distinct product codes; 1,036 are outside the executed universe, while 600 universe products have no positive test-week demand. The lower line and unit coverage than basket coverage reflects the fact that many large baskets contain a mixture of supported and excluded product codes; mixed baskets are projected onto their supported items as described in Section 4.8.

### Complementary benchmark: M5 Forecasting Accuracy

The M5 files are a separate forecasting benchmark from the public [Zenodo release](https://doi.org/10.5281/zenodo.10203108), with the [Kaggle competition page](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data) in the manifest. Makridakis et al. (2022) report the competition results. M5 is not joined to UCI because its retailer, identifiers, periods, and units differ.

UCI remains primary because it provides invoice baskets; M5 does not provide the customer baskets or operational fields needed for this inventory replay.

### External basket validation: dunnhumby Complete Journey

The second basket source is the documented dunnhumby Complete Journey release, covering approximately 2.6 million transaction lines for 2,500 households over 102 weeks. The project uses the public release mirror and records the source URL, release URL, DbCL-1.0 statement, SHA-256 checksum, schema, and cleaning counts in `data/processed/dunnhumby/dunnhumby_source_profile.json`. It is prepared and replayed separately, not row-joined to UCI. The corrected external replay uses a top-1,000 product universe selected by training active-week support and training volume; weeks 1–78 are training, 79–90 validation, and 91–102 test. It uses one-week lead time, normalized costs, alpha = 1.5, and the same graph/popularity buffer logic. A stock-tightening factor of 0.01 makes item fill non-degenerate; the original top-300/full-stock result is retained as an audit comparison.

## 4.3 Cleaning and preparation

The two UCI workbook sheets were concatenated, field names normalized, identifiers retained as strings, timestamps parsed, and quantities/prices converted to numeric values. Line value equals quantity multiplied by unit price.

The retained transaction-line rule keeps a line only when invoice, stock code, description, and timestamp are present; the invoice does not begin with “C”; quantity and unit price are both positive; and the stock code begins with a numeric character.

The rule removes cancellations/returns, non-positive quantities or prices, missing keys, and obvious service codes. It defines a conservative analytical universe, not a claim that every numeric stock code is homogeneous; counts and source row IDs remain auditable.

Retained lines sharing `invoice_id` form a basket with timestamp, customer/country where present, line count, distinct products, total units, and value. Duplicate product lines remain quantities in the transaction table; co-purchase construction deduplicates products so each pair counts once per basket.

The weekly panel uses Monday-start weeks and expands product-week combinations over the observed universe. No-sale weeks receive zero units, transactions, and revenue, while average price remains missing rather than zero.

## 4.4 Chronological split and leakage control

The chronological split is training (1 December 2009 to 30 June 2011), validation (1 July to 31 August 2011), and test (1 September 2011 to the final cleaned observation).

These dates were frozen before model selection. Product inclusion, filters, graph weights, forecast parameters, and policy parameters use training data only; validation selects models and policies, and the test window is used once.

The co-purchase file uses baskets through 30 June 2011 and contains 3,279 supported products and 1,576,291 pairs. The inventory universe is the 2,731 products with at least 20 positive training weeks. Test-period baskets are used in neither construction.

For M5, models are fit through `d_1913` and evaluated on the next 28 daily observations; tuning is independent of the UCI experiment.

## 4.5 Demand forecasting

The forecast target is weekly unit demand for each retained UCI product. Forecast and inventory evaluation are reported separately; forecast accuracy does not automatically imply policy performance.

The executed stage used three transparent candidates per product and review week: recent-four-week mean, recent-eight-week mean, and seasonal-naive demand from 52 weeks earlier, with recent-eight as fallback. Croston, TSB, count, and rolling-bootstrap forecasts were not run.

Candidate forecasts were generated from training history, and the candidate with the lowest product-level validation MAE was selected on the validation window; each product therefore used a recent-four-week mean, recent-eight-week mean, or seasonal-naive forecast.

For each product and review week, the executed output included a point forecast and a residual standard deviation estimated from selected-model validation errors, floored at 0.25 units. The simulator used that residual dispersion in a nominal 90% protection band with z = 1.645. This is a safety-stock approximation, not a fully calibrated probabilistic forecast. The primary policies use the same selected forecast and residual dispersion; basket information enters through the replenishment buffer, not through a privileged basket-aware forecast.

Forecast metrics are MAE for absolute weekly error, WAPE for volume-weighted error, forecast bias (mean forecast minus mean demand), empirical coverage of the nominal interval, and mean interval width.

For M5, the available sample benchmark is reported only as an appendix pipeline check. It is not used to claim inventory performance.

## 4.6 Replenishment policies

All policies use weekly periodic review. At review week t, inventory position is on-hand stock plus on-order stock minus backorders. The order quantity is the nonnegative ceiling of target stock minus inventory position. The independent base target is two weeks of forecast demand plus z times the calibrated residual scale times the square root of two, where z is the standard-normal quantile for the scenario critical-fractile target. The executed Phase 3 replay used the frozen six-fold safety calibration of the residual scale; this is why its absolute inventory levels are larger than those in the earlier four-policy pilot, which used the unmultiplied residual scale. The primary Phase 3 estimand is service at matched average inventory.

### Edge-level basket-aware policies

PA1 is the partner-protection policy actually used in the primary replay. For each product (i), training-only directed edges identify at most five supported partners (j). The incremental item buffer is a weighted sum of partner risk, using conditional co-purchase probability, pair count, and partner residual scale (1.645 sigma_j). The buffer is computed once from the training graph, scaled to a common total mass across graph and control variants, and applied across the full weekly review horizon as S^{PA1}_{i,t}=S^{ind}_{i,t}+alpha b_i. Validation used the alpha grid [0.10, 0.25, 0.50, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]. Alpha = 1.5 was selected because it was an interior value meeting the frozen service-gain rule and had the lowest matched-cost result among eligible interior values. The primary replay uses alpha = 1.5, not the earlier boundary value 3.0.

PA2 allocates the same total buffer mass using a greedy basket-coverage score estimated from training baskets. Its objective rewards buffers that cover many distinct basket requirements; it is budget constrained so a service gain cannot be explained by an unconstrained increase in total buffer mass.

PA3 raises targets only for products whose PA1 score exceeds the validation-selected threshold (tau = 0.50), then rescales the resulting buffer to the same total mass. It is a joint-service screening rule, not an unrestricted graph multiplier.

The controls are C1, the independent baseline matched to PA1 or C4 within 1% of average inventory; C2, a degree-preserving edge rewire; C3, a graph built after training-basket label shuffling; C4, a popularity-only buffer with no pair information; and C5, a stale graph built from an earlier training window. All graph statistics are training-only. P1 and P3 plan on seven days in stochastic-lead-time worlds; P2 and P4 include the stochastic lead-time term, and all actual receipts follow the sampled scenario draws. The primary like-for-like test is PA1 versus C4 at matched inventory; PA1 versus C1 is the secondary independent-control contrast. PA1 versus C2/C3/C5 is a paired common-target placebo comparison, because a placebo is intended to test the graph signal rather than add another independent-target calibration.

The policy labels and controls are:

| Policy | Information used | Constraint or purpose |
|---|---|---|
| PA1 | Directed training-only partner edges | Partner-protection buffer |
| PA2 | Training-only basket coverage | Same total buffer mass as PA1 |
| PA3 | PA1 score threshold | Thresholded joint-service buffer |
| C1 | No basket graph | Independent policy at matched inventory |
| C2/C3 | Rewired or shuffled graph | Edge/topology placebos |
| C4/C5 | Popularity-only or stale graph | Hub and stability controls |

## 4.7 Cost and lead-time assumptions

No UCI or M5 field is treated as an observed procurement cost or supplier lead time. The supplied scenario table contains synthetic assumptions only. It varies holding cost, shortage penalty, and lead-time family while keeping the scenario identity and random seed explicit.

The 12 scenarios cross four lead-time families (deterministic seven-day, low-variance normal, high-variance normal, and right-skewed discrete over 2–21 days) with (h,p) pairs (0.05, 2.0), (0.15, 5.0), and (0.30, 10.0). Ordering and purchase costs are normalized to 1.0, and each row has its own seed. The cost-responsive target is `p/(p+h)`; low/high variance use clipped rounded normal draws and the skewed family uses a truncated exponential. All assumptions are recorded in `results/experiment_config.json`.

The primary simulated total cost is the sum over review weeks of holding cost, shortage penalty, fixed ordering cost, and unit purchase cost: C = sum over t of [h times ending on-hand units + p times unmet units + K times the indicator that a positive order is placed + c times ordered units].

Here `OH_end` is end-of-week positive on-hand inventory, `U` is unmet weekly demand, `Q_t` is total quantity ordered in review week `t`, `q_i,t` is the product quantity ordered, `K = 1` is a normalized fixed cost per review batch with at least one order, and `c = 1` is normalized acquisition cost per ordered unit. Holding cost is charged once per simulated week on ending on-hand units; shortage penalty is charged once per unmet demand unit in that weekly aggregate; neither `h` nor `p` is charged per transaction line. The unit purchase component is included in reported total cost and is identical across policies apart from the quantity ordered. These normalized parameters make the cost comparison transparent and avoid presenting synthetic values as retailer accounting data. The three `(h,p)` pairs vary carrying-cost versus shortage emphasis; they are sensitivity scenarios rather than estimates.

## 4.8 Inventory simulation and demand replay

The simulation uses weekly demand and observed held-out baskets. At each Monday review, receipts are posted, orders are placed, the basket proxy is evaluated against beginning-of-demand stock, and aggregate weekly demand is fulfilled. Fulfilled units consume stock; residual demand is unmet under the primary lost-sales rule, with backorder as a sensitivity condition.

The replay is an event-time approximation: baskets in a week share the same pre-demand on-hand state, while item fulfilment uses the aggregate weekly demand vector. Thus partial fills consume stock for item metrics, but the basket proxy is not a basket-by-basket order history.

Products outside the universe are removed before replay. Baskets with no in-universe product are omitted; mixed baskets are projected onto their in-universe products. The metric therefore describes in-universe observed-basket service.

Receipts follow each order's scenario lead-time draw and are posted before same-day ordering. There is no warm-up or pre-test pipeline: all policies start with the same independent deterministic target based on the first test forecast, two-week coverage, and residual dispersion; the initial target excludes the basket buffer.

Common random numbers are used across policies. All twelve scenarios are replayed with 120 paired replications; deterministic scenarios repeat the identical demand path so their intervals are degenerate. At each replication, the independent control is selected from the frozen target grid and, if necessary, one linear interpolation is attempted; every accepted comparison is below the 1% band. Demand and baskets remain fixed. The primary uncertainty analysis uses 1,000 paired resamples over replications and test weeks; the rolling-origin check repeats the analysis over three chronological windows.

## 4.9 Evaluation protocol and uncertainty estimates

Inventory outcomes are total cost and components, average and peak inventory, item fill, the complete-basket proxy, stockouts, unmet units, order activity, and the applied service target.

The item-level unit fill rate is fulfilled units divided by demanded units, equivalently one minus unmet units divided by demanded units: FR_item = sum(F_i,t) / sum(D_i,t) = 1 − sum(U_i,t) / sum(D_i,t).

The complete-basket fulfilment proxy is the proportion of held-out observed baskets for which all requested product quantities are available at the demand event. It is a proxy for customer-order service, not a measure of all customer demand, because failed or abandoned baskets are not observed in the UCI data.

Effects are paired within scenario and seed. PA1 minus C4 is the primary like-for-like graph-on-top-of-popularity contrast; PA1 minus C1 is the secondary inventory-matched independent-control contrast. PA1 minus C2, C3, and C5 are common-target placebo comparisons. Means and empirical 95% replication intervals are reported, with deterministic scenarios shown as degenerate intervals. Cost and service effect sizes are interpreted together.

Sensitivity analyses vary: (1) graph-support and minimum-pair thresholds; (2) graph density and top-k neighbourhood size; (3) service target; (4) holding-cost and shortage-penalty ratios; (5) deterministic versus low-, high-, and right-skewed lead times; (6) lost-sales versus backorder treatment; (7) product-universe and sparse-series filters; (8) basket fulfilment defined by all requested units versus all distinct items; (9) 1,000-resample paired bootstrap uncertainty; and (10) three rolling-origin windows with training-only re-estimation of the universe, forecasts, and graph. Threshold and top-k sensitivity remains a one-scenario diagnostic, not a pooled claim.

The earlier Phase 2 edge-level run used alpha = 3.0 at the grid boundary and is retained as historical secondary evidence. The primary analysis supersedes it for interpretation: alpha = 1.5 is interior, the matching tolerance is 1%, and the primary configuration hash is `70cc7bc98246449e106eb25e81456a03d6364806cdd68953bd9f72523d26d065`.

The executed experiment froze model versions, thresholds, cost table, critical-fractile rule, lead-time distributions, initial conditions, random seeds, and primary outcome definitions before test evaluation. The primary Phase 3 replay was run once under its recorded parent validation hash. Exact settings, level tables, paired contrasts, bootstrap draws, rolling windows, and the external dataset profile are recorded in the research package.

# 5. Results

## 5.1 Status of the results

The results are comparative simulations based on cleaned UCI demand, observed test-week baskets, and the frozen assumptions in `results/experiment_config.json`; they are not historical inventory observations or retailer savings. M5 remains a separate appendix benchmark.

## 5.2 Data preparation results

The data preparation audit established the following:

| Quantity | Result |
|---|---:|
| Raw UCI transaction rows | 1,067,371 |
| Retained positive merchandise lines | 1,036,877 |
| Retained invoice baskets | 39,516 |
| Retained products | 4,707 |
| Dense UCI product-week rows | 498,942 |
| Training-period invoices | 29,265 |
| Training-eligible products | 3,279 |
| Training-only co-purchase edges | 1,576,291 |
| Products in executed inventory simulation | 2,731 |
| Synthetic scenario rows | 12 |
| M5 weekly sample rows | 54,800 |

Integrity checks found zero invalid retained lines, duplicate basket identifiers, negative weekly values, self-edges, or failed source checksums. These engineering checks do not establish unbiased data or policy performance.

[[BASKET_SIZE_FIGURE]]

The basket-size plot makes the wholesale-like transaction structure visible: the retained baskets average about 26 transaction lines, with a long right tail, a pattern that is consistent with the basket-size benchmarks reported by Martin et al. (2020). The graph summary below is constructed from training-period data only; 1,576,291 retained edges represent about 29.3% of the possible unordered pairs among the 5,374,281-product-pair universe used for the density calculation.

[[GRAPH_SUMMARY_FIGURE]]

## 5.3 Forecast results

The validation design selected a forecasting method separately for each of the 2,731 simulated products from recent-four-week mean, recent-eight-week mean, and seasonal-naive 52-week demand. The selected method was then used for the test-period inventory replay.

The executed results are:

| Dataset | Model | Window | MAE | WAPE | Bias | 90% coverage | 90% width |
|---|---|---|---:|---:|---:|---:|---:|
| UCI | Recent four weeks | Validation | 21.170 | 0.782 | -0.249 | Not estimated | Not estimated |
| UCI | Recent eight weeks | Validation | 20.220 | 0.747 | -0.706 | Not estimated | Not estimated |
| UCI | Seasonal naive 52 weeks | Validation | 35.604 | 1.316 | 6.661 | Not estimated | Not estimated |
| UCI | Selected per product | Validation | 18.058 | 0.667 | -3.617 | 90.2% | 86.02 |

The selected UCI forecast reduced validation MAE by 10.7% relative to the recent-eight-week baseline and by 14.7% relative to the recent-four-week baseline. Its residual-based nominal 90% band covered 90.2% of validation observations, with mean width 86.02 units. These validation numbers are optimistic because the per-product model was selected by comparing the three candidates on those same validation observations. They are useful for documenting the selection rule, but they are not independent generalization estimates. The executed run used residual dispersion for safety-stock calculation; it did not claim fully calibrated probabilistic forecasting. Forecast accuracy is not interpreted as inventory superiority.

For transparency, the frozen selected forecast was also evaluated descriptively on the held-out test window after the policy replay:

| Dataset | Model | Test MAE | Test WAPE | Test bias |
|---|---|---:|---:|---:|
| UCI | Recent four weeks | 26.036 | 0.670 | -3.069 |
| UCI | Recent eight weeks | 25.631 | 0.659 | -5.111 |
| UCI | Seasonal naive 52 weeks | 49.341 | 1.269 | 18.121 |
| UCI | Selected per product | 28.577 | 0.735 | -1.899 |

These test metrics are honest held-out diagnostics, not tuning statistics. The negative selected bias is consistent with under-forecasting during the September–December peak test window and helps explain why realised item fill is below the nominal target. The small M5 sample check is reported in Appendix F rather than treated as a full benchmark.

## 5.4 Primary policy levels and paired contrasts

The primary replay covers all twelve synthetic scenarios, with 120 paired replications per scenario and the same 1% inventory-matching rule. The earlier S05 table is retained as a diagnostic in the package, but it is not the headline estimand. Because the scenarios use different h and p values, the headline result is a scenario-clustered mean of within-scenario differences, not a pooled cost level. Replication-level intervals below are normal 95% confidence intervals for the paired mean difference; deterministic scenarios have degenerate intervals.

| Policy | Cost | Average inventory | Item fill | Basket fill | Unmet units | Stockout frequency |
|---|---:|---:|---:|---:|---:|---:|
| PA1 | 5,478,634 [5,466,649, 5,492,489] | 1,344,831 [1,343,232, 1,346,021] | 0.8573 [0.8552, 0.8592] | 0.6352 [0.6132, 0.6555] | 212,050 [209,285, 215,129] | 0.0551 [0.0543, 0.0559] |
| C1 matched to PA1 | 5,246,922 [5,236,509, 5,259,267] | 1,334,487 [1,332,881, 1,335,692] | 0.8303 [0.8284, 0.8320] | 0.5408 [0.5239, 0.5527] | 252,166 [249,695, 254,951] | 0.0925 [0.0916, 0.0934] |
| C4 popularity | 5,309,898 [5,298,637, 5,321,780] | 1,338,562 [1,336,751, 1,340,103] | 0.8834 [0.8814, 0.8853] | 0.7019 [0.6813, 0.7212] | 173,235 [170,460, 176,258] | 0.0592 [0.0582, 0.0602] |
| C2 rewired | 5,559,885 [5,548,006, 5,570,923] | 1,347,493 [1,345,630, 1,349,281] | 0.8452 [0.8434, 0.8469] | 0.6117 [0.5927, 0.6291] | 230,103 [227,468, 232,710] | 0.0643 [0.0633, 0.0653] |
| C3 shuffled | 5,548,299 [5,535,587, 5,561,532] | 1,346,953 [1,344,745, 1,348,889] | 0.8468 [0.8452, 0.8483] | 0.6001 [0.5831, 0.6176] | 227,650 [225,375, 230,126] | 0.0677 [0.0666, 0.0688] |
| C5 stale graph | 5,626,094 [5,614,769, 5,638,404] | 1,349,745 [1,348,273, 1,351,339] | 0.8351 [0.8334, 0.8367] | 0.5942 [0.5773, 0.6100] | 245,110 [242,663, 247,632] | 0.0734 [0.0723, 0.0745] |

Relative to C1, PA1 costs 4.42% more and carries 0.78% more average inventory. Relative to C4, it costs 3.18% more and carries 0.47% more average inventory. These percentages are descriptive within S05 and use the absolute level means above.

The primary paired contrasts are PA1−C4, the graph-on-top-of-popularity test, and PA1−C1, the inventory-matched independent comparison. The scenario-clustered results are:

| Contrast | Cost difference (95% CI) | Inventory difference (95% CI) | Item-fill difference (95% CI) | Basket-fill difference (95% CI) |
| --- | ---: | ---: | ---: | ---: |
| PA1 − C1 | +201,341 [132,942, 269,741] | +7,585 [4,435, 10,736] | +0.0268 [0.0260, 0.0276] | +0.1113 [0.0902, 0.1325] |
| PA1 − C4 | +194,213 [113,211, 275,215] | +6,092 [6,017, 6,168] | −0.0258 [−0.0268, −0.0248] | −0.0644 [−0.0659, −0.0630] |

The direction is unchanged in every scenario: PA1−C1 is positive for item and basket fill in S01–S12, whereas PA1−C4 is negative for both. Cost differences are positive in every scenario for both contrasts. The per-scenario table, matching-quality table, and forest-plot-ready values are `results/phase3_scenario_contrast_summary.csv` and `results/phase3_matching_quality.csv`. Maximum accepted inventory gaps were 0.80% for PA1−C1 and 0.99% for C4−C1; no comparison violated the 1% band.

| Contrast | Cost difference | Inventory difference | Item-fill difference | Basket-fill difference |
|---|---:|---:|---:|---:|
| PA1 − C1 | +231,712 [227,660, 236,225] | +10,343 [10,321, 10,380] | +0.0270 [0.0263, 0.0276] | +0.0944 [0.0803, 0.1119] |
| PA1 − C4 | +168,736 [161,770, 175,981] | +6,268 [5,514, 7,314] | −0.0261 [−0.0272, −0.0248] | −0.0667 [−0.0849, −0.0493] |
| PA1 − C2 | −81,252 [−85,980, −76,182] | −2,663 [−3,876, −1,074] | +0.0121 [+0.0115, +0.0127] | +0.0235 [+0.0138, +0.0342] |
| PA1 − C3 | −69,665 [−74,949, −64,060] | −2,122 [−3,824, −246] | +0.0105 [+0.0099, +0.0112] | +0.0352 [+0.0260, +0.0441] |
| PA1 − C5 | −147,460 [−151,484, −143,045] | −4,914 [−6,483, −3,509] | +0.0222 [+0.0216, +0.0227] | +0.0410 [+0.0339, +0.0486] |

The 1,000-resample week-and-replication bootstrap is a direction check rather than a replacement for the paired mean CI. Its pooled percentile interval for PA1−C4 is negative for item fill (approximately −0.033 to −0.018) and basket fill (approximately −0.082 to −0.046); the corresponding PA1−C1 intervals are positive (approximately 0.020 to 0.034 for item fill and 0.072 to 0.207 for basket fill). The bootstrap cost interval is broad because it resamples scenarios with different synthetic cost scales, so cost inference uses the scenario-clustered mean CI. Thus the all-scenario evidence does not support a graph-on-top-of-popularity gain in this replay. The common-target placebo results remain allocation checks, not topology-identification tests.

Six-fold calibration was chosen on the validation window, before test evaluation, by selecting the candidate multiplier closest to the critical-fractile item-fill target. Across the 24 scenario-policy validation rows, six-fold had mean item fill 0.9487 against mean target 0.9725, versus 0.9152 at three-fold and 0.9625 at nine-fold; the six-fold candidate was the lowest-cost eligible interior calibration satisfying the pre-registered three-percentage-point acceptance rule. In the held-out test, however, the matched C1 target was approximately 0.993 on average while realised C1 item fill was approximately 0.83–0.84, reflecting peak-period under-forecasting and showing that validation calibration is optimistic for the test window. The three-/six-/nine-fold table is `results/phase3_calibration_robustness.csv`.

[[FRONTIER_FIGURE]]

[[COST_PENALTY_FIGURE]]

## 5.5 Rolling windows, sensitivity, external data, and mechanism

The three rolling windows give mixed robustness evidence. The compact outcome table reports all primary outcome classes, not only service:

| Window | Policy | Cost | Average inventory | Item fill | Basket fill | Unmet units | Stockout frequency |
|---|---|---:|---:|---:|---:|---:|---:|
| W1 | PA1 | 2,716,026 | 851,272 | 0.9709 | 0.9608 | 24,376 | 0.0159 |
| W1 | C4 | 2,715,009 | 851,226 | 0.9712 | 0.9571 | 24,104 | 0.0172 |
| W2 | PA1 | 2,798,678 | 850,705 | 0.9563 | 0.9002 | 38,970 | 0.0310 |
| W2 | C4 | 2,786,311 | 850,306 | 0.9595 | 0.9078 | 36,163 | 0.0302 |
| W3 primary | PA1 | 3,784,125 | 858,085 | 0.9401 | 0.9191 | 89,015 | 0.0386 |
| W3 primary | C4 | 3,763,181 | 857,419 | 0.9434 | 0.9184 | 84,189 | 0.0403 |

PA1 item fill was below C4 in all three windows, while basket fill was higher in W1, lower in W2, and nearly equal in W3. These rolling outputs are level checks; the corresponding paired contrast file reports PA1−C4 and PA1−C1 with window-specific intervals. The direction is therefore not a universal graph benefit. Sensitivity settings were not merely listed: top-k, minimum pair count, service target, h/p ratio, fixed order cost K, lost-sales versus backorder, and all-units versus distinct-item basket definitions each changed at least one output in the released sensitivity audit. The audit is in `results/gate_sensitivity_summary.csv`; threshold and top-k checks remain one-scenario diagnostics.

For transparency, the rolling contrast estimates were:

| Window | PA1−C4 item fill | PA1−C4 basket fill | PA1−C1 item fill | PA1−C1 basket fill |
| --- | ---: | ---: | ---: | ---: |
| W1 | −0.0003 [−0.0003, −0.0003] | +0.0037 [+0.0037, +0.0037] | +0.0055 [+0.0055, +0.0055] | +0.0258 [+0.0258, +0.0258] |
| W2 | −0.0031 [−0.0031, −0.0031] | −0.0076 [−0.0076, −0.0076] | +0.0057 [+0.0057, +0.0057] | +0.0332 [+0.0332, +0.0332] |
| W3 | −0.0032 [−0.0032, −0.0032] | +0.0007 [+0.0007, +0.0007] | +0.0030 [+0.0030, +0.0030] | +0.0253 [+0.0253, +0.0253] |

These are single-path chronological diagnostics, so the displayed intervals are degenerate and should not be mistaken for sampling intervals. In these rolling checks the C1 grid match was looser than the primary 1% band (5–7%); therefore the all-scenario 1% matched analysis, not the rolling C1 contrast, is the headline inference.

The corrected dunnhumby replay expands the training-only universe from 300 to 1,000 products and applies a declared stock-tightening factor of 0.01 to both policy targets. Under the same chronological split, alpha, graph logic, one-week lead-time assumption, and normalized costs, C4 item fill is 0.9482 and PA1 item fill is 0.0325, giving PA1−C4 = −0.9157; the cost difference is positive. The complete-basket proxy remains tied at 1.0, so only item fill discriminates. The direction of PA1−C4 therefore replicates the UCI item-fill result, although the magnitude is not comparable because the external universe and stress calibration differ. The original top-300/full-stock run remains as an audit file and was correctly classified as non-discriminating. No third dataset was added because a clean, license-compatible, reproducible source was not available in this release.
The external contrast was recorded with 120 paired deterministic paths and 1,000 bootstrap resamples to match the primary count; because the path is deterministic, those intervals are degenerate and are not treated as independent sampling evidence.

The mechanism is simple. A basket buffer can help only if it reallocates stock toward products whose joint availability affects the complete-order metric, while the resulting inventory, purchase, ordering, and shortage costs remain acceptable. A popularity buffer can achieve the same outcome when high-volume products also dominate basket completion. The PA1−C4 result shows that co-purchase edges did not add value on top of popularity in the primary replay; the placebo contrasts show that buffer allocation, not necessarily graph topology, drives the observed differences.

All scenario-level rows, matched comparisons, configuration hashes, figures, rolling-window outputs, external source profile, and phase reports are retained in `research_data_package/results/`.

# 6. Discussion

## 6.1 Interpretation of the executed evidence

The all-scenario Phase 3 replay shows a conditional service gain against the inventory-matched independent control, but not a graph-specific gain over popularity. PA1−C1 is positive for item and basket fill, while PA1−C4 is negative for both and more costly in every scenario. The tighter 1% match, 120 replications, 1,000-resample bootstrap, and three rolling windows strengthen the uncertainty statement, but the extra-buffer explanation is not fully ruled out because PA1 remains slightly higher in inventory than its matched control and C4 is not a causal experiment. Positive service differences should not be read as evidence that making one product available changes demand for its partner.

## 6.2 Relationship to prior literature

The study connects basket analysis, intermittent transaction demand, multi-item fulfilment, safety-stock logic, and stochastic lead-time replay. Its policy is a heuristic coordination layer adjacent to joint-replenishment and correlated-demand models, not a proof of optimality. The evidence reinforces the literature's distinction between forecast accuracy, calibrated uncertainty, and inventory-policy outcomes.

## 6.3 Interpretation for research design

The most important design result is methodological: a tightly matched independent control, a popularity-only control, graph-topology placebos, replication-level intervals, and rolling windows are needed before a basket graph can be credited with value. Completed transactions support a basket-service proxy, but they cannot identify stockout substitution or causal complementarity.

# 7. Implications

## 7.1 Implications for inventory managers

The evidence supports an offline counterfactual or controlled pilot, not immediate deployment. A manager should compare any basket-aware buffer with an independent policy at the same average inventory, using retailer-specific holding, shortage, ordering, and purchase costs. The operating dashboard should include item fill, complete-basket fulfilment, unmet units, average inventory, stockout frequency, and cost. Because C4 outperformed PA1 in the primary replay, a popularity allocation is the appropriate low-complexity benchmark before investment in a graph policy. The tested results do not justify a blanket rule to protect highly connected items.

Lead-time variability should be estimated from purchase orders and receipts rather than imported from the synthetic scenarios. A live pilot should be preceded by a shadow replay with actual availability and supplier events, and should preserve a placebo or randomized comparison where feasible.

## 7.2 Implications for researchers

Researchers should separate forecast improvement from policy improvement and should report the inventory-matched baseline alongside unadjusted cost. Graph-derived policy claims require edge-level placebos, popularity controls, stability strata, and a chronological split. Null or negative topology results are informative: in this study the strongest service control was popularity-only, and the thresholded graph policy was weak.

# 8. Limitations and future research

UCI Online Retail II records completed transaction lines, not attempted demand, on-hand balances, purchase orders, supplier dates, receipts, stockouts, lost sales, backorders, or observed costs. Complete-basket fulfilment is therefore a replay proxy; it cannot recover abandoned orders, substitutions, or historical stockout rates. Inventory, lead-time, cost, and service outcomes are simulated or normalized throughout the package.

The primary robustness upgrades are complete: alpha = 1.5 is interior, matching is within 1%, all twelve scenarios use 120 paired replications, bootstrap uncertainty uses 1,000 resamples, and three rolling windows are reported. The corrected dunnhumby stress replay is separate from UCI and discriminates on item fill but not on the complete-basket proxy; it does not convert the study into a causal or operational validation. The Scopus and Web of Science searches were specified but not run because licensed exports were unavailable, and the reference list is an open-record cross-check rather than a completed database-verified systematic review. The code is publicly archived at GitHub, but no DOI has yet been minted for the repository.

Future research needs observed inventory and supplier events, attempted orders and substitutions, calibrated probabilistic forecasts with CRPS or quantile loss, richer joint-replenishment and forecast-then-optimise baselines, and operational constraints such as case packs, capacity, perishability, and supplier reliability. The public repository archives the released configuration and source-download manifests; a DOI remains future work.

# 9. Conclusion

Across twelve synthetic scenarios, PA1 improved simulated item and complete-basket fill relative to its inventory-matched independent control, but it cost more and performed worse than the popularity-only C4 control in every scenario. Rolling windows did not establish a universal graph benefit, and the external check was non-discriminating. The evidence therefore supports a conditional service trade-off, not a graph-specific economic advantage. The extra-inventory explanation is not yet ruled out, and missing inventory, supplier, stockout, and attempted-demand records prevent historical or causal claims. Popularity is the stronger tested baseline; basket structure remains a candidate signal for controlled offline testing.

# 10. References and appendices

## 10.1 References

Agrawal, R., & Srikant, R. (1994). Fast algorithms for mining association rules in large databases. VLDB, 487–499. https://www.vldb.org/conf/1994/P487.PDF

Chen, Y.-L., Tang, K., Shen, R.-J., & Hu, Y.-H. (2005). Market basket analysis in a multiple store environment. Decision Support Systems, 40(2), 339–354. https://doi.org/10.1016/j.dss.2004.04.009

Hausman, W. H., Lee, H. L., & Zhang, A. X. (1998). Joint demand fulfillment probability in a multi-item inventory system with independent order-up-to policies. European Journal of Operational Research, 109(3), 646–659. https://doi.org/10.1016/S0377-2217(97)00152-5

Song, J.-S. (1998). On the order fill rate in a multi-item, base-stock inventory system. Operations Research, 46(6), 831–845. https://doi.org/10.1287/opre.46.6.831

Hill, R. M., & Pakkala, T. P. (2007). Base stock inventory policies for a multi-item demand process. International Journal of Production Economics, 109(1–2), 137–148. https://doi.org/10.1016/j.ijpe.2006.11.012

Abbott, H., & Palekar, U. S. (2008). Retail replenishment models with display-space elastic demand. European Journal of Operational Research, 186(2), 586–607. https://doi.org/10.1016/j.ejor.2006.12.067

Zhang, R., Kaku, I., & Xiao, Y. (2012). Model and heuristic algorithm of the joint replenishment problem with complete backordering and correlated demand. International Journal of Production Economics, 139(1), 33–41. https://doi.org/10.1016/j.ijpe.2011.01.019

Feng, H., Wu, Q., Muthuraman, K., & Deshpande, V. (2015). Replenishment policies for multi-product stochastic inventory systems with correlated demand and joint-replenishment costs. Production and Operations Management, 24(4), 647–664. https://doi.org/10.1111/poms.12290

Rahimi, Z., Down, D. G., Li, N., & Arnold, D. M. (2026). Ordering policies for multi-item inventory systems with correlated demands. European Journal of Operational Research, 333(2), 381–397. https://doi.org/10.1016/j.ejor.2025.12.042

Poormoaied, S., & Atan, Z. (2020). A continuous review policy for two complementary products with interrelated demand. Computers & Industrial Engineering, 150, 106980. https://doi.org/10.1016/j.cie.2020.106980

Poormoaied, S. (2022). Inventory decision in a periodic review inventory model with two complementary products. Annals of Operations Research, 315, 1937–1970. https://doi.org/10.1007/s10479-021-03949-w

Song, J.-S. (1994). The effect of leadtime uncertainty in a simple stochastic inventory model. Management Science, 40(5), 603–613. https://doi.org/10.1287/mnsc.40.5.603

Song, J.-S., Zhang, H., Hou, Y., & Wang, M. (2010). The effect of lead time and demand uncertainties in (r, q) inventory systems. Operations Research, 58(1), 68–80. https://doi.org/10.1287/opre.1090.0711

Hansen, O., Transchel, S., & Friedrich, H. (2023). Replenishment strategies for lost sales inventory systems of perishables under demand and lead time uncertainty. European Journal of Operational Research, 308(2), 661–675. https://doi.org/10.1016/j.ejor.2022.11.041

Martin, J., Nenycz-Thiel, M., Dawes, J., Tanusondjaja, A., Cohen, J., McColl, B., & Trinh, G. (2020). Fundamental basket size patterns and their relation to retailer performance. Journal of Retailing and Consumer Services, 54, 102032. https://doi.org/10.1016/j.jretconser.2020.102032

Omar, H., Klibi, W., Babai, M. Z., & Ducq, Y. (2023). Basket data-driven approach for omnichannel demand forecasting. International Journal of Production Economics, 257, 108748. https://doi.org/10.1016/j.ijpe.2022.108748

Peng, L., Wang, L., & Wang, S. (2022). A review of the joint replenishment problem from 2006 to 2022. Management System Engineering, 1, 9. https://doi.org/10.1007/s44176-022-00010-3

Chen, D. (2019). Online Retail II [Data set]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D

Makridakis, S., Spiliotis, E., & Assimakopoulos, V. (2022). The M5 accuracy competition: Results, findings and conclusions. International Journal of Forecasting, 38(4), 1346–1364. https://doi.org/10.1016/j.ijforecast.2021.11.013

Rethlefsen, M. L., Kirtley, S., Waffenschmidt, S., et al. (2021). PRISMA-S: An extension to the PRISMA statement for reporting literature searches in systematic reviews. Systematic Reviews, 10, 39. https://doi.org/10.1186/s13643-020-01542-z

Syntetos, A. A., & Boylan, J. E. (2005). The accuracy of intermittent demand estimates. International Journal of Forecasting, 21(2), 303–314. https://doi.org/10.1016/j.ijforecast.2004.10.001

Teunter, R. H., Syntetos, A. A., & Babai, M. Z. (2011). Intermittent demand: Linking forecasting to inventory obsolescence. European Journal of Operational Research, 214(3), 606–615. https://doi.org/10.1016/j.ejor.2011.05.018

Yang, Y., Ding, C., Lee, S., Yu, L., & Ma, F. (2021). A modified Teunter–Syntetos–Babai method for intermittent demand forecasting. Journal of Management Science and Engineering, 6(1), 53–63. https://doi.org/10.1016/j.jmse.2021.02.008

Wang, S., Kang, Y., & Petropoulos, F. (2024). Combining probabilistic forecasts of intermittent demand. European Journal of Operational Research, 315(3), 1038–1048. https://doi.org/10.1016/j.ejor.2024.01.032

Subramanian, S., & Harsha, P. (2021). Demand modeling in the presence of unobserved lost sales. Management Science, 67(6), 3803–3833. https://doi.org/10.1287/mnsc.2020.3667

Akçay, Y., Li, Y., & Natarajan, H. P. (2020). Category inventory planning with service level requirements and dynamic substitutions. Production and Operations Management, 29(11), 2553–2578. https://doi.org/10.1111/poms.13240

Ergin, E., Gümüş, M., & Yang, N. (2022). An empirical analysis of intra-firm product substitutability in fashion retailing. Production and Operations Management, 31(2), 607–621. https://doi.org/10.1111/poms.13569

Trapero, J. R., de Frutos, E. H., & Pedregal, D. J. (2024). Demand forecasting under lost sales stock policies. International Journal of Forecasting, 40(3), 1055–1068. https://doi.org/10.1016/j.ijforecast.2023.09.004

Huber, J., Müller, S., Fleischmann, M., & Stuckenschmidt, H. (2019). A data-driven newsvendor problem: From data to decision. European Journal of Operational Research, 278(3), 904–915. https://doi.org/10.1016/j.ejor.2019.04.043

van der Laan, N., Teunter, R. H., Romeijnders, W., & Kilic, O. A. (2022). The data-driven newsvendor problem: Achieving on-target service-levels using distributionally robust chance-constrained optimization. International Journal of Production Economics, 249, 108509. https://doi.org/10.1016/j.ijpe.2022.108509

Lin, S., Chen, Y., Li, Y., & Shen, Z. M. (2022). Data-driven newsvendor problems regularized by a profit risk constraint. Production and Operations Management, 31(4), 1630–1644. https://doi.org/10.1111/poms.13635

Wang, W., Deng, S., & Zhang, Y. (2025). Data-driven ordering policies for target oriented newsvendor with censored demand. European Journal of Operational Research, 323(1), 86–96. https://doi.org/10.1016/j.ejor.2024.10.045

Elmachtoub, A. N., & Grigas, P. (2022). Smart “Predict, then Optimize.” Management Science, 68(1), 9–26. https://doi.org/10.1287/mnsc.2020.3922

van der Haar, J. F., Wellens, A. P., Boute, R. N., & Basten, R. J. I. (2024). Supervised learning for integrated forecasting and inventory control. European Journal of Operational Research, 319(2), 573–586. https://doi.org/10.1016/j.ejor.2024.07.004

Bergsma, R., de Ruijt, C., & Bhulai, S. (2025). A systematic review of machine learning approaches in inventory control optimization. Operations Research Perspectives, 15, 100367. https://doi.org/10.1016/j.orp.2025.100367

Gneiting, T., & Raftery, A. E. (2007). Strictly proper scoring rules, prediction, and estimation. Journal of the American Statistical Association, 102(477), 359–378. https://doi.org/10.1198/016214506000001437

Spiliotis, E., Makridakis, S., Kaltsounis, A., & Assimakopoulos, V. (2021). Product sales probabilistic forecasting: An empirical evaluation using the M5 competition data. International Journal of Production Economics, 240, 108237. https://doi.org/10.1016/j.ijpe.2021.108237

Theodorou, E., Spiliotis, E., & Assimakopoulos, V. (2025). Forecast accuracy and inventory performance: Insights on their relationship from the M5 competition data. European Journal of Operational Research, 322(2), 414–426. https://doi.org/10.1016/j.ejor.2024.12.033

Petropoulos, F., Apiletti, D., Assimakopoulos, V., et al. (2022). Forecasting: Theory and practice. International Journal of Forecasting, 38(3), 705–871. https://doi.org/10.1016/j.ijforecast.2021.11.001

Rangapuram, S. S., Werner, L. D., Benidis, K., Mercado, P., Gasthaus, J., & Januschowski, T. (2021). End-to-end learning of coherent probabilistic forecasts for hierarchical time series. Proceedings of the 38th International Conference on Machine Learning, 139, 8832–8843. https://proceedings.mlr.press/v139/rangapuram21a.html

## 10.2 Appendix A. Data package contents

The reproducible code and data package is publicly archived at [GitHub](https://github.com/TalhaZabir/basket-aware-inventory-research). The public data records are [UCI Online Retail II](https://doi.org/10.24432/C5CG6D), the separate [M5 data release on Zenodo](https://doi.org/10.5281/zenodo.10203108), and the documented [dunnhumby Complete Journey release](https://github.com/bltap-plmarket/dunnhumby-complete-journey/releases/tag/v1.0-data), whose source page is [dunnhumby Source Files](https://www.dunnhumby.com/source-files/). The repository has no DOI yet. UCI identifies Online Retail II as licensed under the Creative Commons Attribution 4.0 International license (CC BY 4.0). Redistribution or adaptation of that source requires appropriate attribution to Daqing Chen and the UCI Machine Learning Repository. The dunnhumby mirror states DbCL-1.0; its terms should be reviewed before redistribution. The M5 files remain subject to their own source terms. The search and metadata-verification boundary is recorded in `results/gate5_literature_audit.md`.

| Component | Contents | Status and interpretation |
|---|---|---|
| Raw UCI source | `data/raw/uci_online_retail_ii.zip` | Downloaded and checksum-recorded; source transaction archive |
| Raw M5 sources | `data/raw/m5/` | Downloaded benchmark files; retained as a separate source |
| Clean transaction lines | `data/processed/uci_transaction_lines_clean.csv` | 1,036,877 positive merchandise lines after documented filters |
| Basket table | `data/processed/uci_baskets.csv` | Invoice-level basket summaries; completed transactions only |
| Weekly demand panel | `data/processed/uci_weekly_product_demand.csv` | Dense product-week demand panel for forecasting and replay |
| Co-purchase graph | `data/processed/uci_copurchase_edges_train_only.csv` | Constructed using training data through 2011-06-30 only |
| M5 sample panel | `data/processed/m5_weekly_product_demand_sample.csv` | Separate benchmark extract; not linked to UCI products |
| dunnhumby raw source | `data/raw/dunnhumby/dunnhumby-complete-journey-data.zip` | Documented public release mirror; checksum and license note recorded |
| dunnhumby processed data | `data/processed/dunnhumby/` | Clean lines, baskets, weekly panel, source profile, and separate external replay inputs |
| Synthetic scenarios | `data/synthetic/inventory_scenarios.csv` | Assumption-only lead-time and cost scenarios; not observed data |
| Provenance and validation | `data_dictionary.csv`, `source_manifest.csv`, `validation_report.json` | Documents fields, sources, checksums, and package checks |
| Reproduction scripts | `scripts/` | Download, cleaning, feature construction, scenario generation, and validation |
| Legacy experiment engine | `scripts/run_experiment.py` | Shared cost-responsive simulation engine; earlier four-policy runs used 30 stochastic replications |
| P0 robustness analyses | `scripts/run_p0_analyses.py` | Inventory-matched baseline, service-inventory frontier, shuffled-score placebo, break-even ratios, and sensitivity/stratification tables |
| P0 outputs | `results/frontier_results.csv`, `results/frontier_plot.svg`, `results/frontier_plot.png`, `results/cost_vs_penalty.svg`, `results/cost_vs_penalty.png`, `results/basket_size_distribution.svg`, `results/basket_size_distribution.png`, `results/graph_summary.svg`, `results/graph_summary.png`, `results/placebo_results.csv`, `results/placebo_comparison_summary.csv`, `results/inventory_matched_baseline.csv`, `results/break_even_analysis.csv`, `results/sensitivity_results.csv` | Verified analysis outputs; inventory, lead-time, costs, and service outcomes are simulated |
| P1 robustness analyses | `scripts/run_p1_analyses.py` | Explicit missing contrasts, test-week bootstrap intervals, extended alpha calibration, and rolling-origin replay |
| P1 outputs | `results/bootstrap_test_week_results.csv`, `results/bootstrap_test_week_summary.csv`, `results/bootstrap_test_week_pooled_summary.csv`, `results/alpha_extended_validation_calibration.csv`, `results/rolling_origin_results.csv`, `results/rolling_origin_summary.csv`, `results/forecast_test_summary.csv`, `results/p1_analysis_report.md` | Sampling and window-robustness outputs; all inventory outcomes remain simulated |
| Figure generation | `scripts/make_results_figures.py` | Recreates the cost/penalty, basket-size, and graph-summary figures from package outputs |
| Primary Phase 3 replay | `scripts/run_phase3_test.py`, `scripts/summarize_phase3_primary.py` | Alpha 1.5, 1% match, 120 stochastic replications, 1,000 bootstrap resamples |
| Rolling and external checks | `scripts/run_three_rolling_windows.py`, `scripts/prepare_and_run_dunnhumby.py` | Three UCI rolling windows and a separate dunnhumby validation pipeline |

## 10.3 Appendix B. Outcome definitions

| Outcome | Definition | Interpretation |
|---|---|---|
| Forecast MAE/RMSE | Error between forecast and held-out unit demand | Point forecast accuracy; not an inventory result |
| Probabilistic calibration | Coverage or scoring-rule performance for predictive intervals/distributions | Whether forecast uncertainty is credible |
| Item fill rate | Units or demand occasions fulfilled at the item level | Item-level service |
| Complete-basket fulfilment proxy | Share of replayed observed baskets for which every required product is available | Order-level service proxy; censored by completed-transaction data |
| Unmet units | Demand units not fulfilled under the simulated policy | Shortage quantity under stated lost-sales/backorder rules |
| Average inventory | Time-average simulated on-hand inventory | Inventory investment proxy |
| Stockout frequency | Number or share of periods with zero available stock when demand arrives | Simulated stockout exposure |
| Total cost | Holding cost plus ordering cost plus shortage penalty under the frozen specification | Economic comparison within the scenario, not observed retailer cost |
| Policy difference | Basket-aware outcome minus matched independent-baseline outcome | Primary paired contrast with uncertainty interval |

## 10.4 Appendix C. Frozen experiment record

This appendix records the configuration that was frozen for the executed analyses. It is an audit record of completed runs, not a pre-run checklist. The machine-readable originals are `results/experiment_config.json`, `results/phase3_alpha_validation_config.json`, `results/phase3_test_config.json`, `results/phase3_primary_diagnostics.json`, `data/processed/dunnhumby/dunnhumby_source_profile.json`, and `data/synthetic/inventory_scenarios.csv` in the research package. Earlier Phase 1/2 configurations remain as historical audit records.

### C.1 Experiment config JSON contents

| JSON field | Frozen value |
|---|---|
| train_end_week | 2011-06-27 |
| validation_start_week / validation_end_week | 2011-07-04 / 2011-08-29 |
| test_start_week / test_end_week | 2011-09-05 / 2011-12-05 |
| product_support_threshold | 20 positive training transactions |
| products_simulated | 2,731 |
| test_weeks | 14 |
| forecast_selection | Lowest product-level validation MAE among recent4, recent8, and seasonal52 |
| basket_alpha_candidates | [0.10, 0.25, 0.50, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0] |
| selected_basket_alpha | 1.5 in the Phase 3 primary analysis |
| basket_alpha_selection_rule | Validation only; lowest matched-cost eligible interior alpha meeting the preregistered service-gain rule |
| cost_target_rule | Critical fractile p/(p+h), where p is shortage penalty per unit and h is holding cost per unit-week |
| basket_score | Phase 2 PA1 uses top-five supported directed partners; PA2 uses training-basket coverage; PA3 thresholds PA1 scores |
| initial_inventory | Common independent deterministic target using the first test forecast and two-week protection |
| warm_up_weeks | 0 |
| replay_event_order | Post scheduled receipts; place weekly order; evaluate in-universe basket proxy; consume aggregate weekly demand |
| out_of_universe_baskets | Omit baskets with no in-universe products; project mixed baskets onto in-universe products |
| review_interval_weeks / coverage_weeks | 1 / 2 |
| basket_fulfilment_proxy | Share of observed test-week baskets whose full in-universe quantities fit within simulated on-hand stock at weekly review |
| stockout_model | Lost sales in the primary analysis; backorder is a sensitivity condition |
| stochastic_replications / deterministic_replications | Phase 3 all-scenario replay: 120 / 120; earlier Phase 2 grid: 30 / 1 |
| replication_reason | 120 paired stochastic paths provide stable replication intervals while keeping one primary scenario; deterministic paths are degenerate |
| primary_contrast / secondary_contrast | PA1 minus C4 at matched inventory; PA1 minus C1 secondary; PA1 minus C2/C3/C5 common-target placebos |
| lead_time_sampling | Clipped rounded normal for low/high variance; truncated exponential discrete distribution on 2 to 21 days for right-skewed lead time |
| critical_fractile_break_even_rule | Basket-aware is preferred when p/h exceeds the scenario-specific break-even ratio computed from paired non-shortage cost and unmet-unit differences |
| primary_cost | Holding plus shortage plus ordering plus normalized purchase cost |
| observed_data_boundary | Inventory, supplier, lead-time, stockout, lost-sales, and historical cost fields are unavailable and remain synthetic or simulated |

The Phase 3 primary test configuration hash is `70cc7bc98246449e106eb25e81456a03d6364806cdd68953bd9f72523d26d065`, under parent alpha-validation hash `ac87a2e332c1c82cff38e93a053770ebe97b744c7af8931e9f3269582ef05866`. It produced 4,320 policy rows, 1,440 rows for each headline contrast, 120 replications in each of twelve scenarios, and 1,000 bootstrap draws per contrast. No matching comparison exceeded the 1% band. The rolling-origin file contains three windows, and the dunnhumby source profile records the external checksum and license statement.

### C.2 Scenario lead-time PMFs

Lead times are sampled in days and then converted to whole review periods by `ceil(days / 7)`. The following are the resulting weekly probability mass functions used by the replay. They are synthetic assumptions, not estimates from supplier records.

| Scenario family | Day-level construction | P(L = 1 week) | P(L = 2 weeks) | P(L = 3 weeks) |
|---|---|---:|---:|---:|
| deterministic_7d | L = 7 days | 1.0000 | 0.0000 | 0.0000 |
| low_variance_normal | round and clip N(7, 1^2) to 5–9 days | 0.6915 | 0.3085 | 0.0000 |
| high_variance_normal | round and clip N(7, 3^2) to 1–14 days | 0.5662 | 0.4338 | 0.0000 |
| right_skewed_discrete | d in {2,...,21}, probability proportional to exp(-(d-2)/5) | 0.7118 | 0.2312 | 0.0570 |

### C.3 Policy parameters and replication controls

| Parameter | Frozen value |
|---|---|
| Review schedule | Weekly review; one order decision per product per review |
| Forecast coverage | Two weeks |
| Service target | Scenario critical fractile p/(p+h); the policy is not evaluated at an arbitrary common 0.95 target in the primary replay |
| Independent policies | P1 plans on a deterministic seven-day lead time; P2 uses the sampled lead-time draw |
| Basket-aware policies | P3 plans on a deterministic seven-day lead time; P4 uses the sampled lead-time draw |
| Basket buffer | Add alpha multiplied by the frozen graph score and current product forecast to the base target over the product's training-period graph neighbourhood; alpha = 1.5 in primary results |
| Ordering and purchase cost | K = 1 per positive order event; unit purchase cost = 1 per ordered unit |
| Holding and shortage cost units | h per unit-week of on-hand inventory; p per unmet demand unit in the replayed week |
| Basket service rule | A basket is complete only when every in-universe product quantity in the projected observed basket can be fulfilled from on-hand stock at weekly review |
| Partial fills | Fulfilled units consume stock; remaining units are unmet under lost sales and do not become backorders in the primary analysis |
| Stochastic replications | 120 paired replications in each of twelve scenarios; common random numbers; deterministic scenarios repeat the same path |
| Placebo control | C2 degree-preserving rewire, C3 label-shuffled graph, and C5 stale graph; the earlier score-shuffle file remains a score placebo and does not test topology |
| Bootstrap | 1,000 paired resamples over replications and test-week contributions; pooled intervals are reported from pooled draws rather than averaged scenario endpoints |

### C.4 Frozen data and output controls

The transaction cleaning rule, product universe, training-only edge construction, random seeds, scenario identifiers, output filenames, and sensitivity definitions were frozen before the final result tables were assembled. The primary all-scenario run uses 120 paired paths per scenario, 1,000 bootstrap resamples, and the 1% matching band. The resulting tables and figures are the files listed in Appendix A.

## 10.5 Appendix D. Evidence status

| Evidence category | Included evidence | What it can support |
|---|---|---|
| Observed or directly derived | UCI transaction lines, baskets, weekly demand, training-only co-purchase edges, M5 demand and calendar fields | Demand patterns, basket reconstruction, forecast benchmarking, reproducible feature construction |
| Synthetic or assumed | Inventory states, lead times, ordering and shortage costs, initial stock, stockouts, unmet demand, policy outcomes | Controlled comparative simulation and sensitivity analysis |
| Not available | Historical on-hand balances, purchase orders, supplier receipts, actual lead times, lost sales, uncompleted baskets, realised costs | Cannot support historical stockout, savings, causal complementarity, or operational-optimum claims |

Phase status is recorded in `results/final_phase_status.md`. Phase 3 precision targets and Phase 4 external replay are complete as separate simulated analyses. Licensed Scopus/Web of Science screening and automated all-number regeneration remain open; they are not presented as completed.

## 10.6 Appendix E. Per-scenario policy outcomes

The pooled table in Section 5 is a descriptive summary only. Because the scenarios use different holding and shortage-cost pairs, the following appendix preserves the legacy four-policy scenario-level comparisons. These rows are not substitutes for equivalent PA1-versus-C4 Phase 3 tests in all twelve scenarios. Costs are normalized simulation units; service values are means over the available replications.

| Scenario | Lead-time family | h | p | P1 cost | P2 cost | P3 cost | P4 cost | P1 item | P3 item | P1 basket | P3 basket |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S01 | deterministic_7d | 0.05 | 2 | 2,031,082 | 2,031,082 | 2,111,581 | 2,111,581 | 0.831 | 0.861 | 0.744 | 0.780 |
| S02 | deterministic_7d | 0.15 | 5 | 3,158,743 | 3,158,743 | 3,174,361 | 3,174,361 | 0.827 | 0.858 | 0.738 | 0.774 |
| S03 | deterministic_7d | 0.30 | 10 | 4,977,002 | 4,977,002 | 4,874,975 | 4,874,975 | 0.827 | 0.858 | 0.738 | 0.774 |
| S04 | low_variance_normal | 0.05 | 2 | 2,098,783 | 2,134,781 | 2,165,711 | 2,211,768 | 0.782 | 0.818 | 0.498 | 0.564 |
| S05 | low_variance_normal | 0.15 | 5 | 3,427,295 | 3,401,815 | 3,395,093 | 3,404,409 | 0.778 | 0.815 | 0.491 | 0.557 |
| S06 | low_variance_normal | 0.30 | 10 | 5,579,684 | 5,449,946 | 5,373,944 | 5,319,757 | 0.778 | 0.815 | 0.491 | 0.557 |
| S07 | high_variance_normal | 0.05 | 2 | 2,116,858 | 2,234,531 | 2,179,384 | 2,324,586 | 0.768 | 0.806 | 0.471 | 0.538 |
| S08 | high_variance_normal | 0.15 | 5 | 3,501,521 | 3,456,967 | 3,453,816 | 3,502,512 | 0.763 | 0.802 | 0.464 | 0.530 |
| S09 | high_variance_normal | 0.30 | 10 | 5,750,365 | 5,429,742 | 5,510,338 | 5,392,719 | 0.763 | 0.802 | 0.464 | 0.530 |
| S10 | right_skewed_discrete | 0.05 | 2 | 2,104,110 | 2,279,255 | 2,170,159 | 2,378,418 | 0.778 | 0.814 | 0.484 | 0.549 |
| S11 | right_skewed_discrete | 0.15 | 5 | 3,449,046 | 3,450,004 | 3,414,407 | 3,528,665 | 0.774 | 0.811 | 0.477 | 0.542 |
| S12 | right_skewed_discrete | 0.30 | 10 | 5,629,958 | 5,333,869 | 5,418,897 | 5,369,106 | 0.774 | 0.811 | 0.477 | 0.541 |

## 10.7 Appendix F. M5 sample benchmark check

The M5 extract is included as a separate, small forecasting pipeline check. It is not a full M5 competition benchmark: the executed result uses a 200-series sample and a four-week holdout, and it does not report the official hierarchical WRMSSE competition score or claim inventory relevance. No M5 product identifiers are linked to UCI products.

| Dataset | Model | Holdout | MAE | WAPE | Bias |
|---|---|---:|---:|---:|---:|
| M5 sample | Recent four weeks | 4 weeks | 3.281 | 0.401 | -0.578 |
| M5 sample | Recent eight weeks | 4 weeks | 3.121 | 0.382 | -0.473 |
| M5 sample | Seasonal naive 52 weeks | 4 weeks | 4.738 | 0.580 | -0.853 |

These values document that the package can read the M5 schema and run the same simple forecast candidates on a limited holdout. They should not be interpreted as evidence that the UCI inventory findings generalize to M5 or to retail operations more broadly.
