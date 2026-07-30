```text
RQ5: Operator Selection and Supplementary Comparisons

This folder contains the replication materials for RQ5 of:

An Empirical Study of Mutant Operators for Injecting and Fixing Real-World Defects

RQ5 evaluates source-level mutant-operator selection under fixed operator-count and proxy-cost budgets. It also contains the supplementary cross-abstraction comparison with PraPR. The complexity–popularity analysis used to support the search-space interpretation is included for transparency.

Folder Structure

RQ5/
├── README.md
├── strict_bug_operator_mappings.csv
├── cost_aware_operator_selection.py
├── complexity_popularity.py
├── complexity_popularity_correlation.csv
├── cost_aware_results/
│   ├── operator_cost_table.csv
│   ├── heldout_results.csv
│   ├── heldout_summary.csv
│   ├── selected_portfolios.csv
│   ├── out_of_fold_predictions.csv
│   ├── paired_comparisons.csv
│   ├── primary_scheme_summary.csv
│   ├── README_RESULTS.txt
│   ├── coverage_java.svg
│   ├── coverage_python.svg
│   └── coverage_javascript.svg
└── prapr_comparison/
    ├── README.md
    ├── prapr_published_mutator_frequencies.csv
    ├── prapr_mapping_audit.csv
    ├── prapr_mapped_ranking.csv
    ├── strict_java_bug_operator_mappings.csv
    ├── run_prapr_comparison.py
    └── prapr_supplementary_comparison.csv

1. Input Data

The operator-selection experiment uses:

RQ5/strict_bug_operator_mappings.csv

Required columns:

language, project, operators

The operators column contains semicolon-separated canonical operator codes. An optional bug_id column may also be included.

The cleaned dataset contains 925 eligible bug-to-operator mappings:

Language

Eligible mappings

Java

619

Python

178

JavaScript

128

Total

925

A fix is counted as covered only when all operator families required by its developer patch are included in the selected operator set.

2. Environment and Dependencies

Requirements

Python 3.10 or later

pandas

NumPy

SciPy with scipy.optimize.milp

scikit-learn

Matplotlib

Install the dependencies from the repository root:

python -m pip install pandas numpy scipy scikit-learn matplotlib

3. GitHub-Relative Path Configuration

The replication script should not contain machine-specific paths.

In cost_aware_operator_selection.py, configure the script directory as:

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "cost_aware_results"
MEASURED_COST_FILE = BASE_DIR / "operator_runtime_costs.csv"

INPUT_CANDIDATES = (
    BASE_DIR / "strict_bug_operator_mappings.csv",
)

With this configuration, the experiment can be run directly after cloning the repository.

4. Cost-Aware Operator Selection

The cost-aware experiment evaluates whether the search-space complexity tiers identified in RQ3 can improve operator selection when repair relevance and structural proxy cost are considered jointly.

Proxy-Cost Schemes

The primary exponential mapping is:

Complexity tier

Proxy cost

Low

1

Moderate

2

High

4

Extremely High

8

Two additional mappings are evaluated as sensitivity checks:

Scheme

Low

Moderate

High

Extremely High

Linear

1

2

3

4

Exponential

1

2

4

8

Steep

1

3

6

10

The evaluated budget fractions are:

10%, 20%, 30%, 40%, and 50%

Each budget is calculated as a fraction of the total proxy cost of the canonical operator set.

Evaluated Strategies

The experiment compares five strategies under the same proxy-cost budget:

FrequencyOperators are ranked by their occurrence frequency in the training fixes.

Frequency-per-costOperators are ranked by training frequency divided by proxy cost.

Exact cost-awareA mixed-integer linear program selects the cost-feasible operator portfolio that maximizes complete-fix coverage on the training projects.

Cheap-firstOperators are ranked by increasing proxy cost, with frequency used for tie-breaking.

RandomA no-ranking baseline based on 1,000 randomly generated cost-feasible operator portfolios.

For the ranking-based strategies, operators are considered in ranked order and selected whenever their cost fits within the remaining budget.

Exact Cost-Aware Objective

For an operator set (S), the total proxy cost is:

[\mathrm{Cost}(S)=\sum_{o\in S}c(o)]

The exact cost-aware strategy selects:

[S_C^* =\arg\max_{S\subseteq\mathcal{O}}\sum_{b\in B_{\mathrm{train}}}\mathbb{I}[R_b\subseteq S]]

subject to:

[\sum_{o\in S}c(o)\leq C]

where (R_b) is the complete operator set required by fix (b), (c(o)) is the proxy cost of operator (o), and (C) is the available budget.

Evaluation Settings

Project-level held-out folds: 5
Random portfolios per condition: 1,000
Paired bootstrap iterations: 5,000
Random seed: 20260322
Primary proxy-cost scheme: exponential

Run

From the repository root:

python RQ5/cost_aware_operator_selection.py

Generated Outputs

The script writes the following files to:

RQ5/cost_aware_results/

File

Description

operator_cost_table.csv

Complexity tier and assigned cost for every operator and cost scheme

heldout_results.csv

Fold-level coverage and selected-portfolio statistics

heldout_summary.csv

Aggregated held-out results by language, cost scheme, budget, and strategy

selected_portfolios.csv

Operators selected in every fold and condition

out_of_fold_predictions.csv

Bug-level held-out coverage outcomes

paired_comparisons.csv

Paired bootstrap differences and 95% confidence intervals

primary_scheme_summary.csv

Summary for the primary exponential mapping

README_RESULTS.txt

Human-readable result summary

coverage_java.svg

Java coverage figure

coverage_python.svg

Python coverage figure

coverage_javascript.svg

JavaScript coverage figure

Primary Results at the 30% Proxy-Cost Budget

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

At this budget, frequency-per-cost improves over frequency by:

Java: 10.18 percentage points

Python: 7.87 percentage points

JavaScript: 17.19 percentage points

Across all 45 combinations of language, budget, and proxy-cost mapping:

frequency-per-cost performs better than frequency in 12 comparisons;

frequency-per-cost performs worse in 3 comparisons;

30 comparisons are inconclusive;

exact cost-aware performs better in 9 comparisons and worse in 6; and

frequency outperforms cheap-first in 35 comparisons.

Interpretation Limitation

The linear, exponential, and steep costs are structural proxies derived from the RQ3 complexity tiers. They are not measured execution times, mutant counts, generated-candidate counts, or validation costs.

The results therefore represent complete-fix coverage under structural proxy-cost budgets. They must not be interpreted as evidence of wall-clock runtime reduction.

5. Complexity–Popularity Correlation

This analysis examines the relationship between operator popularity and search-space complexity across the 33 canonical operators.

Complexity Encoding

The ordinal complexity tiers are encoded as:

Complexity tier

Score

Low

1

Moderate

2

High

3

Extremely High

4

Operator popularity is the percentage of the 955 representable fixes whose developer patches contain the operator.

Run

From the repository root:

python RQ5/complexity_popularity.py

Expected Output

Number of operators: 33
Spearman rho: 0.5723
Spearman p-value: 0.000501
Kendall tau-b: 0.4863
Kendall p-value: 0.000437

The script also writes:

RQ5/complexity_popularity_correlation.csv

Interpretation

Spearman's rank correlation shows a statistically significant positive association between operator popularity and search-space complexity:

rho = 0.5723
p = 0.000501
n = 33

This result indicates that more frequently required operators generally tend to have larger search spaces, although the relationship is not uniform. For example, VA and MOCS belong to the Extremely High complexity tier but each appears in only 7.1% of representable fixes.

The Kendall tau-b result is included as a robustness check.

6. Supplementary Cross-Abstraction Comparison with PraPR

The PraPR comparison is located in:

RQ5/prapr_comparison/

PraPR ranks JVM bytecode-level mutators using published frequencies. This study evaluates unified source-level semantic operator families. Therefore, PraPR is treated as a supplementary cross-abstraction reference rather than a direct source-level baseline.

The analysis maps PraPR's published mutator priorities to the unified taxonomy and evaluates the resulting family ranking on the same 619 strict Java mappings.

This analysis does not:

run PraPR;

generate bytecode mutants;

reproduce PraPR's full APR pipeline; or

measure end-to-end repair success.

PraPR Mapping Procedure

Read the published mutator frequencies from:

RQ5/prapr_comparison/prapr_published_mutator_frequencies.csv

Apply the documented mutator-to-family mapping in:

RQ5/prapr_comparison/prapr_mapping_audit.csv

Consolidate mutators mapped to the same unified family by summing their published frequencies.

Rank the resulting families by aggregated frequency in descending order.

Break ties by the earliest published PraPR rank and then by family label.

Evaluate complete-fix Coverage@(k) for:

k = 1, 3, 5, and 10

The mapped top-ten family order is:

MCR, VR, ROR, CR, CI, MPM, AOR, MRV, DTR, VA

Run

From the repository root:

python RQ5/prapr_comparison/run_prapr_comparison.py

Expected Results

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

PraPR Output Files

File

Description

prapr_mapped_ranking.csv

Consolidated source-level family ranking

prapr_supplementary_comparison.csv

Coverage values reported in the manuscript

strict_java_bug_operator_mappings.csv

The 619 eligible Java mappings

prapr_mapping_audit.csv

Mapping decisions and rationales

Interpretation

The PraPR results represent complete-fix coverage after cross-abstraction taxonomy mapping.

They must not be described as:

the number of bugs repaired by PraPR;

a reproduction of PraPR;

a direct source-level baseline; or

end-to-end evidence that one APR system outperforms another.

7. Recommended Reproduction Order

Run the analyses independently from the repository root.

Step 1: Complexity–Popularity Correlation

python RQ5/complexity_popularity.py

Verify:

RQ5/complexity_popularity_correlation.csv

Step 2: Cost-Aware Operator Selection

python RQ5/cost_aware_operator_selection.py

Verify:

RQ5/cost_aware_results/primary_scheme_summary.csv
RQ5/cost_aware_results/paired_comparisons.csv
RQ5/cost_aware_results/README_RESULTS.txt

Step 3: PraPR Supplementary Comparison

python RQ5/prapr_comparison/run_prapr_comparison.py

Verify:

RQ5/prapr_comparison/prapr_mapped_ranking.csv
RQ5/prapr_comparison/prapr_supplementary_comparison.csv

8. Reproducibility Notes

All paths in this README are repository-relative. No user-specific or machine-specific directory is required.

The documented random seed makes the random baseline and paired bootstrap procedure reproducible, subject to compatible Python, library, and solver versions.
