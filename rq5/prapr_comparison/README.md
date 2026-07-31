Mutation-Based Bug Fixing Experiments

This repository contains the replication materials for the paper:

An Empirical Study of Mutant Operators for Injecting and Fixing Real-World Defects

It provides a self-contained toolkit for running mutation-based experiments on Defects4J projects, analysing generated mutants and plausible patches, reproducing the operator-level analyses, and evaluating the RQ5 operator-selection experiments.

The main workflow is:

Export developer patches as buggy-versus-fixed diffs.

Run MAJOR and PIT mutation analysis on Defects4J bugs.

Summarise mutation results by project and bug.

Analyse plausible mutants by operator.

Reproduce RQ5 cost-aware operator selection, complexity–popularity correlation, and the supplementary PraPR comparison.

The core mutation workflow is implemented in scripts/. The RQ5 replication materials are located in RQ5/.

1. Repository Structure

Mutation/
├── README.md
├── transparency/
│   ├── atomic_decomposition.md
│   ├── defects4j.csv
│   └── BugsInPy.xlsx
│
├── scripts/
│   ├── run_one_project_both_final.py
│   ├── export_dev_patches.py
│   ├── summarize_mutation_by_project.py
│   ├── compute_patches.py
│   ├── evaluate_patches.py
│   └── README.md
│
├── RQ5/
│   ├── README.md
│   ├── strict_bug_operator_mappings.csv
│   ├── cost_aware_operator_selection.py
│   ├── complexity_popularity.py
│   ├── complexity_popularity_correlation.csv
│   ├── cost_aware_results/
│   │   ├── operator_cost_table.csv
│   │   ├── heldout_results.csv
│   │   ├── heldout_summary.csv
│   │   ├── selected_portfolios.csv
│   │   ├── out_of_fold_predictions.csv
│   │   ├── paired_comparisons.csv
│   │   ├── primary_scheme_summary.csv
│   │   ├── README_RESULTS.txt
│   │   ├── coverage_java.svg
│   │   ├── coverage_python.svg
│   │   └── coverage_javascript.svg
│   └── prapr_comparison/
│       ├── README.md
│       ├── prapr_published_mutator_frequencies.csv
│       ├── prapr_mapping_audit.csv
│       ├── prapr_mapped_ranking.csv
│       ├── strict_java_bug_operator_mappings.csv
│       ├── run_prapr_comparison.py
│       └── prapr_supplementary_comparison.csv
│
├── logs/
│   ├── Lang-1/
│   │   ├── mutants.log
│   │   ├── kill.csv
│   │   ├── major_summary.csv
│   │   └── pit_summary.csv
│   └── <Project>-<Bug>/
│
├── results/
│   ├── mutation_summary_by_project.csv
│   ├── mutation_summary_by_bug.csv
│   ├── <Project>/
│   │   ├── per_bug_summary.csv
│   │   ├── per_project_summary.csv
│   │   └── operator_usage.csv
│   └── dev_patches/
│       ├── Lang/
│       │   ├── Lang-1.diff
│       │   ├── Lang-2.diff
│       │   └── ...
│       └── ...
│
├── d4j_work/
│   ├── Lang-1-fixed/
│   ├── Lang-1-buggy/
│   └── ...
│
└── d4j_work_diff/
    └── ...

The logs/, results/, d4j_work/, and d4j_work_diff/ directories are created or populated during execution.

2. Environment and Dependencies

2.1 Core Defects4J Mutation Experiments

Requirements:

Linux, tested on Ubuntu-like systems

Python 3.8 or later

Java 8 for MAJOR compilation

Java 11 for the Defects4J CLI and PIT runtime

Defects4J installed and working

Set the following environment variables before running the scripts. Adapt the paths to your machine:

export D4J_HOME=/home1/yourname/tools_and_libs/defects4j
export EXPERIMENT_ROOT=/home1/yourname/my_mutation_experiments

export JAVA11_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export JAVA8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export MAJOR_JAVA_HOME="$JAVA8_HOME"

Verify the Defects4J installation:

$D4J_HOME/framework/bin/defects4j info -p Lang -b 1

2.2 RQ5 Analyses

The RQ5 experiments require:

Python 3.10 or later

pandas

NumPy

SciPy with scipy.optimize.milp

scikit-learn

Matplotlib

Install the required Python packages from the repository root:

python -m pip install pandas numpy scipy scikit-learn matplotlib

3. Core Scripts

All core mutation-analysis scripts are located in scripts/.

run_one_project_both_final.py

Runs MAJOR and PIT for a Defects4J project and a selected set of bugs on the fixed revision. It supports process-level parallelism, PIT worker threads, PIT forks, and Java heap configuration.

Main outputs include:

mutants.log

kill.csv

major_summary.csv

pit_summary.csv

export_dev_patches.py

Exports developer patches as unified diff -ruN files by comparing the buggy and fixed revisions of each Defects4J bug.

summarize_mutation_by_project.py

Scans mutation logs and creates:

per-project mutation summaries

per-bug mutation summaries

compute_patches.py

Reads kill.csv and mutants.log and computes:

total mutants

plausible mutants with LIVE status

aggregate project-level counts

plausible-mutant counts by operator

evaluate_patches.py

Provides additional patch-analysis functionality, such as comparing generated patches against developer patches, filtering patches, and exporting further tables. Its available options depend on the current script version.

python3 scripts/evaluate_patches.py -h

4. Core Mutation-Analysis Workflow

4.1 Export Developer Patches

The export script checks out buggy and fixed Defects4J revisions and creates unified diff files.

List the Defects4J projects detected under $D4J_HOME/framework/projects:

cd scripts
python3 export_dev_patches.py --list

Export developer patches for one or more projects:

python3 export_dev_patches.py Lang
python3 export_dev_patches.py Lang Mockito --force

The --force option overwrites existing diff files.

Example outputs:

$EXPERIMENT_ROOT/results/dev_patches/Lang/Lang-1.diff
$EXPERIMENT_ROOT/results/dev_patches/Lang/Lang-2.diff
...

4.2 Run MAJOR and PIT

The mutation runner checks out the fixed revision of each bug, compiles it, and executes both mutation engines.

Run all active bugs in a project:

cd scripts
python3 run_one_project_both_final.py Lang \
  --jobs 4 \
  --threads 8 \
  --forks 2 \
  --jvm-xmx 8g

Run a single bug:

python3 run_one_project_both_final.py Lang 2 --threads 6 --forks 2

Run a selected subset of bugs:

python3 run_one_project_both_final.py Lang --bugs 1,5,9,12

Key options:

Option

Description

project

Positional Defects4J project name, such as Lang or Math

bug_id

Optional positional ID for a single bug

--list-bugs

Prints all active Defects4J bug IDs for the project

--bugs

Comma-separated list of selected bug IDs

--jobs

Number of bugs executed in parallel

--threads

Number of PIT worker threads

--forks

PIT fork count

--jvm-xmx

Java heap size, for example 8g

Per-bug outputs are stored under:

$EXPERIMENT_ROOT/logs/<Project>-<Bug>/
├── mutants.log
├── kill.csv
├── major_summary.csv
└── pit_summary.csv

4.3 Summarise Mutation Results

After the mutation runs complete, create project-level and bug-level summaries:

cd scripts
python3 summarize_mutation_by_project.py \
  "$EXPERIMENT_ROOT/logs" \
  --outdir "$EXPERIMENT_ROOT/results"

The generated files include:

mutation_summary_by_project.csv

mutation_summary_by_bug.csv

The summaries report, for each mutation engine:

project and bug

total mutants

killed mutants

survived mutants

kill rate

4.4 Compute Plausible Mutants by Operator

The script treats mutants marked LIVE in kill.csv as plausible and obtains operator information from mutants.log.

Process one logs root:

cd scripts
python3 compute_patches.py --logs-root "$EXPERIMENT_ROOT/logs"

Alternatively, process all logs_* directories under the current directory:

python3 compute_patches.py --all-projects

Per-project outputs are written under results/<Project>/:

File

Description

per_bug_summary.csv

Total and plausible mutant counts for each bug

per_project_summary.csv

Aggregated project-level counts

operator_usage.csv

Plausible-mutant count for each operator

These outputs support the operator-level analysis reported in the paper.

4.5 Evaluate Patches

Use evaluate_patches.py for optional or custom analyses, including:

comparison with developer patches

plausibility or correctness filtering

export of additional paper tables

View the available options:

cd scripts
python3 evaluate_patches.py -h

5. Reproducing the Main Mutation-Analysis Outputs

From the repository root, the high-level reproduction sequence is:

# 1. Export developer diffs
python3 scripts/export_dev_patches.py <Project>

# 2. Run MAJOR and PIT
python3 scripts/run_one_project_both_final.py <Project> --jobs <N>

# 3. Summarise mutation results
python3 scripts/summarize_mutation_by_project.py \
  "$EXPERIMENT_ROOT/logs" \
  --outdir "$EXPERIMENT_ROOT/results"

# 4. Compute plausible mutants and operator usage
python3 scripts/compute_patches.py \
  --logs-root "$EXPERIMENT_ROOT/logs"

# 5. Optionally reproduce additional patch evaluations
python3 scripts/evaluate_patches.py -h

6. Data Transparency

The study uses Defects4J v2.0.1, which contains 835 bugs.

803 bugs were analysed for mutant-operator expressiveness.

32 bugs were excluded because of benchmark depletion, including dependency or test failures.

The detailed manual decomposition of developer patches into atomic mutant operators is documented in transparency/atomic_decomposition.md.

The Defects4J manual analysis is provided in transparency/defects4j.csv.

The BugsInPy manual analysis is provided in transparency/BugsInPy.xlsx.

7. RQ5: Operator Selection and Supplementary Comparisons

RQ5 evaluates source-level mutant-operator selection under fixed operator-count and structural proxy-cost budgets. It also includes:

the complexity–popularity analysis used to support the search-space interpretation; and

a supplementary cross-abstraction comparison with PraPR.

The RQ5 replication materials are located in:

RQ5/

7.1 Input Data

The operator-selection experiment uses:

RQ5/strict_bug_operator_mappings.csv

Required columns:

language

project

operators

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

A fix is counted as covered only when every operator family required by its developer patch is included in the selected operator set.

8. GitHub-Relative Path Configuration

The RQ5 scripts should use repository-relative paths rather than machine-specific paths.

In RQ5/cost_aware_operator_selection.py, configure the script directory as follows:

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "cost_aware_results"
MEASURED_COST_FILE = BASE_DIR / "operator_runtime_costs.csv"

INPUT_CANDIDATES = (
    BASE_DIR / "strict_bug_operator_mappings.csv",
)

With this configuration, the experiment can be executed directly after cloning the repository.

9. Cost-Aware Operator Selection

The cost-aware experiment evaluates whether the search-space complexity tiers identified in RQ3 can improve operator selection when repair relevance and structural proxy cost are considered jointly.

9.1 Proxy-Cost Schemes

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

9.2 Evaluated Strategies

Five strategies are compared under the same proxy-cost budget:

Strategy

Description

Frequency

Ranks operators by their occurrence frequency in the training fixes

Frequency-per-cost

Ranks operators by training frequency divided by proxy cost

Exact cost-aware

Uses mixed-integer linear programming to select the cost-feasible portfolio that maximises complete-fix coverage on the training projects

Cheap-first

Ranks operators by increasing proxy cost, with frequency used for tie-breaking

Random

Uses 1,000 randomly generated cost-feasible operator portfolios as a no-ranking baseline

For ranking-based strategies, operators are considered in ranked order and selected whenever their cost fits within the remaining budget.

9.3 Exact Cost-Aware Objective

For an operator set (S), the total proxy cost is:

[\mathrm{Cost}(S)=\sum_{o\in S}c(o)]

The exact cost-aware strategy selects:

[S_C^*=\arg\max_{S\subseteq\mathcal{O}}\sum_{b\in B_{\mathrm{train}}}\mathbb{I}[R_b\subseteq S]]

subject to:

[\sum_{o\in S}c(o)\leq C]

where:

(R_b) is the complete operator set required by fix (b);

(c(o)) is the proxy cost of operator (o); and

(C) is the available budget.

9.4 Evaluation Settings

Setting

Value

Project-level held-out folds

5

Random portfolios per condition

1,000

Paired bootstrap iterations

5,000

Random seed

20260322

Primary proxy-cost scheme

Exponential

9.5 Run the Experiment

From the repository root:

python RQ5/cost_aware_operator_selection.py

9.6 Generated Outputs

The script writes the following files to RQ5/cost_aware_results/:

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

9.7 Primary Results at the 30% Proxy-Cost Budget

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

At the 30% budget, frequency-per-cost improves over frequency by:

Java: 10.18 percentage points

Python: 7.87 percentage points

JavaScript: 17.19 percentage points

Across all 45 combinations of language, budget, and proxy-cost mapping:

frequency-per-cost performs better than frequency in 12 comparisons;

frequency-per-cost performs worse in 3 comparisons;

30 comparisons are inconclusive;

exact cost-aware performs better in 9 comparisons and worse in 6; and

frequency outperforms cheap-first in 35 comparisons.

9.8 Interpretation Limitation

The linear, exponential, and steep costs are structural proxies derived from the RQ3 complexity tiers. They are not measured execution times, mutant counts, generated-candidate counts, or validation costs.

The results therefore represent complete-fix coverage under structural proxy-cost budgets. They must not be interpreted as evidence of wall-clock runtime reduction.

10. Complexity–Popularity Correlation

This analysis examines the relationship between operator popularity and search-space complexity across the 33 canonical operators.

10.1 Complexity Encoding

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

10.2 Run the Analysis

From the repository root:

python RQ5/complexity_popularity.py

10.3 Expected Output

Number of operators: 33
Spearman rho: 0.5723
Spearman p-value: 0.000501
Kendall tau-b: 0.4863
Kendall p-value: 0.000437

The script also writes:

RQ5/complexity_popularity_correlation.csv

10.4 Interpretation

Spearman's rank correlation shows a statistically significant positive association between operator popularity and search-space complexity:

rho = 0.5723
p = 0.000501
n = 33

More frequently required operators generally tend to have larger search spaces, although the relationship is not uniform. For example, VA and MOCS belong to the Extremely High complexity tier but each appears in only 7.1% of representable fixes.

The Kendall tau-b result is included as a robustness check.

11. Supplementary Cross-Abstraction Comparison with PraPR

The PraPR comparison is located in:

RQ5/prapr_comparison/

PraPR ranks JVM bytecode-level mutators using published frequencies, whereas this study evaluates unified source-level semantic operator families. PraPR is therefore treated as a supplementary cross-abstraction reference rather than a direct source-level baseline.

The analysis maps PraPR's published mutator priorities to the unified taxonomy and evaluates the resulting family ranking on the same 619 strict Java mappings.

This analysis does not:

run PraPR;

generate bytecode mutants;

reproduce PraPR's full APR pipeline; or

measure end-to-end repair success.

11.1 PraPR Mapping Procedure

Read the published mutator frequencies from:

RQ5/prapr_comparison/prapr_published_mutator_frequencies.csv

Apply the documented mutator-to-family mapping in:

RQ5/prapr_comparison/prapr_mapping_audit.csv

Consolidate mutators mapped to the same unified family by summing their published frequencies.

Rank the resulting families by aggregated frequency in descending order.

Break ties by the earliest published PraPR rank and then by family label.

Evaluate complete-fix coverage for (k=1,3,5,10).

The mapped top-ten family order is:

MCR, VR, ROR, CR, CI, MPM, AOR, MRV, DTR, VA

11.2 Run the Comparison

From the repository root:

python RQ5/prapr_comparison/run_prapr_comparison.py

11.3 Expected Results

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

11.4 PraPR Output Files

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

11.5 Interpretation

The PraPR results represent complete-fix coverage after cross-abstraction taxonomy mapping.

They must not be described as:

the number of bugs repaired by PraPR;

a reproduction of PraPR;

a direct source-level baseline; or

end-to-end evidence that one APR system outperforms another.

12. Recommended Reproduction Order

The core mutation experiments and RQ5 analyses can be executed independently.

Step 1: Run the Core Mutation Experiments

python3 scripts/export_dev_patches.py <Project>
python3 scripts/run_one_project_both_final.py <Project> --jobs <N>
python3 scripts/summarize_mutation_by_project.py \
  "$EXPERIMENT_ROOT/logs" \
  --outdir "$EXPERIMENT_ROOT/results"
python3 scripts/compute_patches.py \
  --logs-root "$EXPERIMENT_ROOT/logs"

Step 2: Reproduce the Complexity–Popularity Correlation

python RQ5/complexity_popularity.py

Verify:

RQ5/complexity_popularity_correlation.csv

Step 3: Reproduce Cost-Aware Operator Selection

python RQ5/cost_aware_operator_selection.py

Verify:

RQ5/cost_aware_results/primary_scheme_summary.csv
RQ5/cost_aware_results/paired_comparisons.csv
RQ5/cost_aware_results/README_RESULTS.txt

Step 4: Reproduce the PraPR Supplementary Comparison

python RQ5/prapr_comparison/run_prapr_comparison.py

Verify:

RQ5/prapr_comparison/prapr_mapped_ranking.csv
RQ5/prapr_comparison/prapr_supplementary_comparison.csv

13. Reproducibility Notes

Paths documented for RQ5 are repository-relative and do not require user-specific or machine-specific directories.

The documented random seed makes the random baseline and paired-bootstrap procedure reproducible, subject to compatible Python, library, and solver versions.

The MAJOR and PIT experiments depend on the configured Java versions, Defects4J installation, project dependencies, and benchmark availability.

RQ5 proxy costs represent structural complexity tiers rather than measured runtime or candidate-generation cost.

The PraPR analysis is a taxonomy-mapped supplementary comparison rather than a full execution or reproduction of PraPR.
