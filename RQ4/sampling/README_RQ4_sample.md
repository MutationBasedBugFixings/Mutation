# RQ4 reconstructed 92-bug sample

## Population reconstruction
The uploaded `Defects4j_full(1).xlsx` contains 835 rows:
- 803 records in the main annotation block, including 26 Chart bugs.
- 32 additional Jsoup records in the final block.
After excluding Chart, the RQ4 population is 777 + 32 = 809 bugs across 16 non-Chart projects.
The reconstructed population has 809 unique (project, bug_id) keys.

## Sampling method
- Fixed seed: 20261126
- Sample size: 92
- Two-stage proportional stratified sampling:
  1. Allocate the sample proportionally across all 16 projects.
  2. Within each project, allocate proportionally across primary syntactic-operator strata.
- Sampling without replacement.
- Primary operator rule: use the first operator code listed in the `Mutant ID` field. If no recognized target code is present, or the entry is `no`, assign `Others`.

## Important limitation
This is a newly reconstructed, reproducible cohort from the uploaded annotation workbook. It is NOT proof of the exact historical 92 bugs used in the previously reported experiment. The workbook does not preserve an original 92-ID sample list or its random seed.

The first-listed operator rule is an explicit operational rule for this reconstructed sample. If the original study used a different rule for composite/multi-operator annotations, the sample strata should be regenerated using that rule.

No mutation experiments or Phase-2 validation were run to create this sample. The existing 53/92 result and rho=0.78 must not be attributed to this new cohort unless its selected bugs are actually validated and the statistics recomputed.

## Files
- `sample_92.csv`: selected 92 bug IDs and operator strata.
- `population_809.csv`: reconstructed 809-bug population.
- `RQ4_92_sample_and_audit.xlsx`: combined workbook.
- `population_reconciliation.csv`: population count checks.
- `project_population_audit.csv`: population/sample counts by project.
- `operator_strata_audit.csv`: population/sample counts by primary operator.
- `project_operator_allocation.csv`: exact two-stage allocation.
