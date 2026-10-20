# Basket-Aware Inventory Research Data Package

Prepared 20 October 2026 for the project “Basket-Aware Inventory Optimization under Demand and Supplier Lead-Time Uncertainty.”

## What is included

- `data/raw/uci_online_retail_ii.zip`: downloaded from the official UCI repository when available.
- `data/raw/m5/`: M5 Forecasting Accuracy files downloaded from the public Zenodo record that mirrors the competition release. The official Kaggle competition page is retained in the source manifest.
- `data/processed/uci_transaction_lines_clean.csv`: positive, non-cancelled merchandise transaction lines with normalized fields.
- `data/processed/uci_baskets.csv`: one row per invoice basket with product counts, units, and observed basket value.
- `data/processed/uci_weekly_product_demand.csv`: dense weekly product panel for the cleaned UCI merchandise universe.
- `data/processed/uci_copurchase_edges_train_only.csv`: product-pair features derived only from the training-period baskets.
- `data/processed/m5_schema_profile.json`: M5 file shapes, columns, and example rows.
- `data/processed/m5_weekly_product_demand_sample.csv`: small, reproducible M5 item-store weekly sample for schema and pipeline testing.
- `data/raw/dunnhumby/dunnhumby-complete-journey-data.zip`: separately sourced dunnhumby Complete Journey basket data; checksum and licence statement are in the source profile.
- `data/processed/dunnhumby/`: clean transaction lines, baskets, weekly demand panel, and source profile; never merged with UCI.
- `data/synthetic/inventory_scenarios.csv`: clearly labeled synthetic lead-time and cost scenarios. These are not observed records.
- `metadata/data_dictionary.csv`: field-level definitions, units, source, and observed/synthetic status.
- `metadata/source_manifest.csv`: provenance, URLs, checksums, and download status.
- `metadata/cleaning_summary.json`: counts and cleaning decisions used for the UCI outputs.
- `scripts/download_data.py`: pinned, checksum-aware downloader for UCI and M5.
- `scripts/prepare_data.py`: reproducible UCI cleaning, basket aggregation, weekly panel, co-purchase features, and M5 profiling.
- `scripts/build_synthetic_scenarios.py`: deterministic scenario-table generator.
- `scripts/run_experiment.py`: chronological forecast selection, M5 sample benchmark, four-policy UCI inventory simulation, paired stochastic replications, and result tables.
- `scripts/run_p0_analyses.py`: inventory-matched independent baseline, service-inventory frontiers, shuffled-score placebo, break-even shortage ratios, sensitivity analyses, and RQ3 stratification.
- `scripts/run_p1_analyses.py`: explicit missing contrasts, test-week bootstrap intervals, expanded alpha calibration, and rolling-origin window robustness.
- `scripts/run_phase3_calibration.py`, `scripts/run_phase3_test.py`, `scripts/summarize_phase3_primary.py`: interior-alpha validation, the all-scenario replay, matched-control and placebo contrasts, and level tables.
- `scripts/run_three_rolling_windows.py`: three chronological rolling-origin checks with training-only re-estimation.
- `scripts/prepare_and_run_dunnhumby.py`: separate external basket-data preparation and replay.
- `results/`: executed forecast metrics, replication-level inventory outcomes, all four paired policy contrasts, frozen configuration, frontiers, placebo results, matched-baseline results, break-even analysis, bootstrap intervals, rolling-origin outputs, sensitivity tables, and the generated results reports.

## Important interpretation limits

UCI Online Retail II is transaction data from a UK online retailer. It can support completed-transaction and basket reconstruction, but it does not contain on-hand inventory, purchase orders, supplier lead times, stockouts, lost sales, or historical inventory costs. The cleaned UCI data therefore support demand and co-purchase analysis only. Any inventory, lead-time, shortage, holding-cost, or service outcome in a later experiment must be simulated and labeled as such.

The M5 files are a separate Walmart retail forecasting benchmark. The dunnhumby files are a separate basket dataset. Neither is a valid row-level join partner for UCI because the datasets have different retailers, product identifiers, time periods, units, and data-generating processes. They are retained as separate validation or forecasting sources, not merged with UCI.

## Reproduce from a fresh checkout

Run these commands from the package root with the bundled project Python executable:

```powershell
$PY = "C:\Users\pc\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $PY scripts\download_data.py --datasets uci,m5
& $PY scripts\prepare_data.py --all
& $PY scripts\build_synthetic_scenarios.py
& $PY scripts\validate_package.py
& $PY scripts\run_experiment.py --replications 30
& $PY scripts\run_p0_analyses.py
& $PY scripts\run_p1_analyses.py
& $PY scripts\run_phase3_calibration.py
& $PY scripts\run_phase3_test.py
& $PY scripts\summarize_phase3_primary.py
& $PY scripts\run_three_rolling_windows.py
& $PY scripts\prepare_and_run_dunnhumby.py
```

The downloader skips an existing file only when its recorded checksum matches. If a source is unavailable, it writes the exact URL and status to `metadata/source_manifest.csv` and does not create a fake substitute.

## Recommended chronological evaluation protocol

For UCI, define the model-training period before deriving product universes, basket filters, association thresholds, graph edges, forecasts, or policy parameters. A reproducible starting split is:

- training: 2009-12-01 through 2011-06-30;
- validation: 2011-07-01 through 2011-08-31;
- test: 2011-09-01 through the last observed date in the cleaned data.

The executed primary experiment uses the corresponding Monday-start weeks: training through 2011-06-27, validation 2011-07-04 through 2011-08-29, and test 2011-09-05 through 2011-12-05. It does not use random train-test splits. Product selection, forecast selection, and co-purchase features are based only on the training period; validation selects the basket-buffer parameter, and the test period is used once. The primary replay covers all twelve scenarios with alpha = 1.5, a 1% inventory-matching band, 120 paired replications per scenario, and 1,000 bootstrap resamples. Alpha = 3.0 is retained only as historical Phase 2 evidence and sensitivity output. See `results/phase3_gate1_report.md` for the Gate 1 evidence summary.

For M5, the competition’s validation boundary is `d_1913`; the next 28 daily columns in `sales_train_evaluation.csv` are the public validation horizon. The preparation script does not tune a forecasting model or claim competition performance.

## Valid integration and non-integration

The package links UCI tables through `invoice_id`, `stock_code`, and `week_start`. It links M5 tables through the official M5 keys, such as `id`, `item_id`, `store_id`, `wm_yr_wk`, and `d`. It does not join UCI to M5. No supplier, inventory, cost, or stockout fields are fabricated.

## Synthetic scenarios

`data/synthetic/inventory_scenarios.csv` contains scenario assumptions only: review interval, lead-time distribution, holding cost, shortage penalty, ordering cost, and service target. The executed results are stored under `results/`. They use 2,731 products with at least 20 positive training weeks and replay 14 test weeks from 5 September 2011 through 5 December 2011. All inventory trajectories, lead times, costs, stockouts, unmet units, and policy outcomes remain simulated rather than observed.

## License and citation

Follow the source licenses and citation requirements. UCI Online Retail II is documented at https://archive.ics.uci.edu/dataset/502/online+retail+ii and has DOI https://doi.org/10.24432/C5CG6D. The M5 public copy is documented at https://doi.org/10.5281/zenodo.10203108 and originates from the Kaggle competition at https://www.kaggle.com/competitions/m5-forecasting-accuracy/data. The dunnhumby source page is https://www.dunnhumby.com/source-files/ and the documented public release mirror is https://github.com/bltap-plmarket/dunnhumby-complete-journey/releases/tag/v1.0-data; the mirror states DbCL-1.0. Check each source page and licence before redistribution or publication. The public project repository is https://github.com/TalhaZabir/basket-aware-inventory-research.

## Public repository release

The public release publishes code, manuscript sources, the final DOCX, metadata, figures, frozen configurations, and result tables. Large raw and derived data files are excluded through `.gitignore`; use the documented download and preparation scripts to recreate them. See `PUBLIC_RELEASE.md` for the exact primary-analysis configuration and release boundary.
