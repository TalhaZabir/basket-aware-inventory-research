# Consolidated phase status

## Phase 0 Audit and freeze

Completed. Known defects were reconciled, the primary estimand was frozen as service at matched inventory, and the execution log was created. The Phase 1 duplicate invocation is disclosed and excluded.

## Phase 1 Baseline calibration

Completed with a boundary limitation. The empirical-quantile forecast and safety multiplier were selected on validation; independent validation service was within three percentage points of target. The multiplier selected at 6.0, the grid boundary. The frozen test replay is retained and not rerun.

## Phase 2 Pair-aware policy

Completed. PA1, PA2, and PA3 were frozen with C1–C5 controls. The single guarded test replay completed under config hash `ce09b3fdfbae9f723fd8cf6f697ac7f6202a5740f6a4be92998c6abd158c88be`; matching tolerance passed at a maximum 2.23% inventory gap.

## Phase 3 Uncertainty and robustness

Completed for the primary analysis. The final replay covers all twelve scenarios with interior alpha=1.5, a 1% matching band, 120 paired replications per scenario, 1,000 bootstrap resamples, and three rolling-origin windows. The scenario-clustered PA1−C4 intervals reject a graph-on-top-of-popularity benefit; PA1−C1 is positive in every scenario. Placebo contrasts are reported separately.

## Phase 4 External validity

Completed as a separate pipeline. The documented dunnhumby Complete Journey release is downloaded, checksum-recorded, cleaned, replayed, and not merged with UCI. Its top-300 external replay is non-discriminating because both policies attain full simulated fill.

## Phase 5 Mechanism

Completed as a bounded stylised mechanism. The two-item availability model gives the condition under which joint service can benefit from reallocation at equal inventory. It is not presented as a general optimality proof.

## Phase 6 Literature and references

Partially completed as a targeted review. Scopus/Web of Science authenticated exports were unavailable, so no systematic-search hit counts are reported. The manuscript retains documented search strings and the expanded literature streams.

## Phase 7 Manuscript rewrite

Completed. Sections 1–10 were rebuilt around the Phase 3 primary evidence, with one primary analysis, paired intervals, absolute level results, rolling windows, external validation, a short mechanism section, and a consolidated limitations section.

## Phase 8 Quality gates

Core package validation and accessibility checks pass. Full visual rendering remains environment-limited by the absence of LibreOffice. The public project repository is live at https://github.com/TalhaZabir/basket-aware-inventory-research. The final decision branch is: conditional simulated service benefit, but no established graph-specific economic advantage.
