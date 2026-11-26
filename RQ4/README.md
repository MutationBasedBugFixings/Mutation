# RQ4 reproducible 92-bug sample

This directory contains the sampling script for the RQ4 dynamic-validation cohort.

## Important population definition

The RQ4 population is the 809 non-Chart Defects4J bugs: 835 original records minus 26 Chart bugs whose buggy revisions could not be retrieved. Do not substitute the RQ5 `strict_eligible` subset for this RQ4 population.

## Why the script requires a separate assignment file

`cleaned_bug_operator_sets.csv` is an RQ5-derived mapping source. Its operator fields can contain multiple syntactic operators and do not, by themselves, establish the single RQ4 operator stratum used in the manuscript's sample table. The script therefore refuses to select an arbitrary first operator.

Prepare `data/rq4_operator_assignments.csv` with exactly one reviewed row for each of the 809 non-Chart bugs:

```csv
project,bug_id,rq4_operator
Lang,Lang1,CI
...
```

Allowed `rq4_operator` values: `CI`, `MCR`, `MRV`, `LOR`, `VA`, `ROR`, `Others`.

For composite/multi-operator fixes, assign the RQ4 stratum using the same documented annotation rule used in the RQ1/RQ4 analysis. Do not infer it from column order.

## Inputs

- `transparency/defects4j.csv`: original Defects4J population (must contain project and bug ID columns).
- `RQ4/data/cleaned_bug_operator_sets.csv`: RQ5-derived operator mapping source, used for traceability/reconciliation.
- `RQ4/data/rq4_operator_assignments.csv`: reviewed RQ4 semantic/operator-stratum assignment for all 809 bugs.

## Run

From the repository root:

```bash
python RQ4/scripts/reconstruct_sample.py \
  --population transparency/defects4j.csv \
  --mapping RQ4/data/cleaned_bug_operator_sets.csv \
  --assignments RQ4/data/rq4_operator_assignments.csv \
  --outdir RQ4/sampling \
  --seed 20261126
```

The script validates that the population contains exactly 809 unique non-Chart bugs and that all 809 have one reviewed RQ4 stratum. It then selects 92 bugs without replacement, using the manuscript's operator quotas and proportional allocation across projects within each operator stratum.

## Outputs

- `sample_92.csv`
- `project_operator_allocation.csv`
- `operator_strata_audit.csv`
- `population_reconciliation.csv`
- `sampling_provenance.csv`

The sample is reproducible for the same inputs, script version, and seed. The script intentionally stops rather than emitting a misleading final sample if the population or assignments are incomplete.
