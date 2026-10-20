# Gate 3 external-validity replay

The original top-300 dunnhumby check was non-discriminating because both policies had full fill. The corrected check uses the same chronological split, alpha = 1.5, graph construction, one-week lead-time assumption, normalized costs, and PA1/C4 policy logic, but expands the training-only universe to the top 1,000 products and applies a pre-declared stock-tightening factor of 0.01 to both policies' initial target. This is an external stress replay, not a claim about observed dunnhumby inventory.

| Policy | Item fill | Complete-basket fill | Unmet units | Average inventory | Total cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| C4 popularity | 0.948235 | 1.000000 | 1,722,239 | 13,676.17 | 46,614,146 |
| PA1 graph | 0.032547 | 1.000000 | 32,187,525 | 13,668.17 | 320,801,624 |

The external PA1−C4 item-fill difference is −0.915688 and the cost difference is +274,187,478. The complete-basket proxy is tied at 1.0 and therefore does not discriminate even after tightening stock. Thus the direction of PA1−C4 replicates the UCI headline result for item fill (negative), but the magnitude is not comparable because the external replay uses a different dataset, universe, scale, and stress factor. The result is a reproducible external transportability check, not causal evidence.

The contrast was recorded under the same replication counts as the primary protocol: 120 paired deterministic paths and 1,000 bootstrap resamples. Since the external lead time and replay path are deterministic, all repeated paths are identical and the resulting confidence and bootstrap intervals are degenerate; this is reported explicitly in `results/dunnhumby_gate3_contrast_summary.csv` rather than presented as independent sampling evidence.

The older top-300/full-stock result remains in `dunnhumby_external_validation_summary.csv` for auditability. No third basket dataset was added: a clean, license-compatible, locally reproducible third source was not available in the current release, and an unverified download would weaken rather than strengthen external validity.
