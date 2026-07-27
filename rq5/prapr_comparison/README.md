Supplementary Cross-Abstraction Comparison with PraPR

This folder reproduces the supplementary PraPR comparison reported in RQ5 of An Empirical Study of Mutant Operators for Injecting and Fixing Real-World Defects.

Scope

PraPR ranks concrete JVM bytecode-level mutators using frequencies mined from the HD-Repair corpus. The paper studies unified source-level semantic operator families. Therefore, this package does not treat PraPR as a direct source-level baseline. It reproduces a transferred-utility analysis in which PraPR's published mutator priorities are mapped to the paper's unified taxonomy and evaluated on the same 619 strict Java bug-to-operator mappings.

This package does not run PraPR, generate bytecode mutants, or measure end-to-end APR success. It only computes complete-fix representability under a mapped operator-family budget.

Metric

For a selected top-k family set S_k, a Java fix is covered only when all operator families required by its developer patch are contained in S_k.

Coverage@k = covered fixes / 619

Mapping and ranking rule

Read the published PraPR mutator frequencies from data/prapr_published_mutator_frequencies.csv.

Apply the documented mutator-to-family mapping in mapping/prapr_mapping_audit.csv.

Consolidate mutators mapped to the same unified family by summing their published frequencies.

Rank families by aggregated frequency in descending order.

Break frequency ties by the earliest published PraPR rank, then by family label.

Evaluate the mapped top-k order for k = 1, 3, 5, 10 on the 619 Java mappings.

The resulting top ten families are:

MCR, VR, ROR, CR, CI, MPM, AOR, MRV, DTR, VA

Requirements

Python 3.10 or later

pandas 2.x

Install with pip:

python -m pip install -r requirements.txt

or create the Conda environment:

conda env create -f environment.yml
conda activate prapr-supplementary-replication

Run

From the package root:

bash run.sh

or:

python scripts/run_prapr_comparison.py

Expected output

k

Selected families

Covered fixes

Coverage

1

MCR

54 / 619

8.72%

3

MCR, VR, ROR

76 / 619

12.28%

5

MCR, VR, ROR, CR, CI

180 / 619

29.08%

10

MCR, VR, ROR, CR, CI, MPM, AOR, MRV, DTR, VA

333 / 619

53.80%

The script writes:

results/prapr_mapped_ranking.csv

results/prapr_supplementary_comparison.csv

results/coverage_membership_by_bug.csv

results/run_metadata.json

File descriptions

Inputs

data/strict_java_bug_operator_mappings.csv — the 619 eligible Java developer fixes and their complete required operator-family sets.

data/prapr_published_mutator_frequencies.csv — PraPR mutator frequencies used to derive the published priority order.

mapping/prapr_mapping_audit.csv — direct/approximate mapping decisions and rationales.

Code

scripts/run_prapr_comparison.py — self-contained reproduction script.

run.sh — convenience launcher.

requirements.txt and environment.yml — software dependencies.

Outputs

results/prapr_mapped_ranking.csv — consolidated family ranking.

results/prapr_supplementary_comparison.csv — values reported in the manuscript table.

results/coverage_membership_by_bug.csv — bug-level audit showing coverage at each budget.

results/run_metadata.json — settings and interpretation note.

Interpretation

The results should be described as complete-fix representability after cross-abstraction taxonomy mapping. They must not be described as the number of bugs repaired by PraPR or as proof that one ranking method outperforms the other end to end.

PraPR reference

A. Ghanbari, S. Benton, and L. Zhang, “Practical Program Repair via Bytecode Mutation,” Proceedings of the 28th ACM SIGSOFT International Symposium on Software Testing and Analysis (ISSTA), 2019, pp. 19–30.
