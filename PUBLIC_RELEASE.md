# Public release profile

This repository publishes the reproducible code, manuscript, metadata, figures, frozen configurations, and result tables for the basket-aware inventory research project.

Large raw and derived data files are intentionally excluded from Git history. They are reproducible through the download and preparation scripts, with source URLs, checksums, schema notes, and license statements in `metadata/source_manifest.csv`, `metadata/data_dictionary.csv`, and `data/processed/dunnhumby/dunnhumby_source_profile.json`. This avoids GitHub's large-file limits and does not redistribute source data beyond the applicable terms.

The public primary analysis is frozen as:

- alpha = 1.5, selected at an interior validation value;
- 1% inventory-matching tolerance;
- 120 paired stochastic replications in S05;
- 1,000 paired bootstrap resamples;
- three rolling-origin windows;
- primary contrast PA1 minus C4, with PA1 minus C1 and graph placebos retained.

The final manuscript is `basket_aware_inventory_full_manuscript_sections_1_to_10.docx`; the source sections and assembly scripts are included in this repository.
