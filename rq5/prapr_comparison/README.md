RQ5 Replication Package

This package reproduces two supplementary evaluations reported in RQ5 of An Empirical Study of Mutant Operators for Injecting and Fixing Real-World Defects:

Supplementary cross-abstraction comparison with PraPR

Cost-aware mutant-operator selection under proxy-cost budgets

The two evaluations use complete-fix coverage: a bug is covered only when every operator family required by its developer patch is included in the selected operator set.

1. Supplementary Cross-Abstraction Comparison with PraPR

Scope

PraPR ranks concrete JVM bytecode-level mutators using frequencies mined from the HD-Repair corpus. The paper studies unified source-level semantic operator families. Therefore, this package does not treat PraPR as a direct source-level baseline.

The analysis maps PraPR's published mutator priorities to the unified source-level taxonomy and evaluates the mapped ranking on the same 619 strict Java bug-to-operator mappings used in RQ5.

This package does not run PraPR, generate bytecode mutants, or measure end-to-end APR success. It computes complete-fix representability under a mapped operator-family budget.

Metric

For a selected top-(k) family set (S_k), a Java fix is covered only when all operator families required by its developer patch are contained in (S_k).

[\mathrm{Coverage@}k =\frac{\text{covered fixes}}{619}]

Mapping and ranking procedure

Read the published PraPR mutator frequencies from:

data/prapr_published_mutator_frequencies.csv

Apply the documented mutator-to-family mapping in:

mapping/prapr_mapping_audit.csv

Consolidate mutators mapped to the same unified family by summing their published frequencies.

Rank the resulting families by aggregated frequency in descending order.

Break frequency ties by:

earliest published PraPR rank; then

family label.

Evaluate the mapped top-(k) order for:

k = 1, 3, 5, 10

The resulting top-ten family order is:

MCR, VR, ROR, CR, CI, MPM, AOR, MRV, DTR, VA

Requirements

Python 3.10 or later

pandas 2.x

Install the dependencies with:

python -m pip install -r requirements.txt

or create the Conda environment:

conda env create -f environment.yml
conda activate prapr-supplementary-replication

Run

From the package root:

bash run.sh

or:

python scripts/run_prapr_comparison.py

Expected results

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

Output files

results/prapr_mapped_ranking.csv

results/prapr_supplementary_comparison.csv

results/coverage_membership_by_bug.csv

results/run_metadata.json

Input and code files

data/strict_java_bug_operator_mappings.csvThe 619 eligible Java developer fixes and their complete required operator-family sets.

data/prapr_published_mutator_frequencies.csvPraPR mutator frequencies used to derive the published priority order.

mapping/prapr_mapping_audit.csvDirect and approximate mapping decisions with their rationales.

scripts/run_prapr_comparison.pySelf-contained reproduction script.

run.shConvenience launcher.

requirements.txt and environment.ymlSoftware dependencies.

Interpretation

The results represent complete-fix coverage after cross-abstraction taxonomy mapping. They must not be interpreted as:

the number of bugs repaired by PraPR;

a reproduction of PraPR's complete APR pipeline; or

end-to-end evidence that one ranking method outperforms another.

PraPR reference

A. Ghanbari, S. Benton, and L. Zhang, “Practical Program Repair via Bytecode Mutation,” Proceedings of the 28th ACM SIGSOFT International Symposium on Software Testing and Analysis (ISSTA), 2019, pp. 19–30.

2. Cost-Aware Mutant-Operator Selection

Scope

This experiment evaluates whether the RQ3 search-space complexity tiers can improve operator selection when empirical repair relevance and proxy cost are considered jointly.

The evaluation uses the same 925 eligible bug-to-operator mappings:

Java: 619

Python: 178

JavaScript: 128

Projects are evaluated using project-level held-out folds. In each fold, operator portfolios are constructed from the training projects and evaluated only on the held-out projects.

Input file

The script expects:

strict_bug_operator_mappings.csv

with the following required columns:

language, project, operators

The operators column must contain semicolon-separated canonical operator codes.

An optional bug_id column may also be supplied. When it is absent, the script creates row-based identifiers.

The script checks these locations:

/home1/furqan/my_mutation_experiments/scripts/rq5_results/strict_bug_operator_mappings.csv
/home1/furqan/my_mutation_experiments/scripts/strict_bug_operator_mappings.csv

The base directory is configured in the script as:

BASE_DIR = Path("/home1/furqan/my_mutation_experiments/scripts").resolve()

Place the input file in one of the expected locations or update BASE_DIR before running the script.

Proxy-cost schemes

Each canonical operator is assigned a cost according to its RQ3 complexity tier.

Primary exponential mapping

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

Sensitivity mappings

Linear: (1, 2, 3, 4)

Steep: (1, 3, 6, 10)

The evaluated budget fractions are:

10%, 20%, 30%, 40%, 50%

Each budget is calculated as a fraction of the total cost of all canonical operator families under the selected cost scheme.

Selection strategies

The script evaluates five strategies under the same proxy-cost budget:

FrequencyOperators are ranked by their occurrence frequency in the training fixes.

Frequency-per-costOperators are ranked by training frequency divided by proxy cost.

Cheap-firstOperators are ranked by increasing proxy cost, with frequency used for tie-breaking.

Exact cost-awareA mixed-integer linear program selects the cost-feasible portfolio that maximizes complete-fix coverage on the training projects.

RandomThe no-ranking baseline uses 1,000 randomly generated cost-feasible portfolios.

For the ranking-based strategies, operators are traversed in ranked order and selected whenever their cost fits within the remaining budget.

Exact cost-aware objective

For a selected operator portfolio (S):

[\mathrm{Cost}(S)=\sum_{o\in S}c(o)]

The exact cost-aware strategy solves:

[S_C^* =\arg\max_{S\subseteq\mathcal{O}}\sum_{b\in B_{\mathrm{train}}}\mathbb{I}[R_b\subseteq S]]

subject to:

[\sum_{o\in S}c(o)\leq C]

where:

(R_b) is the complete operator set required by fix (b);

(c(o)) is the assigned proxy cost of operator (o); and

(C) is the available proxy-cost budget.

Held-out evaluation settings

The supplied script uses:

Five project-level folds
1,000 random portfolios per condition
5,000 paired bootstrap iterations
Random seed: 20260322

The primary cost scheme is:

exponential

Requirements

Install the libraries imported by the supplied script:

python -m pip install pandas numpy scipy scikit-learn matplotlib

The exact cost-aware strategy uses:

scipy.optimize.milp

Run

Save the supplied cost-aware script as:

cost_aware_operator_selection.py

Place it under:

/home1/furqan/my_mutation_experiments/scripts/

Then run:

cd /home1/furqan/my_mutation_experiments/scripts
python cost_aware_operator_selection.py

Output directory

The script writes all outputs to:

/home1/furqan/my_mutation_experiments/scripts/cost_aware_results/

Output files

operator_cost_table.csvCost assigned to each operator under every evaluated cost scheme.

heldout_results.csvFold-level coverage, selected-operator counts, and selected costs.

heldout_summary.csvWeighted held-out summary for each language, cost scheme, budget, and strategy.

selected_portfolios.csvOperators selected in each held-out fold.

out_of_fold_predictions.csvBug-level coverage outcomes for each deterministic strategy and coverage probabilities for the random baseline.

paired_comparisons.csvPaired bootstrap differences and 95% confidence intervals.

primary_scheme_summary.csvSummary for the primary exponential cost mapping.

README_RESULTS.txtHuman-readable summary of the primary results and paired comparisons.

coverage_java.svg

coverage_python.svg

coverage_javascript.svg

The script also attempts to export PNG versions of the three figures.

Headline primary-scheme results

Under the exponential mapping and a 30% proxy-cost budget:

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

Across all 45 combinations of language, budget, and proxy-cost mapping:

frequency-per-cost is better than frequency in 12 comparisons;

frequency-per-cost is worse in 3 comparisons;

the remaining 30 comparisons are inconclusive;

exact cost-aware is better in 9 comparisons and worse in 6; and

frequency outperforms cheap-first in 35 comparisons.

Optional measured-cost evaluation

When this file exists:

/home1/furqan/my_mutation_experiments/scripts/operator_runtime_costs.csv

the script also evaluates a measured-cost scheme.

The file must contain:

operator,cost

It must include every canonical operator, and every cost must be finite and greater than zero. The script normalizes measured costs by the minimum supplied cost.

Important limitation

The default linear, exponential, and steep costs are structural proxies derived from the RQ3 complexity tiers. They are not measured execution times, mutant counts, candidate counts, or validation costs.

The results must therefore be interpreted as complete-fix coverage under structural proxy-cost budgets, not as evidence of wall-clock runtime reduction.

3. Recommended Reproduction Order

Run the two analyses independently:

Step 1: PraPR supplementary comparison

python scripts/run_prapr_comparison.py

Verify:

results/prapr_supplementary_comparison.csv

Step 2: Cost-aware operator selection

python cost_aware_operator_selection.py

Verify:

cost_aware_results/primary_scheme_summary.csv
cost_aware_results/paired_comparisons.csv
cost_aware_results/README_RESULTS.txt

The generated tables and figures reproduce the RQ5 supplementary PraPR comparison and cost-aware operator-selection results.
