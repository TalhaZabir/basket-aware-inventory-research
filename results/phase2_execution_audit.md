# Phase 2 execution audit

## Frozen execution

- Parent validation configuration: `677bfb9345b95983bf1fb63fee0e4dd8da3ac63b372530d6c76587aaf5482e44`.
- Frozen test configuration hash: `ce09b3fdfbae9f723fd8cf6f697ac7f6202a5740f6a4be92998c6abd158c88be`.
- Test status in `run_log.csv`: one `primary_replay` row for `phase2_test_frozen`; no duplicate test row.
- Test specification: alpha 3.0, PA3 threshold quantile 0.50, empirical-quantile forecast, safety multiplier 6.0, one deterministic lead-time path per deterministic scenario, and 30 stochastic lead-time replications per stochastic scenario. Both planning labels were evaluated on deterministic paths; no extra deterministic lead-time draw was introduced.
- Matching specification: the frozen target grid plus at most one linear-interpolation replay; maximum absolute relative inventory gap in the test matched file was 2.23%, below the 5% tolerance.
- Output counts: 3,822 policy rows and 3,822 matched rows.

## Guard verification

After the primary replay completed, a second invocation of `run_phase2_test.py` was attempted as a guard smoke test. It exited before simulation with: `Refusing to rerun the Phase 2 test window: a frozen primary replay is already logged.` No second test replay was run and no duplicate row was appended.

## Interpretation boundary

The test replay freezes the Phase 2 policy comparison only. It does not replace the planned Phase 3 bootstrap, placebo intervals, rolling-origin robustness check, or wider sensitivity analysis.
