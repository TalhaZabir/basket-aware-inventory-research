# Gate 1 evidence report

The primary replay covers S01–S12 with 120 paired replications per scenario, a 1% average-inventory matching band, and 1,000 bootstrap resamples. The pooled estimand is the unweighted mean of the twelve scenario-level paired means; its confidence interval is the normal 95% interval across those twelve scenario estimates.

The primary directions are stable across all twelve scenarios. PA1−C1 is positive for item fill and complete-basket fill in every scenario; PA1−C4 is negative for both measures in every scenario. Cost differences are positive in every scenario. The scenario-clustered means are +0.0268 item fill and +0.1113 basket fill for PA1−C1, and −0.0258 item fill and −0.0644 basket fill for PA1−C4. No primary matching comparison exceeded 1%.

Six-fold residual calibration was selected on validation by closeness to the critical-fractile target under a three-percentage-point acceptance rule. Mean validation item fill was 0.9152 at 3×, 0.9487 at 6×, and 0.9625 at 9× against a mean target of 0.9725. Held-out C1 fill is materially lower than its applied target because the test window contains a peak-period under-forecast; this is an observed calibration failure, not evidence of historical service.

The rolling-origin file reports PA1−C4 and PA1−C1 for W1–W3. Those diagnostics use one chronological path per window, so their intervals are degenerate; the rolling C1 matching grid is 5–7%, outside the primary 1% band. They are therefore robustness diagnostics, not substitutes for the primary all-scenario matched analysis.

The sensitivity audit confirms that top-k, minimum pair count, service target, h/p ratio, K, lost-sales versus backorder, and basket definition each change at least one reported output. Threshold and top-k settings remain one-scenario diagnostics. All quantities remain simulated because the public transaction sources contain no inventory, supplier, stockout, or procurement-cost records.
