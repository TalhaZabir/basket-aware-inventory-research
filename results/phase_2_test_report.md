# Phase 2 frozen test report

This is the single guarded Phase 2 replay under parent validation hash `677bfb9345b95983bf1fb63fee0e4dd8da3ac63b372530d6c76587aaf5482e44`. No test result was used to tune alpha, tau, graph construction, or matching.

C2: item-fill gain 0.020192 [0.015561, 0.023452], basket-fill gain 0.133105 [0.068080, 0.183554], cost difference 620637.35
C3: item-fill gain 0.021681 [0.017316, 0.024725], basket-fill gain 0.121145 [0.055305, 0.172394], cost difference 613799.70
C4: item-fill gain 0.077016 [0.071422, 0.079621], basket-fill gain 0.240404 [0.210554, 0.251689], cost difference 237087.11
C5: item-fill gain 0.004455 [0.000907, 0.007143], basket-fill gain 0.089648 [0.040327, 0.125551], cost difference 728797.85
PA1: item-fill gain 0.035885 [0.032089, 0.038389], basket-fill gain 0.143115 [0.091722, 0.181351], cost difference 528500.10
PA2: item-fill gain 0.067330 [0.061893, 0.070336], basket-fill gain 0.236627 [0.205323, 0.251542], cost difference 304999.02
PA3: item-fill gain 0.003683 [0.000975, 0.005529], basket-fill gain -0.003817 [-0.015675, 0.001377], cost difference 732869.35

The matched rows use the preregistered target grid plus one interpolation replay when needed. Results are based on 30 stochastic lead-time replications and one deterministic lead-time path per deterministic scenario; both deterministic- and stochastic-planning labels were evaluated on the deterministic path. They are not the Phase 3 100-replication or bootstrap analysis.

Files: `phase2_test_config.json`, `phase2_test_results.csv`, `phase2_test_summary.csv`, `phase2_test_matched.csv`, `phase2_test_matched_summary.csv`, and `run_log.csv`.
