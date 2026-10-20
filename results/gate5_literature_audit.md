# Gate 5 literature audit

## Search status

The manuscript now labels Section 3 a targeted literature review. Scopus and Web of Science Core Collection were not searchable from the project environment because no authenticated institutional session or export was available. It would be methodologically incorrect to report hit, deduplication, screening, or inclusion counts. The manuscript therefore reports the exact planned strings and the boundary of the search rather than a fabricated PRISMA flow.

The planned search covers nine streams: market-basket and co-purchase representation; multi-item fulfilment and service-level theory; censored demand, stockouts, and substitution; data-driven newsvendor models; forecast-then-optimise and machine-learning inventory control; intermittent demand; probabilistic scoring and safety stock; graph and hierarchical forecasting; and stochastic lead times.

## Reproducible query record

The six query families are preserved in Section 3.1 in Scopus `TITLE-ABS-KEY` syntax. Web of Science uses the same strings with `TS=`. The intended filters are English records published from 1994 through 2026, including articles, reviews, and conference papers. A licensed rerun should export RIS or CSV from each database, deduplicate by DOI and normalized title, record title/abstract exclusions, and archive the final included set with the repository.

## Metadata verification boundary

The reference list was checked against publisher, repository, DOI landing-page, and open bibliographic records available without a licensed database. The recent additions are: Omar et al. (2023), DOI 10.1016/j.ijpe.2022.108748; van der Haar et al. (2024), DOI 10.1016/j.ejor.2024.07.004; Wang et al. (2024), DOI 10.1016/j.ejor.2024.01.032; Theodorou et al. (2025), DOI 10.1016/j.ejor.2024.12.033; Bergsma et al. (2025), DOI 10.1016/j.orp.2025.100367; and Rahimi et al. (2026), DOI 10.1016/j.ejor.2025.12.042. The M5, PRISMA-S, and UCI records are also linked in the manuscript.

The DOI strings are retained as the machine-checkable identifiers. A full Crossref API audit of every entry remains a release task because outbound API access was unavailable in this environment; no claim of a completed Scopus, Web of Science, or Crossref census is made. Uncited Baykal-Gürsoy and Berry entries were removed. The remaining entries are cited in Sections 2–3 or in the data and methods sections.

## Positioning after the audit

The defensible gap is not that no prior study exists. Omar et al. (2023) already show that basket-derived graph variables can enter retail forecasting and stock-control analysis. The narrower contribution here is a controlled comparison of a transparent transaction-derived graph buffer against popularity-only control at matched simulated inventory, with placebo graphs, stochastic lead-time scenarios, and a stratified test of when low-popularity/high-lift relationships can matter.
