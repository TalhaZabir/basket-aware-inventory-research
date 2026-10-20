# Executed forecast and inventory simulation results

## Evidence boundary

The UCI transaction and basket tables are observed or directly derived. Inventory states, lead times, costs, stockouts, unmet units, and policy outcomes below are simulated under the frozen configuration. M5 remains a separate forecasting benchmark and is not merged with UCI.

## Frozen configuration

- Product universe: 2731 products with at least 20 positive training weeks.
- Forecast split: training through 2011-06-27; validation 2011-07-04 to 2011-08-29; test 2011-09-05 to 2011-12-05.
- Selected basket buffer alpha: 1.5 from candidates [0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0].
- Active service target: critical fractile p/(p+h), with p equal to shortage penalty and h equal to holding cost.
- Stochastic replications: 30; deterministic scenarios: one deterministic run.

## Forecast validation

| model | validation_mae | validation_wape | validation_bias | validation_90pct_coverage | validation_90pct_width | products_selected |
| --- | --- | --- | --- | --- | --- | --- |
| recent4 | 21.1701 | 0.782208 | -0.248596 | nan | nan | 1226 |
| recent8 | 20.2204 | 0.74712 | -0.705816 | nan | nan | 971 |
| seasonal52 | 35.6039 | 1.31552 | 6.66121 | nan | nan | 534 |
| selected_per_product | 18.0583 | 0.667231 | -3.61675 | 0.902356 | 86.0249 | 2731 |

## M5 benchmark sample

| dataset | series | holdout_weeks | holdout_start | holdout_end | model | mae | wape | bias |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M5 sample | 200 | 4 | 2016-03-28 | 2016-04-18 | recent4 | 3.28063 | 0.401422 | -0.578125 |
| M5 sample | 200 | 4 | 2016-03-28 | 2016-04-18 | recent8 | 3.12078 | 0.381864 | -0.473281 |
| M5 sample | 200 | 4 | 2016-03-28 | 2016-04-18 | seasonal52 | 4.7375 | 0.579688 | -0.8525 |

## Basket-buffer calibration

| alpha | total_cost | item_fill_rate | complete_basket_fill_rate | unmet_units |
| --- | --- | --- | --- | --- |
| 0 | 991225 | 0.964996 | 0.887509 | 23285 |
| 0.25 | 1.00031e+06 | 0.96668 | 0.888928 | 22165 |
| 0.5 | 1.01014e+06 | 0.968153 | 0.892477 | 21185 |
| 1 | 1.03102e+06 | 0.97068 | 0.89709 | 19504 |
| 1.5 | 1.05303e+06 | 0.972917 | 0.903123 | 18016 |
| 2 | 1.07622e+06 | 0.974808 | 0.906671 | 16758 |
| 3 | 1.12567e+06 | 0.977646 | 0.915543 | 14870 |

## Inventory summary

| scenario_id | policy | replications | total_cost_mean | average_inventory_units_mean | item_fill_rate_mean | complete_basket_fill_rate_mean | unmet_units_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 | P1_independent_deterministic | 1 | 2.03108e+06 | 261310 | 0.830936 | 0.744347 | 251252 |
| S01 | P2_independent_stochastic | 1 | 2.03108e+06 | 261310 | 0.830936 | 0.744347 | 251252 |
| S01 | P3_basket_deterministic | 1 | 2.11158e+06 | 313724 | 0.860628 | 0.779589 | 207126 |
| S01 | P4_basket_stochastic | 1 | 2.11158e+06 | 313724 | 0.860628 | 0.779589 | 207126 |
| S02 | P1_independent_deterministic | 1 | 3.15874e+06 | 254354 | 0.827187 | 0.737739 | 256823 |
| S02 | P2_independent_stochastic | 1 | 3.15874e+06 | 254354 | 0.827187 | 0.737739 | 256823 |
| S02 | P3_basket_deterministic | 1 | 3.17436e+06 | 306585 | 0.857781 | 0.774302 | 211357 |
| S02 | P4_basket_stochastic | 1 | 3.17436e+06 | 306585 | 0.857781 | 0.774302 | 211357 |
| S03 | P1_independent_deterministic | 1 | 4.977e+06 | 254354 | 0.827187 | 0.737739 | 256823 |
| S03 | P2_independent_stochastic | 1 | 4.977e+06 | 254354 | 0.827187 | 0.737739 | 256823 |
| S03 | P3_basket_deterministic | 1 | 4.87498e+06 | 306585 | 0.857781 | 0.774302 | 211357 |
| S03 | P4_basket_stochastic | 1 | 4.87498e+06 | 306585 | 0.857781 | 0.774302 | 211357 |
| S04 | P1_independent_deterministic | 30 | 2.09878e+06 | 245844 | 0.782413 | 0.498218 | 323364 |
| S04 | P2_independent_stochastic | 30 | 2.13478e+06 | 272869 | 0.803886 | 0.540015 | 291452 |
| S04 | P3_basket_deterministic | 30 | 2.16571e+06 | 294164 | 0.81832 | 0.5644 | 270000 |
| S04 | P4_basket_stochastic | 30 | 2.21177e+06 | 322753 | 0.83475 | 0.59025 | 245583 |
| S05 | P1_independent_deterministic | 30 | 3.42729e+06 | 239232 | 0.777795 | 0.490813 | 330226 |
| S05 | P2_independent_stochastic | 30 | 3.40182e+06 | 265051 | 0.799102 | 0.533186 | 298561 |
| S05 | P3_basket_deterministic | 30 | 3.39509e+06 | 287306 | 0.814712 | 0.55653 | 275362 |
| S05 | P4_basket_stochastic | 30 | 3.40441e+06 | 314682 | 0.830966 | 0.584244 | 251208 |
| S06 | P1_independent_deterministic | 30 | 5.57968e+06 | 239224 | 0.777878 | 0.491498 | 330103 |
| S06 | P2_independent_stochastic | 30 | 5.44995e+06 | 265041 | 0.799195 | 0.533916 | 298424 |
| S06 | P3_basket_deterministic | 30 | 5.37394e+06 | 287295 | 0.814806 | 0.557406 | 275223 |
| S06 | P4_basket_stochastic | 30 | 5.31976e+06 | 314668 | 0.831073 | 0.585188 | 251048 |
| S07 | P1_independent_deterministic | 30 | 2.11686e+06 | 239067 | 0.768062 | 0.471424 | 344692 |
| S07 | P2_independent_stochastic | 30 | 2.23453e+06 | 320047 | 0.827222 | 0.572183 | 256772 |
| S07 | P3_basket_deterministic | 30 | 2.17938e+06 | 285749 | 0.805898 | 0.538062 | 288461 |
| S07 | P4_basket_stochastic | 30 | 2.32459e+06 | 371009 | 0.851551 | 0.621101 | 220615 |
| S08 | P1_independent_deterministic | 30 | 3.50152e+06 | 232598 | 0.763173 | 0.463999 | 351957 |
| S08 | P2_independent_stochastic | 30 | 3.45697e+06 | 309901 | 0.822018 | 0.563828 | 264505 |
| S08 | P3_basket_deterministic | 30 | 3.45382e+06 | 279019 | 0.802062 | 0.529961 | 294163 |
| S08 | P4_basket_stochastic | 30 | 3.50251e+06 | 360558 | 0.847441 | 0.613045 | 226724 |
| S09 | P1_independent_deterministic | 30 | 5.75037e+06 | 232559 | 0.763115 | 0.464405 | 352044 |
| S09 | P2_independent_stochastic | 30 | 5.42974e+06 | 309852 | 0.82204 | 0.564655 | 264472 |
| S09 | P3_basket_deterministic | 30 | 5.51034e+06 | 278967 | 0.802061 | 0.53046 | 294164 |
| S09 | P4_basket_stochastic | 30 | 5.39272e+06 | 360507 | 0.847466 | 0.61393 | 226686 |
| S10 | P1_independent_deterministic | 30 | 2.10411e+06 | 243955 | 0.778206 | 0.484435 | 329616 |
| S10 | P2_independent_stochastic | 30 | 2.27925e+06 | 356137 | 0.848599 | 0.610724 | 225002 |
| S10 | P3_basket_deterministic | 30 | 2.17016e+06 | 291829 | 0.814447 | 0.549153 | 275757 |
| S10 | P4_basket_stochastic | 30 | 2.37842e+06 | 409152 | 0.868372 | 0.652741 | 195617 |
| S11 | P1_independent_deterministic | 30 | 3.44905e+06 | 237357 | 0.773515 | 0.477499 | 336587 |
| S11 | P2_independent_stochastic | 30 | 3.45e+06 | 344506 | 0.843668 | 0.60023 | 232330 |
| S11 | P3_basket_deterministic | 30 | 3.41441e+06 | 285003 | 0.81069 | 0.541566 | 281341 |
| S11 | P4_basket_stochastic | 30 | 3.52867e+06 | 397247 | 0.864431 | 0.645012 | 201473 |
| S12 | P1_independent_deterministic | 30 | 5.62996e+06 | 237304 | 0.773541 | 0.476809 | 336549 |
| S12 | P2_independent_stochastic | 30 | 5.33387e+06 | 344422 | 0.843738 | 0.600201 | 232226 |
| S12 | P3_basket_deterministic | 30 | 5.4189e+06 | 284943 | 0.810731 | 0.540822 | 281280 |
| S12 | P4_basket_stochastic | 30 | 5.36911e+06 | 397157 | 0.86449 | 0.644567 | 201386 |

## Basket-aware policy contrasts

| scenario_id | contrast | total_cost_difference_mean | total_cost_difference_p025 | total_cost_difference_p975 | item_fill_rate_difference_mean | complete_basket_fill_rate_difference_mean |
| --- | --- | --- | --- | --- | --- | --- |
| S01 | P2_minus_P1 | 0 | 0 | 0 | 0 | 0 |
| S01 | P3_minus_P1 | 80498.4 | 80498.4 | 80498.4 | 0.0296918 | 0.0352423 |
| S01 | P4_minus_P2 | 80498.4 | 80498.4 | 80498.4 | 0.0296918 | 0.0352423 |
| S01 | P4_minus_P3 | 0 | 0 | 0 | 0 | 0 |
| S02 | P2_minus_P1 | 0 | 0 | 0 | 0 | 0 |
| S02 | P3_minus_P1 | 15618.2 | 15618.2 | 15618.2 | 0.0305935 | 0.0365639 |
| S02 | P4_minus_P2 | 15618.2 | 15618.2 | 15618.2 | 0.0305935 | 0.0365639 |
| S02 | P4_minus_P3 | 0 | 0 | 0 | 0 | 0 |
| S03 | P2_minus_P1 | 0 | 0 | 0 | 0 | 0 |
| S03 | P3_minus_P1 | -102026 | -102026 | -102026 | 0.0305935 | 0.0365639 |
| S03 | P4_minus_P2 | -102026 | -102026 | -102026 | 0.0305935 | 0.0365639 |
| S03 | P4_minus_P3 | 0 | 0 | 0 | 0 | 0 |
| S04 | P2_minus_P1 | 35997.5 | 33963 | 37379.5 | 0.0214735 | 0.0417964 |
| S04 | P3_minus_P1 | 66927.8 | 63528.3 | 68697.2 | 0.0359079 | 0.0661821 |
| S04 | P4_minus_P2 | 76987.1 | 73246.2 | 79038.3 | 0.0308643 | 0.0502349 |
| S04 | P4_minus_P3 | 46056.8 | 43916.7 | 47439.4 | 0.01643 | 0.0258492 |
| S05 | P2_minus_P1 | -25479.2 | -31154.8 | -21426.9 | 0.021307 | 0.042374 |
| S05 | P3_minus_P1 | -32201.3 | -42109.3 | -26434.6 | 0.0369174 | 0.0657171 |
| S05 | P4_minus_P2 | 2593.66 | -8142.57 | 8981.68 | 0.0318636 | 0.0510573 |
| S05 | P4_minus_P3 | 9315.77 | 3152.99 | 14103.9 | 0.0162532 | 0.0277141 |
| S06 | P2_minus_P1 | -129738 | -141588 | -120570 | 0.0213169 | 0.042418 |
| S06 | P3_minus_P1 | -205740 | -226609 | -192613 | 0.0369282 | 0.065908 |
| S06 | P4_minus_P2 | -130189 | -152233 | -115765 | 0.0318784 | 0.0512726 |
| S06 | P4_minus_P3 | -54186.8 | -67569.3 | -43424.9 | 0.0162672 | 0.0277827 |
| S07 | P2_minus_P1 | 117673 | 113334 | 121942 | 0.0591601 | 0.100759 |
| S07 | P3_minus_P1 | 62525.2 | 59643.3 | 64864.8 | 0.0378367 | 0.0666373 |
| S07 | P4_minus_P2 | 90054.4 | 88063.3 | 91366 | 0.0243291 | 0.0489183 |
| S07 | P4_minus_P3 | 145202 | 141929 | 148505 | 0.0456525 | 0.0830396 |
| S08 | P2_minus_P1 | -44554.5 | -57753.7 | -31692.6 | 0.0588452 | 0.0998287 |
| S08 | P3_minus_P1 | -47705 | -57111.8 | -41099.2 | 0.0388888 | 0.0659618 |
| S08 | P4_minus_P2 | 45545.6 | 39107.6 | 50507 | 0.0254225 | 0.0492168 |
| S08 | P4_minus_P3 | 48696.1 | 38277.5 | 60489.9 | 0.0453789 | 0.0830837 |
| S09 | P2_minus_P1 | -320623 | -347565 | -292124 | 0.0589257 | 0.10025 |
| S09 | P3_minus_P1 | -240027 | -259329 | -224918 | 0.0389465 | 0.0660548 |
| S09 | P4_minus_P2 | -37022.8 | -50831.5 | -26257.6 | 0.0254257 | 0.0492756 |
| S09 | P4_minus_P3 | -117619 | -139846 | -91540.7 | 0.0454049 | 0.0834704 |
| S10 | P2_minus_P1 | 175145 | 170712 | 179894 | 0.0703934 | 0.12629 |
| S10 | P3_minus_P1 | 66049.1 | 63475.3 | 68927.9 | 0.0362415 | 0.0647186 |
| S10 | P4_minus_P2 | 99163.3 | 96945.6 | 100859 | 0.0197729 | 0.0420166 |
| S10 | P4_minus_P3 | 208259 | 204434 | 211657 | 0.0539248 | 0.103588 |
| S11 | P2_minus_P1 | 958.29 | -13387.1 | 16678.2 | 0.070153 | 0.122731 |
| S11 | P3_minus_P1 | -34639.5 | -43126.4 | -25738.5 | 0.0371748 | 0.0640675 |
| S11 | P4_minus_P2 | 78660.6 | 71523.7 | 84247.6 | 0.0207635 | 0.0447822 |
| S11 | P4_minus_P3 | 114258 | 102702 | 125498 | 0.0537418 | 0.103446 |
| S12 | P2_minus_P1 | -296088 | -325980 | -260981 | 0.0701974 | 0.123392 |
| S12 | P3_minus_P1 | -211061 | -229568 | -191940 | 0.0371902 | 0.0640137 |
| S12 | P4_minus_P2 | 35236.4 | 19879.2 | 47741.8 | 0.0207521 | 0.0443661 |
| S12 | P4_minus_P3 | -49790.9 | -74163 | -25221 | 0.0537593 | 0.103744 |

## Interpretation

The policy contrasts are paired differences within scenario and replication. Negative cost differences favor the basket-aware policy; positive fill-rate differences favor it. Deterministic scenarios have no stochastic interval because the demand path and lead time are fixed. These are comparative simulation findings, not observed retailer savings or historical stockout estimates.

P0 robustness outputs are generated by `scripts/run_p0_analyses.py`: `frontier_results.csv`, `frontier_plot.png`, `placebo_results.csv`, `inventory_matched_baseline.csv`, `break_even_analysis.csv`, and `sensitivity_results.csv`.
