# Phase 3 execution audit

The final primary replay is frozen in `phase3_test_config.json` with configuration hash `70cc7bc98246449e106eb25e81456a03d6364806cdd68953bd9f72523d26d065` and parent alpha-validation hash `ac87a2e332c1c82cff38e93a053770ebe97b744c7af8931e9f3269582ef05866`.

- Scenario scope: S01–S12; S05 remains the diagnostic low-variance stochastic case.
- Alpha: 1.5, selected as an interior validation value.
- Matching band: maximum accepted relative average-inventory gap 0.79%, below 1% for PA1 and C4.
- Replications: 120 paired replications in every scenario.
- Bootstrap: 1,000 resamples per contrast over replication/week contributions.
- Primary graph-on-top-of-popularity estimand: PA1 minus C4.
- Placebo estimands: PA1 minus C2/C3/C5 at the common primary target.
- Rolling windows: W1, W2, and W3 primary, with graph and universe re-estimation.
- External source: dunnhumby Complete Journey, retained as a separate pipeline.

The primary S05 paired estimates are PA1−C1 item fill +0.0270 and basket fill +0.0944, while PA1−C4 item fill is −0.0261 and basket fill is −0.0667. The 1,000-resample PA1−C4 intervals are cost [110,800, 228,187], item fill [−0.0324, −0.0189], and basket fill [−0.0845, −0.0509]. Thus the graph-on-top-of-popularity claim is not supported.

The UCI rolling results are mixed: PA1 is slightly below C4 on item fill in W1, W2, and W3, while basket fill is higher in W1, lower in W2, and nearly equal in W3. The dunnhumby top-300 replay has full simulated fill for both policies and is non-discriminating.
