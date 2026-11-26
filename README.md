# Mutation-Based Bug Fixing Experiments

This repository contains a small, self-contained toolkit for running
**mutation-based experiments on Defects4J projects** and analysing the
resulting patches.

It also contains the replication materials for **RQ5**, including cost-aware
operator selection, complexity–popularity correlation, and the supplementary
cross-abstraction comparison with PraPR.

The workflow is:

1. Export **developer patches** as buggy-versus-fixed diffs.
2. Run **MAJOR + PIT** mutation analysis on Defects4J bugs.
3. Summarise mutation results per project and per bug.
4. Analyse **plausible mutants per operator**.
5. Reproduce the **RQ5 operator-selection analyses**.

The core mutation workflow lives in the `scripts/` directory. The RQ5
replication materials are located in `RQ5/`.

---

## 1. Environment & Dependencies

### Core Requirements

- Linux (tested on Ubuntu-like systems)
- Python ≥ 3.8
- Java 8 (for MAJOR compilation)
- Java 11 (for Defects4J CLI and PIT runtime)
- [Defects4J](https://github.com/rjust/defects4j) installed and working

### Environment Variables

Set these variables before running the scripts. Adapt the paths to your
machine:

```bash
export D4J_HOME=/home1/yourname/tools_and_libs/defects4j
export EXPERIMENT_ROOT=/home1/yourname/my_mutation_experiments

export JAVA11_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export JAVA8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export MAJOR_JAVA_HOME="$JAVA8_HOME"
```

Check that Defects4J works:

```bash
$D4J_HOME/framework/bin/defects4j info -p Lang -b 1
```

### RQ5 Requirements

The RQ5 analyses require:

- Python ≥ 3.10
- pandas
- NumPy
- SciPy with `scipy.optimize.milp`
- scikit-learn
- Matplotlib

Install the dependencies from the repository root:

```bash
python -m pip install pandas numpy scipy scikit-learn matplotlib
```

---

## 2. Scripts Overview

All core mutation-analysis scripts live in `scripts/`.

### `run_one_project_both_final.py`

Runs **MAJOR** and **PIT** for a given Defects4J project and selected bugs on
the **fixed revision**.

It supports:

- process-level parallelism across bugs;
- PIT worker threads;
- PIT fork configuration; and
- Java heap-size tuning.

Main outputs:

- `mutants.log`
- `kill.csv`
- `major_summary.csv`
- `pit_summary.csv`

### `export_dev_patches.py`

Exports developer patches as unified `diff -ruN` files by comparing the buggy
and fixed revisions of each Defects4J bug.

### `summarize_mutation_by_project.py`

Scans mutation logs and creates:

- per-project mutation summaries; and
- per-bug mutation summaries.

### `compute_patches.py`

Reads `kill.csv` and `mutants.log` for each bug and computes:

- total mutant count;
- plausible mutant count (`LIVE` status);
- aggregate per-project counts; and
- plausible-mutant usage counts per operator.

### `evaluate_patches.py`

Provides helper functions for follow-up patch analysis, such as:

- comparing generated patches with developer patches;
- filtering patches by plausibility or correctness; and
- exporting additional tables for the paper.

Run the following command to inspect the options available in the current
version:

```bash
cd scripts
python3 evaluate_patches.py -h
```

### RQ5 Scripts

The RQ5 analyses are implemented in the following files:

- `RQ5/cost_aware_operator_selection.py`
- `RQ5/complexity_popularity.py`
- `RQ5/prapr_comparison/run_prapr_comparison.py`

---

## 3. Typical Workflow

### Step 1 – Export Developer Patches

This step checks out the buggy and fixed revisions of each bug and writes a
unified diff file.

```bash
cd scripts

# List available Defects4J projects
python3 export_dev_patches.py --list

# Export all developer patches for one project
python3 export_dev_patches.py Lang

# Export patches for multiple projects and overwrite existing files
python3 export_dev_patches.py Lang Mockito --force
```

Example output:

```text
$EXPERIMENT_ROOT/results/dev_patches/Lang/Lang-1.diff
$EXPERIMENT_ROOT/results/dev_patches/Lang/Lang-2.diff
...
```

---

### Step 2 – Run MAJOR + PIT

The script checks out the **fixed revision** of each bug, compiles it, and runs
both mutation engines.

Run all active bugs in a project:

```bash
cd scripts
python3 run_one_project_both_final.py Lang \
  --jobs 4 \
  --threads 8 \
  --forks 2 \
  --jvm-xmx 8g
```

Run a single bug:

```bash
python3 run_one_project_both_final.py Lang 2 --threads 6 --forks 2
```

Run a selected subset of bugs:

```bash
python3 run_one_project_both_final.py Lang --bugs 1,5,9,12
```

Key options:

- `project` – Defects4J project name, such as `Lang` or `Math`
- `bug_id` – optional positional ID for a single bug
- `--list-bugs` – print all active bug IDs for the project
- `--bugs` – comma-separated list of selected bug IDs
- `--jobs` – number of bugs executed in parallel
- `--threads` – number of PIT worker threads
- `--forks` – PIT fork count
- `--jvm-xmx` – Java heap size, for example `8g`

Per-bug outputs are stored under:

```text
$EXPERIMENT_ROOT/logs/<Project>-<Bug>/
├── mutants.log
├── kill.csv
├── major_summary.csv
└── pit_summary.csv
```

---

### Step 3 – Summarise Mutation Results

After the mutation runs complete, create project-level and bug-level summaries:

```bash
cd scripts
python3 summarize_mutation_by_project.py \
  "$EXPERIMENT_ROOT/logs" \
  --outdir "$EXPERIMENT_ROOT/results"
```

Generated files include:

- `mutation_summary_by_project.csv`
- `mutation_summary_by_bug.csv`

The summaries report, for each engine:

- project and bug;
- total mutants;
- killed mutants;
- survived mutants; and
- kill rate.

---

### Step 4 – Compute Plausible Mutants per Operator

The script treats mutants marked `LIVE` in `kill.csv` as plausible and reads
the operator associated with each mutant from `mutants.log`.

Process a single logs root:

```bash
cd scripts
python3 compute_patches.py --logs-root "$EXPERIMENT_ROOT/logs"
```

Alternatively, process all `logs_*` directories under the current folder:

```bash
python3 compute_patches.py --all-projects
```

Per-project outputs are written under `results/<Project>/`:

- `per_bug_summary.csv` – total and plausible mutant counts for each bug
- `per_project_summary.csv` – aggregated project-level counts
- `operator_usage.csv` – plausible-mutant count for each operator

These files support the operator-level analysis reported in the paper.

---

### Step 5 – Evaluate Patches

Use `evaluate_patches.py` for optional or custom analyses, including:

- comparison with developer patches;
- plausibility or correctness filtering; and
- export of additional paper tables.

```bash
cd scripts
python3 evaluate_patches.py -h
```

---

## 4. Reproducing the Paper’s Main Mutation Outputs

From the repository root, run the following sequence:

```bash
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

# 5. Inspect optional patch-evaluation commands
python3 scripts/evaluate_patches.py -h
```

---

## 5. Repository Structure

```text
Mutation/
│
├── README.md
│
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
├── logs/
│   ├── Lang-1/
│   │   ├── mutants.log
│   │   ├── kill.csv
│   │   ├── major_summary.csv
│   │   └── pit_summary.csv
│   └── <Project>-<Bug>/
│       └── ...
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
├── d4j_work_diff/
│   └── ...
|
rq5/
├── README.md
├── data/
│   ├── Defects4j_full.xlsx
│   ├── BugInPy.xlsx
│   ├── bugjs_manual(1).csv
│   └── prapr_mapped_ranking.csv
├── strict_bug_operator_mappings.csv
├── rq5_source_level_portfolio_analysis_corrected.py
├── cost_aware_operator_selection.py
├── complexity_popularity.py
├── rq5_results_corrected_audit/
│   ├── cleaning_audit_all_rows.csv
│   ├── rows_requiring_manual_review.csv
│   ├── strict_bug_operator_mappings.csv
│   ├── dataset_count_audit.csv
│   ├── project_fold_audit.csv
│   ├── selected_portfolios_within_language.csv
│   ├── within_language_project_cv_folds.csv
│   ├── within_language_project_cv_summary.csv
│   ├── cross_language_transfer.csv
│   └── prapr_supplementary_comparison.csv
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
    ├── prapr_published_mutator_frequencies.csv
    ├── prapr_mapping_audit.csv
    ├── prapr_mapped_ranking.csv
    └── README.md
```

The `logs/`, `results/`, `d4j_work/`, and `d4j_work_diff/` directories are
created or populated during execution.

---

## 6. Data Transparency & Reproducibility

This study analyses the full **Defects4J v2.0.1** dataset containing 835 bugs.

- **803 bugs** were analysed for mutant-operator expressiveness.
- **32 bugs** were excluded because of benchmark depletion, including
  dependency or test failures.
- The manual decomposition of developer patches into atomic mutant operators
  is documented in `transparency/atomic_decomposition.md`.
- The Defects4J manual analysis is provided in
  `transparency/defects4j.csv`.
- The BugsInPy manual analysis is provided in
  `transparency/BugsInPy.xlsx`.

---

## 7. RQ5: Operator Selection and Supplementary Comparisons

RQ5 evaluates source-level mutant-operator selection under fixed operator-count
and structural proxy-cost budgets. It also examines cross-language transfer
and includes two supplementary analyses: the relationship between operator
complexity and popularity, and a cross-abstraction comparison with PraPR.

The replication materials are stored in the lowercase repository directory:

```text
rq5/
```

All paths below are relative to the repository root.

---

### 7.1 Input Data and Final Mapping Cohort

The RQ5 analyses use three manually annotated benchmark datasets:

| Language | Original annotation records | Final eligible mappings |
|---|---:|---:|
| Java (Defects4J) | 835 | 633 |
| Python (BugsInPy) | 300 | 194 |
| JavaScript (BugsJS) | 219 | 128 |
| **Total** | **1,354** | **955** |

The final cohort contains 955 eligible bug-to-operator mappings. The final
mapping file has no duplicate `language`–`project`–`bug_id` identities.

The canonical input is:

```text
rq5/strict_bug_operator_mappings.csv
```

The file contains the language, project, bug identifier, and semicolon-separated
canonical operator-family codes. The `operators` field represents the complete
set of operator families assigned to the corresponding developer patch.

The source annotation files are retained for traceability:

```text
rq5/data/Defects4j_full.xlsx
rq5/data/BugInPy.xlsx
rq5/data/bugjs_manual(1).csv
```

A fix is counted as covered only when **all operator families required by its
developer patch** are included in the selected operator set. Therefore, the
reported metric is complete-fix representability under an operator-set budget;
it is not a count of patches generated or bugs automatically repaired.

The source-level cleaning audit is retained in:

```text
rq5/rq5_results_corrected_audit/cleaning_audit_all_rows.csv
rq5/rq5_results_corrected_audit/rows_requiring_manual_review.csv
rq5/rq5_results_corrected_audit/dataset_count_audit.csv
rq5/rq5_results_corrected_audit/project_fold_audit.csv
```

The audit files preserve the original records, eligibility decisions, project
identities, and fold assignments.

---






Only include files that are present in the final release. In particular, the
three SVG filenames above are the names produced by the current server run.
The generated audit and result directories should be committed after the
corresponding experiments have been rerun on the final 955-mapping input.

#### Portable configuration: source-level script

The source-level script must use paths relative to its own location rather
than the original research-server directory. Its configuration should follow
this pattern:

```python
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

JAVA_FILE = DATA_DIR / "Defects4j_full.xlsx"
PYTHON_FILE = DATA_DIR / "BugInPy.xlsx"
JAVASCRIPT_FILE = DATA_DIR / "bugjs_manual(1).csv"

OUTPUT_DIR = BASE_DIR / "rq5_results_corrected_audit"
SOURCE_BASELINE_FILE = DATA_DIR / "source_level_baselines.csv"
PRAPR_FILE = BASE_DIR / "prapr_comparison" / "prapr_mapped_ranking.csv"
```

#### Portable configuration: cost-aware script

The cost-aware script should load the final mapping from the package and write
its outputs inside the package:

```python
BASE_DIR = Path(__file__).resolve().parent

INPUT_CANDIDATES = (
    BASE_DIR / "strict_bug_operator_mappings.csv",
    BASE_DIR / "rq5_results_corrected_audit" / "strict_bug_operator_mappings.csv",
)

OUTPUT_DIR = BASE_DIR / "cost_aware_results"
MEASURED_COST_FILE = BASE_DIR / "operator_runtime_costs.csv"
```

If `operator_runtime_costs.csv` is not supplied, the experiment uses the
structural proxy-cost schemes described below. The scripts must not retain
machine-specific paths such as `/home1/furqan/...`.

---

### 7.3 Fixed Operator-Count Selection and Cross-Language Evaluation

The source-level evaluation compares three operator-selection strategies:

- **Frequency-based:** ranks operator families by the number of training fixes
  in which each family occurs and selects the top \(k\).
- **Composition-aware:** selects a size-\(k\) operator set that maximises
  complete-fix coverage on the training folds. Operator frequency is used as
  a secondary objective when multiple sets achieve the same coverage.
- **No-ranking:** uniformly samples 1,000 size-\(k\) operator sets and reports
  their mean held-out coverage.

The evaluated operator budgets are:

```text
k = 1, 3, 5, and 10
```

For each language, projects are divided into five folds. Four folds are used
to construct the operator sets and the remaining fold is held out for
evaluation. Coverage is pooled across the held-out projects from all folds.

The source-level experiment uses a fixed random seed of `42` and 1,000 random
portfolios for the no-ranking baseline.

The script is:

```text
rq5/rq5_source_level_portfolio_analysis_corrected.py
```

Run it from the repository root:

```bash
python rq5/rq5_source_level_portfolio_analysis_corrected.py
```

The main outputs are:

| Output | Description |
|---|---|
| `within_language_project_cv_summary.csv` | Aggregated within-language results |
| `within_language_project_cv_folds.csv` | Fold-level within-language results |
| `selected_portfolios_within_language.csv` | Selected operator sets |
| `cross_language_transfer.csv` | Cross-language transfer results |
| `strict_bug_operator_mappings.csv` | Final eligible mapping cohort |
| `cleaning_audit_all_rows.csv` | Audit of all 1,354 source records |
| `dataset_count_audit.csv` | Per-language eligibility counts |
| `project_fold_audit.csv` | Project-to-fold assignments |
| `prapr_supplementary_comparison.csv` | Supplementary mapped PraPR results, when the ranking input is available |

The cross-language analysis constructs an operator set from the source language
and transfers it unchanged to the target language. The generated
`cross_language_transfer.csv` is the authoritative source for the reported
cross-language values.

---

### 7.4 Cost-Aware Operator Selection

The cost-aware experiment evaluates whether the RQ3 search-space complexity
tiers can guide operator selection under structural proxy-cost budgets.

#### Proxy-cost schemes

Three mappings are evaluated:

| Scheme | Low | Moderate | High | Extremely High |
|---|---:|---:|---:|---:|
| Linear | 1 | 2 | 3 | 4 |
| Exponential | 1 | 2 | 4 | 8 |
| Steep | 1 | 3 | 6 | 10 |

The primary scheme is exponential. The evaluated budget fractions are:

```text
10%, 20%, 30%, 40%, and 50%
```

Each budget is a fraction of the total cost of the 33 canonical operator
families under the corresponding scheme.

#### Evaluated strategies

Five strategies are compared under the same cost budget:

- **Frequency:** ranks operators by their occurrence frequency in the training
  fixes.
- **Frequency-per-cost:** ranks operators by training frequency divided by
  proxy cost.
- **Exact cost-aware:** uses a mixed-integer linear program to select a
  cost-feasible portfolio that maximises complete-fix coverage on the training
  projects.
- **Cheap-first:** ranks operators by increasing proxy cost, using frequency
  to break ties.
- **Random:** samples 1,000 cost-feasible operator portfolios.

For the ranking-based strategies, operators are considered in ranked order and
selected whenever their cost fits within the remaining budget.

For an operator set \(S\), its total proxy cost is:

\[
\operatorname{Cost}(S)=\sum_{o\in S}c(o).
\]

The exact cost-aware strategy selects:

\[
S_C^* =
\arg\max_{S\subseteq\mathcal{O}}
\sum_{b\in B_{\mathrm{train}}}
\mathbb{I}[R_b\subseteq S]
\]

subject to:

\[
\sum_{o\in S}c(o)\leq C.
\]

Here, \(R_b\) is the complete operator set required by fix \(b\), \(c(o)\) is
the proxy cost of operator \(o\), and \(C\) is the available budget.

#### Evaluation settings

| Setting | Value |
|---|---:|
| Project-level held-out folds | 5 |
| Random portfolios per condition | 1,000 |
| Paired bootstrap iterations | 5,000 |
| Random seed | 20260322 |
| Primary proxy-cost scheme | Exponential |
| Canonical operator families | 33 |

The script is:

```text
rq5/cost_aware_operator_selection.py
```

Run it from the repository root after the final mapping file has been
generated or copied to `rq5/strict_bug_operator_mappings.csv`:

```bash
python rq5/cost_aware_operator_selection.py
```

The script writes:

- `operator_cost_table.csv` – assigned operator costs under each scheme;
- `heldout_results.csv` – fold-level coverage and portfolio statistics;
- `heldout_summary.csv` – aggregated results by language, scheme, budget, and strategy;
- `selected_portfolios.csv` – selected operators for each fold and condition;
- `out_of_fold_predictions.csv` – bug-level held-out coverage outcomes;
- `paired_comparisons.csv` – paired-bootstrap differences and 95% confidence intervals;
- `primary_scheme_summary.csv` – results for the primary exponential scheme;
- `README_RESULTS.txt` – human-readable summary; and
- `coverage_java.svg`, `coverage_python.svg`, and `coverage_javascript.svg` – coverage figures.

**Result-integrity requirement:** the cost-aware results must be generated from
the final 955-mapping file. Before publishing the result directory, verify that
the `paired_bugs` column in `paired_comparisons.csv` reports 633 Java, 194
Python, and 128 JavaScript bugs. Do not reuse a previous 925-mapping summary
or its hard-coded percentages.

The CSV files generated by the final run are the authoritative source for
numerical results. The README intentionally does not duplicate a 30% budget
summary or statistical significance counts that have not been checked against
the final 955-mapping output.

#### Interpretation limitation

The linear, exponential, and steep costs are structural proxies derived from
the RQ3 complexity tiers. They are not measured execution times, mutant counts,
generated-candidate counts, or validation costs. The results therefore
represent complete-fix coverage under structural proxy-cost budgets and must
not be interpreted as evidence of wall-clock runtime reduction.

---

### 7.5 Complexity–Popularity Correlation

This supplementary analysis examines the relationship between operator
popularity and search-space complexity across the 33 canonical operator
families.

The ordinal complexity tiers are encoded as:

| Complexity tier | Score |
|---|---:|
| Low | 1 |
| Moderate | 2 |
| High | 3 |
| Extremely High | 4 |

Operator popularity is calculated as the percentage of the final eligible
mappings whose developer patches contain the corresponding operator family.

The script is:

```text
rq5/complexity_popularity.py
```

Run:

```bash
python rq5/complexity_popularity.py
```

The generated correlation CSV is the authoritative source for the Spearman
and Kendall statistics:

```text
rq5/complexity_popularity_correlation.csv
```

The correlation script and its output must be checked against the final
955-mapping cohort before its numerical statistics are quoted. Values from an
earlier cohort should not be carried forward without rerunning the analysis.

---

### 7.6 Supplementary Cross-Abstraction Comparison with PraPR

PraPR ranks JVM bytecode-level mutators using published frequencies, whereas
this study evaluates unified source-level semantic operator families.
Accordingly, PraPR is treated as a **supplementary cross-abstraction
reference**, not as a direct source-level baseline.

The mapping procedure:

1. Reads the published PraPR mutator frequencies.
2. Applies the documented mutator-to-family mapping.
3. Aggregates frequencies for mutators mapped to the same canonical family.
4. Ranks the unified families by aggregated frequency.
5. Breaks ties using the earliest published PraPR rank and then the family label.
6. Evaluates complete-fix coverage at \(k=1,3,5,10\) on the final 633 Java mappings.

The input and mapping audit are retained in:

```text
rq5/prapr_comparison/prapr_supplementary_comparison.csv
rq5/prapr_comparison/prapr_mapping_audit.csv
rq5/prapr_comparison/prapr_mapped_ranking.csv
```

The updated coverage output is:

```text
rq5/rq5_results_corrected_audit/prapr_supplementary_comparison.csv
```

The output generated from the final 633 Java mappings must be used for the
reported denominator and coverage values. The previous 619-Java-mapping
figures are obsolete and should not be retained.

This analysis does **not** run PraPR, generate bytecode mutants, reproduce
PraPR's full APR pipeline, or measure end-to-end repair success. It measures
complete-fix coverage after mapping published bytecode-level priorities to
the source-level taxonomy.

---

### 7.7 Recommended Reproduction Order

Run the analyses from the repository root.

#### Step 1 – Generate the final source-level mappings and operator-count results

```bash
python rq5/rq5_source_level_portfolio_analysis_corrected.py
```

Verify the final mapping counts:

```text
Java: 633
Python: 194
JavaScript: 128
Total: 955
```

Copy the generated canonical mapping to the package root for the cost-aware
script:

```bash
cp rq5/rq5_results_corrected_audit/strict_bug_operator_mappings.csv \
   rq5/strict_bug_operator_mappings.csv
```

#### Step 2 – Run cost-aware operator selection

```bash
python rq5/cost_aware_operator_selection.py
```

Verify:

```text
rq5/cost_aware_results/primary_scheme_summary.csv
rq5/cost_aware_results/paired_comparisons.csv
rq5/cost_aware_results/README_RESULTS.txt
```

Check that the paired-comparison denominators are 633, 194, and 128.

#### Step 3 – Run the complexity–popularity analysis

```bash
python rq5/complexity_popularity.py
```

Verify that its input is the final 955-mapping cohort and inspect:

```text
rq5/complexity_popularity_correlation.csv
```

#### Step 4 – Verify the PraPR supplementary comparison

Verify that the output was generated from the final 633 Java mappings:

```text
rq5/rq5_results_corrected_audit/prapr_supplementary_comparison.csv
```

---

## 8. Reproducibility Notes

- The final RQ5 cohort contains 955 unique language–project–bug mappings:
  633 Java, 194 Python, and 128 JavaScript.
- The original annotation corpus contains 1,354 records: 835 Java, 300 Python,
  and 219 JavaScript.
- The source-level operator-count analysis uses five project-level folds,
  \(k\in\{1,3,5,10\}\), 1,000 random portfolios, and random seed `42`.
- The cost-aware analysis uses five project-level folds, 1,000 random
  portfolios, 5,000 paired-bootstrap iterations, and random seed `20260322`.
- The 33-family taxonomy and its complexity tiers are defined in the
  replication scripts and should be kept consistent with the manuscript.
- RQ5 proxy costs represent structural complexity tiers, not measured runtime
  or candidate-generation cost.
- The PraPR analysis is a taxonomy-mapped supplementary comparison rather
  than a full execution or reproduction of PraPR.
- A published source-level baseline is not included in the current run unless
  a corresponding `source_level_baselines.csv` input is supplied. A generated
  template is not an experimental baseline result.
- Reproduction may depend on compatible Python, pandas, NumPy, SciPy,
  scikit-learn, Matplotlib, and solver versions. Record the versions used for
  the archived run.

---

## 9. Archival Package

The GitHub repository is the public source for the RQ5 replication materials:

```text
https://github.com/MutationBasedBugFixings/Mutation
```

A Zenodo DOI should be added here after the final, versioned replication
package has been deposited. Do not claim a Zenodo archive until the DOI is
available.


[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19362997.svg)](https://doi.org/10.5281/zenodo.19362997)
