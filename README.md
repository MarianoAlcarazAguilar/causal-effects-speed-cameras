# Speed Cameras Thesis: Working Context

Last updated: 2026-09-11.

This repository contains Mariano's thesis on traffic incidents and speed cameras
in Mexico City, including the transition from Fotomultas to Fotocivicas on
April 22, 2019. The existing empirical work uses circular geographic units,
propensity score matching (PSM), and difference-in-differences (DiD).

## What we are doing now

**Rebuild the empirical analysis from the existing cleaned inputs, without
repeating data collection or initial cleaning. Keep the CDMX business-density
analysis unchanged.**

This is not a restart of the whole thesis. Alberto's feedback says chapters 1
and 2, and most of chapter 3, are largely ready. The priority is to improve the
estimation, reporting, and discussion of results.

The old scripts and notebooks are references, not an approved new pipeline.
New estimates have not yet been produced under the revised design. Do not treat
old matches, panels, or cached objects as the starting sample for the rebuild.

## Clean inputs to reuse

These six inputs are tracked in Git (roughly 18 MB combined). Paths are relative
to the repository root.

| Input | Purpose |
| --- | --- |
| `data/classified-incidents.parquet` | Filtered and classified incidents, with dates and coordinates; aggregate into the new circles. |
| `data/fotocivicas-ubicacion-puntos/` | Camera locations. Keep the `.shp`, `.shx`, `.dbf`, and `.prj` files together. |
| `data/vialidades.json` | Road geometries and attributes. |
| `data/metro-station-coordinates.parquet` | Metro station coordinates, previously geocoded outside this repository. |
| `data/afluencia-metro-semanal.parquet` | Processed Metro ridership used by the existing feature builder. |
| `data/volumen-total-mensual.parquet` | Processed monthly traffic volume for incident rates. |

Reusing cleaned data also means retaining its existing filtering, classification,
and time-window decisions. First validate schema, coverage, coordinates, missing
values, and units. This is a validation step, not a request to clean everything
again. Changing those decisions may require the original data.

The volume-generation notebook divides volume by 1,000. Verify the saved data
and resulting rate units before rescaling coefficients; do not assume that the
old rates are incorrectly scaled.

## Preserve the business-density analysis

Reference notebook: `scripts/writing/mexico-city-business-density.ipynb`.

Preserve its existing inputs and outputs separately:

- `data/raw-data/businesses-cdmx.json`: saved Google business-count responses.
  Requerying today would not reproduce the same historical counts.
- `data/localidadurbana/`: boundary shapefile used for geographic coverage.
- The existing `data/classified-incidents.parquet`: this analysis uses incidents
  to select its hexagons. Do not overwrite this snapshot with a new cleaning.
- `data/vialidades.json`.
- `data/graphs/establecimientos-en-la-cdmx.png` and
  `data/graphs/distribucion-establecimientos-cdmx-hexagonos.png`.

**The business JSON, boundary layer, and figures are currently ignored by Git.**
A fresh clone contains the notebook but not everything required to reproduce
this part. Keep an external backup; do not delete these local files.

## Advisor feedback: priorities

The following records Alberto's requested changes, not completed work:

1. **Comparable samples across radii.** Use the strictest trimming for the main
   radius comparisons. State that the estimand is an ATT for the retained treated
   sample, not automatically all camera locations. Radius-specific trimming can
   be a robustness exercise in an appendix.
2. **Clear tables.** Report observations, R-squared, control means and standard
   deviations, coefficient units, and model/sample notes. Put treatment and its
   time interaction first and fixed-effect indicators last. Report relevant
   coefficient sums with their uncertainty and significance. Use decimal points
   and readable rate scales.
3. **Adjusted PSM + DiD.** Keep matching without replacement and clustering by
   geographic unit. Add pre-treatment propensity-score covariates interacted
   with post-treatment or time indicators. Alberto excludes the pre-treatment
   outcome from this added-control specification. These adjustments do not by
   themselves establish that all matching-related uncertainty is accounted for.
4. **Broader interpretation.** Discuss coefficient magnitudes even when they are
   statistically insignificant, relative to control outcomes and comparable
   Mexican studies. Include unmatched DiD as an appendix comparison.

Optional extensions: doubly robust DiD based on Sant'Anna and Zhao (2020), and
an event study. Package/estimator choice still needs to be checked against the
actual panel and treatment timing; it has not been implemented.

## Design decisions still open

- Define fixed centers and stable IDs before comparing radii. The proposal is
  to examine overlaps at the largest radius, possibly group nearby cameras,
  and check camera inclusion at the smallest radius. **No grouping or exclusion
  rule has been finalized.** Excluding a camera from the sample does not remove
  its potential influence on nearby controls.
- Decide how to generate candidate controls. The old approach uses a grid and
  removes camera-containing circles; the new eligibility and buffer rules are
  still pending.
- Fixed centers alone do not guarantee the same comparison: eligibility,
  trimming, matching, and missing-data filters can still change included IDs
  and weights. Explicitly check the retained sample at every radius.
- Decide how to handle the April 22 treatment date in monthly outcomes,
  especially the partially treated month of April 2019.
- Ensure eligible unit-period combinations with zero incidents remain in the
  panel, rather than disappearing during aggregation.
- Audit coefficient labels and table exports against the fitted models. Do not
  mix estimates, standard errors, or p-values from different specifications.

## Next work sequence

- [ ] Validate and freeze the six cleaned inputs, documenting units and coverage.
- [ ] Finalize centers, camera grouping, and control eligibility rules.
- [ ] Construct circles at all radii with stable unit IDs.
- [ ] Rebuild incident counts, covariates, and a complete unit-time panel.
- [ ] Define and verify the common retained sample for radius comparisons.
- [ ] Estimate the main model and required robustness specifications.
- [ ] Produce consistent tables and interpret magnitudes.
- [ ] Update estimation and results sections of the thesis.
- [ ] Decide whether to add doubly robust DiD and/or an event study.

## Repository map and execution status

| Location | Role |
| --- | --- |
| `causal-effects-speed-cameras/main.tex` | Thesis entry point. |
| `causal-effects-speed-cameras/Chapters/` | Chapter sources. |
| `scripts/auxiliar/` | Earlier data preparation and exploration notebooks. |
| `scripts/grid_builder.py` | Existing geographic-unit construction code. |
| `scripts/ps_features_builder.py` | Existing feature construction code. |
| `scripts/ps_matching.py` | Existing matching code. |
| `scripts/effect_estimation.py` | Existing estimation code. |
| `scripts/writing/` | Analysis and thesis-output notebooks. |
| `repaso-tesis/index.html` | Local interactive refresher, including module 0; not tracked. |

There is not yet a verified, single-command rebuild or a pinned environment for
the revised analysis. Some notebooks contain old relative paths and manual
steps. Run future work with explicit project-relative paths and record the
environment rather than assuming the historical notebooks execute unchanged.

## Git and backups

Remote: `git@github.com:MarianoAlcarazAguilar/causal-effects-speed-cameras.git`.

Git tracks this README, selected LaTeX sources and bibliography/style files,
analysis scripts/notebooks, and the six cleaned inputs. `.gitignore` uses an
allowlist: new files are ignored unless explicitly allowed.

Raw data, old grids/matches/panels, `data/pickle_objects/`, most figures, PDFs,
local tutorials, and backups are intentionally excluded. The original sources
and manual traffic-volume extraction should still be backed up externally.
`.gsheet` files are links, not standalone backups of their spreadsheets.

A clone is therefore not a complete archive, and may lack figures required to
compile the thesis. Old Git history may still contain files excluded from the
current tree.

Do not delete local data as part of routine cleanup, overwrite the business
snapshot, or commit credentials. A Google API key was found in the versioned
business notebook; rotation and removal remain pending until confirmed.

When resuming work, read this README first, inspect `git status`, and update the
decisions and checklist as work is actually completed.
