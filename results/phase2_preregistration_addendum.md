# Phase 2 policy preregistration addendum

Status: frozen before Phase 2 validation evaluation

## Objective

Test whether an edge-level basket-aware buffer improves service at matched inventory relative to an independent policy and to controls that remove or alter pair information. The primary contrast remains P4-style stochastic lead time versus its matched independent control; Phase 2 policy labels are reported separately.

## Pair-aware policies

1. **PA1 partner protection.** For product i, the buffer is

   `alpha * sum_j [(co_purchase_count_ij / sum_k co_purchase_count_ik) * P(j | i) * risk_j]`,

   where `risk_j = 1.645 * residual_sd_j`. The Phase 1 safety multiplier remains in the independent base-stock safety term; it is deliberately not applied again to the incremental pair buffer. The neighbourhood is the top five directed conditional-probability partners after a minimum pair count of five. The buffer is in item units and is added to the order-up-to target; it is not multiplied by current forecast demand.

2. **PA2 basket-coverage allocation.** Allocate the same total buffer mass as PA1 across products in proportion to training-basket marginal coverage score, `sum_b 1/|b|` for baskets containing the product. This is a budget-constrained continuous greedy relaxation: the total additional buffer is fixed to PA1, so any service change is not attributed to extra buffer mass.

3. **PA3 joint-service threshold.** Retain the PA1 buffer only for products at or above the preregistered 0.75 quantile of positive PA1 scores, then rescale the retained buffer to the same total mass as PA1. This tests whether concentrating protection on high joint-service contributors changes outcomes.

The inherited Phase 1 forecast, safety multiplier 6.0, alpha 1.5, weekly review, two-week protection, and lost-sales replay are held fixed during Phase 2 validation. No test result is used for tuning.

## Controls

- **C1:** inventory-matched independent baseline, matched separately by scenario, policy family, and common lead-time path.
- **C2:** endpoint-stub rewiring that preserves the node degree sequence and permutes the observed edge-count multiset.
- **C3:** product-label permutation across training baskets, preserving basket sizes and product marginal counts while destroying the original co-purchase relationships.
- **C4:** popularity-only buffer based on training unit volume, scaled to the same total buffer mass as PA1.
- **C5:** stale graph built from training baskets through 2010-12-27, before the current graph window.

All C2–C5 buffers are scaled to the PA1 total buffer mass. Thus the primary interpretation is allocation and relationship information, not a larger stock budget. The first validation implementation applied the Phase 1 multiplier a second time and produced an unmatched control; that validation is superseded and is not used for tuning or inference.

## Tuning and decision rule

The validation grid is alpha = [0.5, 1.0, 1.5, 2.0, 3.0] and PA3 threshold quantile = [0.50, 0.75, 0.90]. Matching searches independent service targets [0.80, 0.85, 0.90, 0.95, 0.975, 0.99, 0.995, 0.999, 0.9999, 0.99999, 0.999999, 0.9999999] so that the independent control is not artificially capped below the basket-aware inventory level. If the basket-aware inventory lies between two grid points, one linearly interpolated target is replayed and the closest inventory outcome is retained. The validation matching check requires the absolute inventory gap to remain below 5% of the basket-aware inventory; the current validation gaps are below this threshold. The selected setting maximizes scenario-averaged complete-basket-fill gain over the matched independent baseline, with item-fill gain as the tie-breaker; costs are reported but are not pooled for tuning because h and p differ by scenario. The validation-selected setting is frozen before any Phase 2 test replay.

Phase 2 provides evidence of a pair-structure contribution only if the selected policy improves the primary matched-inventory service estimand relative to C1 and is not contradicted by C2, C3, or C4. Otherwise the result is reported as a null or boundary-condition result.

## Phase 2 validation freeze

The corrected validation run froze alpha = 3.0 and PA3 threshold quantile = 0.50 under configuration hash `677bfb9345b95983bf1fb63fee0e4dd8da3ac63b372530d6c76587aaf5482e44`. The maximum observed relative inventory gap after interpolation was 4.60%, below the 5% matching tolerance. The next test evaluation is one guarded replay under this hash with the same forecast, safety multiplier, graph seeds, and policy settings; no test result may change them.

## Reproducibility

Graph seeds, buffers, configuration hashes, validation outputs, and any failed or excluded runs will be recorded in `results/run_log.csv` and `results/phase_2_report.md`.
