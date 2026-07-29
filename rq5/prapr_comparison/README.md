Mutant Operator Study Replication Package

This repository contains the replication package for:

An Empirical Study of Mutant Operators for Injecting and Fixing Real-World Defects

The repository is organized by research question and supplementary analysis.

Repository Structure

Mutant-Operator-Study-Replication/
├── 1-RQ1-RQ2-Manual-Mapping/
├── 2-RQ3-Complexity-Analysis/
├── 3-RQ4-Dynamic-Validation/
├── 4-RQ5-Operator-Selection/
├── 5-PraPR-Supplementary-Comparison/
├── LICENSE
└── README.md

Contents

1-RQ1-RQ2-Manual-Mapping

Contains the manually validated bug-to-operator mappings used to evaluate:

theoretical operator expressiveness;

repairability across Java, Python, and JavaScript;

transformation-level reversibility; and

single- and multi-operator fixes.

2-RQ3-Complexity-Analysis

Contains the operator complexity classification and supporting data used to assign each operator to one of four search-space complexity tiers:

Low

Moderate

High

Extremely High

These tiers are also used as structural proxy costs in the RQ5 cost-aware evaluation.

3-RQ4-Dynamic-Validation

Contains the Java dynamic-validation experiment for the sampled Defects4J bugs, including mutant generation, validation outputs, and semantic assessment results.

4-RQ5-Operator-Selection

Contains the source-level operator-selection experiments under:

fixed operator-count budgets; and

proxy-cost budgets.

The RQ5 package evaluates:

frequency-based selection;

composition-aware selection;

frequency-per-cost selection;

exact cost-aware selection;

cheap-first selection; and

random no-ranking baselines.

5-PraPR-Supplementary-Comparison

Contains the supplementary cross-abstraction comparison with PraPR. PraPR's published bytecode-level mutator priorities are mapped to the study's unified source-level operator taxonomy and evaluated using complete-fix coverage.

This analysis does not run PraPR or reproduce end-to-end APR execution.

RQ5 Operator-Selection Reproduction

The following instructions reproduce the experiments in:

4-RQ5-Operator-Selection/

Recommended Folder Structure

4-RQ5-Operator-Selection/
├── README.md
├── requirements.txt
├── data/
│   └── strict_bug_operator_mappings.csv
├── scripts/
│   ├── run_operator_count_selection.py
│   └── cost_aware_operator_selection.py
├── results/
│   └── operator_count/
└── cost_aware_results/

Requirements

Python 3.10 or later

pandas

NumPy

SciPy

scikit-learn

Matplotlib

Install the dependencies from the repository root:

python -m pip install -r 4-RQ5-Operator-Selection/requirements.txt

Input Data

The cost-aware experiment reads:

4-RQ5-Operator-Selection/data/strict_bug_operator_mappings.csv

Required columns:

language, project, operators

The operators column contains semicolon-separated canonical operator codes.

An optional bug_id column may also be included.

The evaluation uses 925 eligible mappings:

Java: 619

Python: 178

JavaScript: 128

Fixed Operator-Count Evaluation

The fixed-count experiment compares frequency-based, composition-aware, and random no-ranking selection under:

k = 1, 3, 5, 10

A fix is covered only when all operator families required by its developer patch are included in the selected top-(k) operator set.

Run from the repository root:

python 4-RQ5-Operator-Selection/scripts/run_operator_count_selection.py

The generated files should be written under:

4-RQ5-Operator-Selection/results/operator_count/

Cost-Aware Operator Selection

The cost-aware experiment evaluates whether the RQ3 complexity tiers can improve operator selection when repair relevance and structural proxy cost are considered jointly.

Proxy-Cost Schemes

The primary exponential mapping is:

Complexity tier

Cost

Low

1

Moderate

2

High

4

Extremely High

8

Sensitivity mappings:

Linear: (1, 2, 3, 4)

Steep: (1, 3, 6, 10)

Evaluated budget fractions:

10%, 20%, 30%, 40%, 50%

Evaluated Strategies

Frequency: operators are ranked by training-fix frequency.

Frequency-per-cost: operators are ranked by frequency divided by proxy cost.

Exact cost-aware: a mixed-integer linear program selects the cost-feasible portfolio that maximizes training complete-fix coverage.

Cheap-first: operators are ranked by increasing proxy cost, with frequency used for tie-breaking.

Random: 1,000 randomly generated cost-feasible portfolios form the no-ranking baseline.

Evaluation Settings

Project-level folds: 5
Random portfolios per condition: 1,000
Paired bootstrap iterations: 5,000
Random seed: 20260322
Primary cost scheme: exponential

Run

From the repository root:

python 4-RQ5-Operator-Selection/scripts/cost_aware_operator_selection.py

The script writes outputs to:

4-RQ5-Operator-Selection/cost_aware_results/

Expected files:

operator_cost_table.csv
heldout_results.csv
heldout_summary.csv
selected_portfolios.csv
out_of_fold_predictions.csv
paired_comparisons.csv
primary_scheme_summary.csv
README_RESULTS.txt
coverage_java.svg
coverage_python.svg
coverage_javascript.svg

Primary Results at a 30% Proxy-Cost Budget

Language

Frequency

Frequency-per-cost

Exact cost-aware

Cheap-first

Random

Java

48.79%

58.97%

59.45%

22.29%

17.09%

Python

61.24%

69.10%

68.54%

19.66%

19.32%

JavaScript

30.47%

47.66%

38.28%

33.59%

21.89%

Frequency-per-cost improves over frequency by:

Java: 10.18 percentage points

Python: 7.87 percentage points

JavaScript: 17.19 percentage points

Across all 45 combinations of language, budget, and proxy mapping:

frequency-per-cost is better than frequency in 12 comparisons;

frequency-per-cost is worse in 3 comparisons;

30 comparisons are inconclusive;

exact cost-aware is better in 9 comparisons and worse in 6; and

frequency outperforms cheap-first in 35 comparisons.

Important Limitation

The default cost values are structural proxies derived from the RQ3 complexity tiers. They are not measured execution times, candidate counts, mutant counts, or validation costs.

The results must therefore be interpreted as complete-fix coverage under proxy-cost budgets, not as evidence of wall-clock runtime reduction.

PraPR Supplementary Comparison

The following instructions reproduce the analysis in:

5-PraPR-Supplementary-Comparison/

Recommended Folder Structure

5-PraPR-Supplementary-Comparison/
├── README.md
├── requirements.txt
├── data/
│   ├── strict_java_bug_operator_mappings.csv
│   └── prapr_published_mutator_frequencies.csv
├── mapping/
│   └── prapr_mapping_audit.csv
├── scripts/
│   └── run_prapr_comparison.py
└── results/

Run

From the repository root:

python 5-PraPR-Supplementary-Comparison/scripts/run_prapr_comparison.py

Expected result files:

5-PraPR-Supplementary-Comparison/results/prapr_mapped_ranking.csv
5-PraPR-Supplementary-Comparison/results/prapr_supplementary_comparison.csv
5-PraPR-Supplementary-Comparison/results/coverage_membership_by_bug.csv
5-PraPR-Supplementary-Comparison/results/run_metadata.json

Expected PraPR-Mapped Results

(k)

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

Interpretation

The PraPR results represent complete-fix coverage after cross-abstraction taxonomy mapping.

They must not be described as:

the number of bugs repaired by PraPR;

a direct source-level baseline;

a reproduction of PraPR's full repair pipeline; or

end-to-end evidence that one APR system outperforms another.

Reproducibility Notes

All paths in this README are repository-relative. No machine-specific directory is required.

Run all commands from the repository root unless stated otherwise. Generated outputs are deterministic under the documented random seed, subject to compatible library versions and solver behavior.
