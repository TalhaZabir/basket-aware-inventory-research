# Hostile referee simulation

1. **The policy outcomes are simulated, not observed.** Answer: Sections 4 and 8 label all inventory, lead-time, stockout, unmet-demand, and cost quantities as simulated and identify the missing operational records.
2. **The forecast is selected on validation and may be optimistic.** Answer: Section 5 reports the validation/test distinction and states that validation metrics are optimistic because per-product selection used the validation window.
3. **The test window is short.** Answer: the 14-week window, 30 paired stochastic paths, test-week bootstrap, and earlier rolling-origin check are reported; the incomplete three-window/1,000-resample requirement is disclosed.
4. **The pair-aware policy may simply add stock.** Answer: the primary estimand is service at matched inventory; C1 is explicitly matched and Phase 2 reports inventory gaps.
5. **The graph placebo is not a full topology test.** Answer: score-shuffle and edge rewiring controls are distinguished; C4 popularity-only and C2/C3 are reported, and no topology claim is made.
6. **Costs are pooled across heterogeneous scenarios.** Answer: scenario-level files are retained and pooled cost is described as descriptive; the main conclusion relies on paired contrasts and matched inventory.
7. **The alpha choice is boundary-sensitive.** Answer: alpha = 3 is identified as the Phase 2 validation boundary; the earlier alpha = 1.5 score-buffer analysis is kept separate and not presented as the same policy.
8. **Basket demand is censored by completed transactions.** Answer: the basket metric is called a completed-basket service proxy and substitution/abandoned demand are listed as limitations.
9. **External validity is weak.** Answer: M5 is not treated as a second basket dataset; Phase 4 is marked incomplete and a second licensed basket source is specified as required.
10. **The literature review is not systematic.** Answer: Section 3 is labelled targeted, exact licensed-database strings are supplied, and no invented hit counts are reported.

The unresolved gates are visible in `phase_3_report.md`, `phase_4_report.md`, `phase_6_report.md`, and `phase_8_report.md`. No objection is hidden behind a positive headline claim.
