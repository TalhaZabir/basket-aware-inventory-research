# 1. Title and abstract

## Study title

Basket-Aware Inventory Control under Demand and Lead-Time Uncertainty

## Abstract

Retailers replenish products separately even though customers purchase multiple products together and deliveries are uncertain. This study tests whether basket-aware buffering adds service value beyond independent replenishment at tightly matched simulated inventory, and whether any gain remains after popularity and graph-placebo controls.

The primary analysis uses UCI Online Retail II to reconstruct completed invoice baskets, weekly demand, and a training-only co-purchase graph. Three transparent moving-average/seasonal-naive forecasts are selected chronologically per product. A partner-protection policy is compared with an inventory-matched independent control, a popularity-only control, and rewired, shuffled, and stale-graph placebos. The frozen primary replay uses interior alpha = 1.5, a 1% inventory-matching band, 120 stochastic replications, and 1,000 paired bootstrap resamples in the moderate-variance S05 scenario. Three rolling windows and a separate dunnhumby Complete Journey basket dataset provide robustness checks.

In S05, PA1 versus the matched independent control increased item fill by 0.0270 (95% replication interval 0.0263–0.0276) and complete-basket fill by 0.0944 (0.0803–0.1119), at an average inventory difference of 10,343 units and a cost increase of 231,712. Against popularity-only C4, PA1 was worse: item fill −0.0261 and basket fill −0.0667, with cost +168,736; the 1,000-resample intervals excluded zero for all three contrasts. PA1 also exceeded C2, C3, and C5 on both service measures, but those placebo comparisons do not establish that the original edge topology caused the difference. These results support a conditional service trade-off, not a graph-specific advantage. Inventory, supplier, stockout, and historical cost fields are absent, so policy outcomes remain simulated.

**Keywords:** basket-aware inventory control; market-basket analysis; complete-basket fulfilment; lead-time uncertainty; inventory simulation; co-purchase graph; retail forecasting

**Data and code availability:** The reproducible package, cleaning scripts, manifests, figures, and analysis outputs are included in the project source under [`research_data_package/`](research_data_package/). The public source records are [UCI Online Retail II](https://doi.org/10.24432/C5CG6D) and the separate [M5 benchmark release](https://doi.org/10.5281/zenodo.10203108); the datasets are not row-level mergeable.

# 2. Introduction

## 2.1 The inventory problem

Retail inventory control must balance stock, reorder timing, service, and replenishment cost when demand and deliveries are uncertain. Product-level control may be adequate for independent items but can miss the order-level consequence of one unavailable product in a multi-item basket. The operational objective is therefore broader than forecast error: the study reports forecasts, item service, whole-basket service, inventory exposure, unmet demand, and cost under explicit uncertainty.

## 2.2 Why basket relationships matter

Transaction baskets reveal which products are purchased together. Support, conditional purchase probability, Jaccard similarity, and lift are useful descriptive features, but associations may reflect promotions, segments, seasonality, price, assortment, or common availability rather than complementarity. Because item fill and whole-order fulfilment can diverge, this study treats co-purchase as a training-period feature and evaluates both outcomes in a controlled replay; complete-basket fulfilment remains a proxy based only on observed completed baskets.

## 2.3 Why supplier lead-time uncertainty matters

Replenishment timing determines demand covered before stock arrives. Variable delivery can make an expected-lead-time plan under-protect late arrivals, but the effect depends on costs, intermittency, and the replenishment rule. UCI has no purchase-order or receipt data, so the study uses deterministic, low-variance, high-variance, and right-skewed synthetic lead-time scenarios as stress tests rather than estimates of the original suppliers.

## 2.4 Study setting, data boundary, and reproducibility

The primary source is UCI Online Retail II, covering December 2009 through December 2011 (Chen, 2019). The package reconstructs transaction lines, invoice baskets, weekly demand, and training-period product-pair features. M5 is retained as a separate benchmark because its retailer, identifiers, periods, and units differ; no row-level join or supplier, inventory, stockout, or cost field is fabricated. Checksums, scripts, dictionaries, scenarios, configurations, and results are included under `research_data_package/`; source provenance and the UCI 2019 donation-year/2012 citation-widget discrepancy are documented in Appendix A.

## 2.5 Research questions

The study addresses three linked questions: (Q1) Can a reproducible public transaction package support chronological demand forecasting, basket reconstruction, and training-only co-purchase features suitable for inventory-policy simulation? (Q2) Under common forecasts and controlled synthetic lead-time and cost scenarios, does a basket-aware policy improve simulated total cost, item fill rate, or complete-basket fulfilment relative to independent item-level replenishment? (Q3) Under what conditions of basket concentration, graph stability, shortage penalty, holding cost, and lead-time variability does basket-aware control help, have little effect, or perform worse?

The first question is addressed by the completed data audit. The second is addressed by the primary and inventory-matched policy comparisons, and the third by the frontier, placebo, cost-ratio, graph, basket-definition, universe, stockout-model, and stratified analyses. All policy conclusions remain conditional on synthetic inventory and supplier assumptions.

## 2.6 Contribution and scope

The contribution is an empirical integration and boundary-condition analysis. It connects transaction-derived basket structure with demand forecasting and stochastic lead-time inventory simulation, preserves chronological leakage control, separates forecast metrics from inventory outcomes, and compares four policies under common inputs. The study position is deliberately empirical: it evaluates when the added basket-aware buffer changes simulated service, inventory, and cost, and reports the controls and uncertainty needed to interpret those changes. The operational evidence boundary and remaining data requirements are consolidated in Section 8.

# 3. Targeted literature review

## 3.1 Review scope, search protocol, and evidentiary approach

The review was redesigned as a reproducible multi-stream search protocol covering: (1) market-basket and co-purchase representation; (2) multi-item fulfilment and service-level theory; (3) censored demand, stockouts, and substitution; (4) data-driven or feature-based newsvendor models; (5) forecast-then-optimise and machine-learning inventory control; (6) intermittent demand, including Croston, Syntetos–Boylan, and TSB methods; (7) probabilistic forecast scoring, safety stock, and quantile decisions; (8) graph, grouped, and hierarchical forecasting; and (9) stochastic lead times and joint replenishment.

Scopus and Web of Science Core Collection were specified as the target databases. The protocol was dated 20 October 2026, with publication years 1994–2026, English-language records, and article, review, and conference-paper document types. The reporting structure follows PRISMA-S guidance (Rethlefsen et al., 2021), but this is a targeted literature review rather than a completed systematic review: the project environment did not provide authenticated database access or export files. No Scopus or Web of Science hit, duplicate, screening, or inclusion counts are therefore reported. The strings below are preserved as a reproducible search specification for a future licensed run. Open bibliographic, publisher, DOI, repository, and official dataset records were used for the present metadata cross-check and for adding recent sources.

Scopus `TITLE-ABS-KEY` searches:

- `("market basket" OR co-purchase OR complement* OR "joint demand") AND (inventory OR replenishment OR "service level" OR fulfilment OR fulfillment)`
- `(stockout* OR "lost sales" OR censored OR substitution) AND (demand OR sales) AND (forecast* OR inventory OR newsvendor)`
- `(newsvendor OR "safety stock" OR "service level") AND ("data-driven" OR feature-based OR "machine learning" OR "quantile regression" OR "predict then optimize" OR prescriptive)`
- `("intermittent demand" OR Croston OR "Syntetos-Boylan" OR SBA OR TSB) AND (forecast* OR inventory)`
- `("probabilistic forecast*" OR CRPS OR "quantile loss" OR pinball OR "hierarchical forecast*" OR reconciliation OR graph*) AND (retail OR demand OR sales OR inventory)`
- `("lead time" AND uncertainty) AND (inventory OR replenishment)`

Web of Science equivalents use `TS=` in place of `TITLE-ABS-KEY`, with the same six strings, year and language filters. Screening records should be deduplicated by DOI, then screened on title and abstract, followed by full-text eligibility. Include studies that connect demand or sales information to an inventory, service, replenishment, newsvendor, or forecast-decision problem; exclude purely descriptive basket mining, papers without a demand or inventory decision, and applications whose operational setting cannot transfer to stock control. Backward and forward citation chasing is recorded separately from the database results.

The evidence is interpreted by mechanism and setting. A stylized two-product result motivates a mechanism but does not establish performance in a large transaction-derived SKU system; a data-driven forecast result does not establish lower inventory cost; and a dataset description establishes available fields rather than inventory truth. The resulting synthesis therefore reports the search boundary, included evidence streams, and the distinction between observed data and simulated outcomes.

## 3.2 Market-basket and co-purchase representation

Association-rule mining provides a practical method for finding frequent itemsets and product relationships in transaction baskets (Agrawal & Srikant, 1994). Work on market-basket analysis in heterogeneous store environments shows that product mix and availability context can affect observed associations (Chen et al., 2005). These studies support using support, pair counts, conditional probabilities, Jaccard similarity, and lift as descriptive features, but they do not make the resulting edges causal or operationally optimal.

The key implication is leakage control: support, pair counts, thresholds, and weights must use only pre-evaluation baskets. The supplied graph uses baskets through 30 June 2011; density and edge stability are reported because sparse products, assortment changes, promotions, and censoring can destabilize associations.

## 3.3 Multi-item inventory and whole-order fulfilment

Multi-item inventory research distinguishes item-level service from the probability that all items in a customer order are available. Hausman, Lee, and Zhang (1998) examine joint demand fulfilment under independent order-up-to policies, while Song (1998) studies order fill rate in a multi-item base-stock system with compound-Poisson customer orders. Hill and Pakkala (2007) also treat retail orders containing multiple items and evaluate the consequences of immediate and delayed dispatch.

This literature establishes the whole-order outcome, but usually uses analytical or stylized demand. The study therefore uses complete-basket fulfilment as a replay proxy for observed completed baskets, not for all attempted demand.

## 3.4 Censored demand, stockouts, and substitution

When an item stocks out, recorded sales can be a lower bound on latent demand rather than an unbiased demand observation. Subramanian and Harsha (2021) model unobserved lost sales, while Trapero, de Frutos, and Pedregal (2024) connect censored-demand forecasting to lost-sales inventory policies through a Tobit Kalman filter and newsvendor simulation. Akçay, Li, and Natarajan (2020) show that stockout-based substitution can affect category-level service and initial stocking decisions; Ergin, Gümüş, and Yang (2022) provide empirical evidence that shortages can shift sales across locations. These studies establish why sales-only panels can understate demand and why substitution can change both demand measurement and fulfilment outcomes.

Because UCI has no stockout, attempted-order, or substitution fields, the basket measure is a replay proxy rather than a censored-demand correction.

## 3.5 Data-driven newsvendor, forecast-then-optimise, and ML inventory control

The data-driven newsvendor literature replaces a fully specified demand distribution with empirical or feature-based decision rules. Huber et al. (2019) compare machine-learning and quantile-regression approaches from data to newsvendor decisions. Van der Laan et al. (2022) address on-target service levels with distributionally robust chance constraints, while Lin et al. (2022) add a profit-risk constraint for feature-based newsvendor decisions. Wang, Deng, and Zhang (2025) extend data-driven ordering to target-oriented newsvendor problems with censored demand and Kaplan–Meier correction.

Forecast-then-optimise work makes the decision objective explicit: Elmachtoub and Grigas (2022) formalize Smart Predict-then-Optimize, van der Haar et al. (2024) use inventory-control losses, and Bergsma et al. (2025) review integrated ML approaches. This study uses a simpler ladder in which point forecasts and residual dispersion feed a fixed weekly simulator; no ML model is trained on inventory cost.

## 3.6 Intermittent demand and demand classification

Intermittent demand contains many zero periods and irregular positive quantities. Croston’s method and the Syntetos–Boylan Approximation address demand size and inter-demand intervals, while the Teunter–Syntetos–Babai method updates demand occurrence probability and is useful when obsolescence or changing activity is important (Syntetos & Boylan, 2005; Teunter, Syntetos, & Babai, 2011). Boylan and Syntetos (2021) consolidate this stream, and Yang et al. (2021) evaluate a modified TSB method on M5-derived and empirical data. More recent work combines probabilistic forecasts for intermittent demand and evaluates both forecast and inventory performance (Wang, Kang, & Petropoulos, 2024).

The UCI panel is intermittent, so ADI and CV² are relevant diagnostics. The primary experiment uses recent-four-week, recent-eight-week, and seasonal-naive candidates rather than Croston, SBA, or TSB; this keeps the policy comparison transparent without claiming that moving averages are optimal.

## 3.7 Probabilistic scoring, hierarchical and graph forecasting, and service-level theory

Probabilistic forecast quality is not established by a point-error metric alone. Proper scoring rules such as CRPS and quantile or pinball loss evaluate the full predictive distribution or selected quantiles (Gneiting & Raftery, 2007). Spiliotis et al. (2021) show how empirical and simulated quantiles can be evaluated for both forecast performance and inventory utility on M5, while Theodorou, Spiliotis, and Assimakopoulos (2025) document that forecast accuracy and inventory performance can have a weak or policy-dependent relationship. Petropoulos et al. (2022) provide a broad review of forecasting practice and evaluation.

Rangapuram et al. (2021) develop coherent hierarchical forecasts, but the present co-purchase graph is not a sales hierarchy and does not reconcile forecasts. Omar et al. (2023) provide a closer basket-data precedent: graph-derived connectivity variables enter demand forecasts and an omnichannel stock-control evaluation. The present study differs by holding the point-forecast ladder fixed and testing a graph buffer at matched simulated inventory. Safety-stock theory connects demand uncertainty, lead-time demand, and asymmetric costs; accordingly, the study reports forecast metrics separately from item fill, complete-basket fulfilment, inventory, unmet units, and cost.

## 3.8 Complementary products, correlated demand, and joint replenishment

Complementary-product and correlated-demand studies show why independent control can be insufficient: Abbott and Palekar (2008), Zhang et al. (2012), and Feng et al. (2015) examine cross-effects, correlated demand, and joint-replenishment costs. Poormoaied and Atan (2020) and Poormoaied (2022) study two-product complementary systems, while Peng et al. (2022) review joint replenishment. Rahimi et al. (2026) extend this stream to multi-item periodic review with both temporal and cross-item dependence. These results motivate a demand-dependence and service-coordination layer but do not establish that a transaction-derived graph improves a many-SKU system.

## 3.9 Lead-time uncertainty and service risk

Song (1994), Song et al. (2010), and Hansen et al. (2023) show that lead-time uncertainty interacts with demand, cost, and service constraints. This supports crossing deterministic and stochastic lead times with independent and basket-aware control while varying holding cost and shortage penalty; all project lead-time distributions are synthetic because UCI has no supplier events.

## 3.10 Synthesis and study position

The reviewed streams support seven design propositions: (1) basket relationships are useful descriptive features but are sensitive to availability, assortment, and confounding; (2) complete-basket fulfilment is distinct from item fill and should be reported separately; (3) stockout censoring and substitution can bias sales-based demand estimates, but UCI lacks the fields needed to correct them; (4) feature-based newsvendor and forecast-then-optimise methods make the decision objective explicit, while the present experiment uses a simpler fixed policy simulator; (5) intermittent-demand methods and probabilistic scoring are relevant for sparse panels but are not the primary forecast ladder here; (6) graph features are not equivalent to hierarchical forecast reconciliation; and (7) lead-time uncertainty and service-level costs must be evaluated jointly with the replenishment rule.

The targeted search protocol and open-record cross-check identified adjacent studies across all nine streams. The evidence base supports positioning this project as a public-data simulation bridge between basket analysis, demand forecasting, service-level inventory control, and lead-time uncertainty. A definitive claim that no directly matching study exists is not made because licensed Scopus/Web of Science exports were unavailable in the project environment. The defensible gap is narrower: existing streams separately study co-purchase structure, correlated demand, forecast-driven replenishment, or stochastic inventory control, while this study tests a transparent transaction-derived graph buffer against popularity-only control under matched simulated inventory and reports where the graph signal does and does not survive.

