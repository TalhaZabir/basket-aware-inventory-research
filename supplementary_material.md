# Supplementary material

This supplement contains the machine-readable audit behind the manuscript. It is the location for detailed configuration, scenario definitions, full cell-level tables, and legacy analyses; the main text reports the primary estimand and directs readers here for audit detail.

## Supplementary tables

- **S1.** All-cell PA1 minus C4 and PA1 minus C1 paired contrasts, with scenario-clustered estimates and intervals.
- **S2.** Scenario definitions, lead-time probability mass functions, holding and shortage costs, and service targets.
- **S3.** Inventory matching quality for every accepted comparison; all differences are within the 1% band.
- **S4.** Three rolling-origin windows with paired service contrasts and uncertainty intervals.
- **S5.** Sensitivity checks for top-k, minimum pair count, service target, holding-to-shortage ratio, fixed order cost, lost-sales versus backorder treatment, basket definition, and exploratory strata.
- **S6.** Calibration comparison for 3x, 6x, and 9x buffers and the alpha grid.
- **S7.** Legacy per-scenario policy levels retained for reproducibility.
- **S8.** Data and reference audit, including source links, licences, checksums, and unresolved evidence boundaries.

The corresponding CSV files are supplied in the repository release under `results/`. They are supplementary outputs, not additional independent observations.

## Frozen configuration record

The primary analysis used a 2,731-product UCI universe, a training-only co-purchase graph, alpha = 1.5, a 1% inventory-matching band, 120 paired replications in each of 12 factorial cells, common random numbers, and 1,000 paired bootstrap resamples over replications and test-week contributions. Deterministic lead-time cells repeat the same demand path; their replication intervals are therefore degenerate. The training, validation, and test windows and the warm-up rules are defined in the manuscript methodology.

Policy labels are fixed as follows: C1 is the inventory-matched independent control, C4 is the popularity-only control, and PA1 is the graph buffer layered on the popularity baseline. The graph uses training-period pair counts and partner demand scale only. No historical on-hand, supplier lead-time, purchase-order, stockout, or realised-cost field is present in the public basket sources; all such inventory quantities are simulated and labelled accordingly.

## Reproducibility and evidence boundary

The repository includes download and cleaning scripts, source profiles, schemas, scenario files, policy code, figure-generation code, and the manuscript builder. The dunnhumby result is a pipeline stress check, not an external replication: its complete-basket proxy is non-discriminating and its severe item-fill contrast is sensitive to the declared stock-tightening setup. The literature review is targeted rather than a licensed Scopus/Web of Science systematic search.
