# Phase 1 execution audit

## Repair

The Phase 1 test script now checks `results/run_log.csv` before reading the test demand. If a `phase1_test_frozen` primary replay is already present, it exits without writing outputs. This prevents accidental overwrites and repeated use of the held-out window under the same configuration.

## Frozen evidence count

- Primary replay: 1
- Duplicate invocation: 1, marked `duplicate_invocation_ignored`
- Counted stochastic replications: 30 per stochastic scenario
- Counted deterministic paths: 1 per deterministic scenario
- Additional independent evidence from the duplicate: 0

The duplicate invocation is retained in the log for auditability and is not used in any estimate or interval. The held-out test was not rerun after the guard was installed. Therefore Phase 1 is complete as an auditable phase with a documented execution exception; the duplicate does not create a second estimate.

## Guard check

A post-repair invocation was attempted. The script refused to rerun with the message that a frozen primary replay was already logged, and no result file or log row was added by that check.

## Interpretation

The primary matched-inventory result remains the only counted Phase 1 test result. The later Phase 3 replication and bootstrap work must use a new preregistered configuration and separately versioned output files.
