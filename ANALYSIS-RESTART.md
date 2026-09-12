# Analysis Restart: Working Checklist

Branch: `analysis-restart`. Started 2026-09-11.

This file tracks the rebuild of the empirical analysis described in `README.md`
("What we are doing now"). It is a working log, not a replacement for the
README: design decisions that become final should be moved there.

Scope: rebuild estimation, reporting, and discussion from the six cleaned
inputs already tracked in Git. No new data collection or initial cleaning.
The CDMX business-density analysis stays unchanged.

## Checklist

- [ ] Validate and freeze the six cleaned inputs, documenting units and coverage.
- [ ] Finalize centers, camera grouping, and control eligibility rules.
- [ ] Construct circles at all radii with stable unit IDs.
- [ ] Rebuild incident counts, covariates, and a complete unit-time panel.
- [ ] Define and verify the common retained sample for radius comparisons.
- [ ] Estimate the main model and required robustness specifications.
- [ ] Produce consistent tables and interpret magnitudes.
- [ ] Update estimation and results sections of the thesis.
- [ ] Decide whether to add doubly robust DiD and/or an event study.

## Decision log

Record each resolved design decision here with its date and rationale, so the
README can be updated from a single place.

| Date | Decision | Rationale |
| --- | --- | --- |
| | | |
