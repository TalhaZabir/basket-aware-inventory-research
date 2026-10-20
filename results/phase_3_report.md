# Phase 3 uncertainty and robustness report

The final primary replay uses S05, alpha=1.5, a 1% inventory-matching band, 120 stochastic replications, and 1,000 paired bootstrap resamples. The configuration hash is `983c3e4505db8a6efe8fbf2538b2332abad1bb80b35c1c87d0ab8f2741d44097`.

The primary graph-on-top-of-popularity contrast is PA1−C4. PA1 is worse on item fill (−0.0261) and complete-basket fill (−0.0667), with a positive cost difference (+168,736). Bootstrap percentile intervals are cost [110,800, 228,187], item fill [−0.0324, −0.0189], and basket fill [−0.0845, −0.0509]. PA1−C1 is positive for service but includes a small residual inventory difference because the accepted 1% matching band is a tolerance, not exact equality.

PA1−C2, PA1−C3, and PA1−C5 are common-target placebo contrasts. PA1 is better than these controls on item and basket fill in the paired replay, but that result does not identify the original graph topology as the cause. The rolling-origin analysis uses three windows and gives mixed basket-fill direction across windows. The primary analysis therefore supports a conditional service trade-off, not a robust graph-specific advantage.

**Acceptance status:** pass for the requested interior alpha, tighter matching, 100+ replication, 1,000+ bootstrap, and three-window checks. Remaining limitations are documented in Section 8.
