# Phase 1 validation calibration report

The phase was validation-only; the held-out test window was not read for scoring or tuning.

The validation winner by aggregate WAPE was `empirical_quantile`. Forecast metrics are in `phase1_forecast_validation.csv`; the ladder includes moving averages, seasonal-naive, Croston, SBA, TSB, a prior-year seasonal-ratio forecast, and an empirical-quantile point forecast.

Independent service calibration selected the closest realised item-fill target per scenario and policy by multiplying the internal residual scale by one of [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 9.0]. The within-three-percentage-point acceptance result was `True` across 24 scenario-policy rows.

The calibration is not a test result. If the acceptance test fails, the failure and its magnitude must be reported and the forecast/policy must not be declared operationally calibrated.

Files: `phase1_forecast_validation.csv`, `phase1_policy_validation_calibration.csv`, `phase1_validation_config.json`, and `run_log.csv`.
