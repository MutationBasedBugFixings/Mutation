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
│
└── RQ5/
    ├── README.md
    ├── strict_bug_operator_mappings.csv
    ├── cost_aware_operator_selection.py
    ├── complexity_popularity.py
    ├── complexity_popularity_correlation.csv
    │
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
    │
    └── prapr_comparison/
        ├── README.md
        ├── prapr_published_mutator_frequencies.csv
        ├── prapr_mapping_audit.csv
        ├── prapr_mapped_ranking.csv
        ├── strict_java_bug_operator_mappings.csv
        ├── run_prapr_comparison.py
        └── prapr_supplementary_comparison.csv
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
and structural proxy-cost budgets.

It also includes:

- the complexity–popularity analysis used to support the search-space
  interpretation; and
- a supplementary cross-abstraction comparison with PraPR.

The RQ5 replication materials are located in:

```text
RQ5/
```

---

### 7.1 Input Data

The operator-selection experiment uses:

```text
RQ5/strict_bug_operator_mappings.csv
```

Required columns:

- `language`
- `project`
- `operators`

The `operators` column contains semicolon-separated canonical operator codes.
An optional `bug_id` column may also be included.

The cleaned dataset contains 925 eligible bug-to-operator mappings:

| Language | Eligible mappings |
|---|---:|
| Java | 619 |
| Python | 178 |
| JavaScript | 128 |
| **Total** | **925** |

A fix is counted as covered only when **all operator families required by its
developer patch** are included in the selected operator set.

---

### 7.2 GitHub-Relative Path Configuration

The RQ5 replication scripts should not contain machine-specific paths.

In `RQ5/cost_aware_operator_selection.py`, configure the script directory as:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "cost_aware_results"
MEASURED_COST_FILE = BASE_DIR / "operator_runtime_costs.csv"

INPUT_CANDIDATES = (
    BASE_DIR / "strict_bug_operator_mappings.csv",
)
```

With this configuration, the experiment can be executed directly after cloning
the repository.

---

### 7.3 Cost-Aware Operator Selection

The cost-aware experiment evaluates whether the search-space complexity tiers
identified in RQ3 improve operator selection when repair relevance and
structural proxy cost are considered jointly.

#### Proxy-Cost Schemes

The primary exponential mapping is:

| Complexity tier | Proxy cost |
|---|---:|
| Low | 1 |
| Moderate | 2 |
| High | 4 |
| Extremely High | 8 |

Two additional mappings are evaluated as sensitivity checks:

| Scheme | Low | Moderate | High | Extremely High |
|---|---:|---:|---:|---:|
| Linear | 1 | 2 | 3 | 4 |
| Exponential | 1 | 2 | 4 | 8 |
| Steep | 1 | 3 | 6 | 10 |

The evaluated budget fractions are:

```text
10%, 20%, 30%, 40%, and 50%
```

Each budget is calculated as a fraction of the total proxy cost of the
canonical operator set.

#### Evaluated Strategies

The experiment compares five strategies under the same proxy-cost budget:

- **Frequency** – operators are ranked by their occurrence frequency in the
  training fixes.
- **Frequency-per-cost** – operators are ranked by training frequency divided
  by proxy cost.
- **Exact cost-aware** – a mixed-integer linear program selects the
  cost-feasible portfolio that maximises complete-fix coverage on the training
  projects.
- **Cheap-first** – operators are ranked by increasing proxy cost, with
  frequency used for tie-breaking.
- **Random** – a no-ranking baseline based on 1,000 randomly generated
  cost-feasible operator portfolios.

For ranking-based strategies, operators are considered in ranked order and
selected whenever their cost fits within the remaining budget.

#### Exact Cost-Aware Objective

For an operator set \(S\), the total proxy cost is:

\[
\mathrm{Cost}(S)=\sum_{o\in S}c(o)
\]

The exact cost-aware strategy selects:

\[
S_C^*=\arg\max_{S\subseteq\mathcal{O}}
\sum_{b\in B_{\mathrm{train}}}
\mathbb{I}[R_b\subseteq S]
\]

subject to:

\[
\sum_{o\in S}c(o)\leq C
\]

where:

- \(R_b\) is the complete operator set required by fix \(b\);
- \(c(o)\) is the proxy cost of operator \(o\); and
- \(C\) is the available budget.

#### Evaluation Settings

| Setting | Value |
|---|---:|
| Project-level held-out folds | 5 |
| Random portfolios per condition | 1,000 |
| Paired bootstrap iterations | 5,000 |
| Random seed | 20260322 |
| Primary proxy-cost scheme | Exponential |

#### Run

From the repository root:

```bash
python RQ5/cost_aware_operator_selection.py
```

#### Generated Outputs

The script writes the following files to `RQ5/cost_aware_results/`:

- `operator_cost_table.csv` – complexity tier and assigned cost for every
  operator and cost scheme
- `heldout_results.csv` – fold-level coverage and selected-portfolio
  statistics
- `heldout_summary.csv` – aggregated held-out results by language, cost scheme,
  budget, and strategy
- `selected_portfolios.csv` – operators selected in every fold and condition
- `out_of_fold_predictions.csv` – bug-level held-out coverage outcomes
- `paired_comparisons.csv` – paired-bootstrap differences and 95% confidence
  intervals
- `primary_scheme_summary.csv` – summary for the primary exponential mapping
- `README_RESULTS.txt` – human-readable result summary
- `coverage_java.svg` – Java coverage figure
- `coverage_python.svg` – Python coverage figure
- `coverage_javascript.svg` – JavaScript coverage figure

#### Primary Results at the 30% Proxy-Cost Budget

| Language | Frequency | Frequency-per-cost | Exact cost-aware | Cheap-first | Random |
|---|---:|---:|---:|---:|---:|
| Java | 48.79% | 58.97% | 59.45% | 22.29% | 17.09% |
| Python | 61.24% | 69.10% | 68.54% | 19.66% | 19.32% |
| JavaScript | 30.47% | 47.66% | 38.28% | 33.59% | 21.89% |

At the 30% budget, frequency-per-cost improves over frequency by:

- **Java:** 10.18 percentage points
- **Python:** 7.87 percentage points
- **JavaScript:** 17.19 percentage points

Across all 45 combinations of language, budget, and proxy-cost mapping:

- frequency-per-cost performs better than frequency in 12 comparisons;
- frequency-per-cost performs worse in 3 comparisons;
- 30 comparisons are inconclusive;
- exact cost-aware performs better in 9 comparisons and worse in 6; and
- frequency outperforms cheap-first in 35 comparisons.

#### Interpretation Limitation

The linear, exponential, and steep costs are structural proxies derived from
the RQ3 complexity tiers.

They are not:

- measured execution times;
- mutant counts;
- generated-candidate counts; or
- validation costs.

The results therefore represent complete-fix coverage under structural
proxy-cost budgets. They must not be interpreted as evidence of wall-clock
runtime reduction.

---

### 7.4 Complexity–Popularity Correlation

This analysis examines the relationship between operator popularity and
search-space complexity across the 33 canonical operators.

#### Complexity Encoding

The ordinal complexity tiers are encoded as:

| Complexity tier | Score |
|---|---:|
| Low | 1 |
| Moderate | 2 |
| High | 3 |
| Extremely High | 4 |

Operator popularity is the percentage of the 955 representable fixes whose
developer patches contain the operator.

#### Run

From the repository root:

```bash
python RQ5/complexity_popularity.py
```

#### Expected Output

```text
Number of operators: 33
Spearman rho: 0.5723
Spearman p-value: 0.000501
Kendall tau-b: 0.4863
Kendall p-value: 0.000437
```

The script also writes:

```text
RQ5/complexity_popularity_correlation.csv
```

#### Interpretation

Spearman's rank correlation shows a statistically significant positive
association between operator popularity and search-space complexity:

```text
rho = 0.5723
p = 0.000501
n = 33
```

More frequently required operators generally tend to have larger search
spaces, although the relationship is not uniform.

For example, `VA` and `MOCS` belong to the **Extremely High** complexity tier,
but each appears in only 7.1% of representable fixes.

The Kendall tau-b result is included as a robustness check.

---

### 7.5 Supplementary Cross-Abstraction Comparison with PraPR

The PraPR comparison is located in:

```text
RQ5/prapr_comparison/
```

PraPR ranks JVM bytecode-level mutators using published frequencies, whereas
this study evaluates unified source-level semantic operator families.

PraPR is therefore treated as a **supplementary cross-abstraction reference**
rather than a direct source-level baseline.

The analysis maps PraPR's published mutator priorities to the unified taxonomy
and evaluates the resulting family ranking on the same 619 strict Java
mappings.

This analysis does **not**:

- run PraPR;
- generate bytecode mutants;
- reproduce PraPR's full APR pipeline; or
- measure end-to-end repair success.

#### PraPR Mapping Procedure

1. Read the published mutator frequencies from:

   ```text
   RQ5/prapr_comparison/prapr_published_mutator_frequencies.csv
   ```

2. Apply the documented mutator-to-family mapping in:

   ```text
   RQ5/prapr_comparison/prapr_mapping_audit.csv
   ```

3. Consolidate mutators mapped to the same unified family by summing their
   published frequencies.
4. Rank the resulting families by aggregated frequency in descending order.
5. Break ties by the earliest published PraPR rank and then by family label.
6. Evaluate complete-fix coverage for `k = 1, 3, 5, and 10`.

The mapped top-ten family order is:

```text
MCR, VR, ROR, CR, CI, MPM, AOR, MRV, DTR, VA
```

#### Run

From the repository root:

```bash
python RQ5/prapr_comparison/run_prapr_comparison.py
```

#### Expected Results

| k | Selected families | Covered fixes | Coverage |
|---:|---|---:|---:|
| 1 | MCR | 54 / 619 | 8.72% |
| 3 | MCR, VR, ROR | 76 / 619 | 12.28% |
| 5 | MCR, VR, ROR, CR, CI | 180 / 619 | 29.08% |
| 10 | MCR, VR, ROR, CR, CI, MPM, AOR, MRV, DTR, VA | 333 / 619 | 53.80% |

#### Output Files

- `prapr_mapped_ranking.csv` – consolidated source-level family ranking
- `prapr_supplementary_comparison.csv` – coverage values reported in the
  manuscript
- `strict_java_bug_operator_mappings.csv` – the 619 eligible Java mappings
- `prapr_mapping_audit.csv` – mapping decisions and rationales

#### Interpretation

The PraPR results represent complete-fix coverage after cross-abstraction
taxonomy mapping.

They must not be described as:

- the number of bugs repaired by PraPR;
- a reproduction of PraPR;
- a direct source-level baseline; or
- end-to-end evidence that one APR system outperforms another.

---

### 7.6 Recommended RQ5 Reproduction Order

Run the analyses independently from the repository root.

#### Step 1 – Complexity–Popularity Correlation

```bash
python RQ5/complexity_popularity.py
```

Verify:

```text
RQ5/complexity_popularity_correlation.csv
```

#### Step 2 – Cost-Aware Operator Selection

```bash
python RQ5/cost_aware_operator_selection.py
```

Verify:

```text
RQ5/cost_aware_results/primary_scheme_summary.csv
RQ5/cost_aware_results/paired_comparisons.csv
RQ5/cost_aware_results/README_RESULTS.txt
```

#### Step 3 – PraPR Supplementary Comparison

```bash
python RQ5/prapr_comparison/run_prapr_comparison.py
```

Verify:

```text
RQ5/prapr_comparison/prapr_mapped_ranking.csv
RQ5/prapr_comparison/prapr_supplementary_comparison.csv
```

---

## 8. Reproducibility Notes

- All RQ5 paths documented in this README are repository-relative.
- No user-specific or machine-specific directory is required for the RQ5
  analyses.
- The documented random seed makes the random baseline and paired-bootstrap
  procedure reproducible, subject to compatible Python, library, and solver
  versions.
- The MAJOR and PIT experiments depend on the configured Java versions,
  Defects4J installation, project dependencies, and benchmark availability.
- RQ5 proxy costs represent structural complexity tiers rather than measured
  runtime or candidate-generation cost.
- The PraPR analysis is a taxonomy-mapped supplementary comparison rather than
  a full execution or reproduction of PraPR.

---

## 9. Archival Package

The replication package is archived on Zenodo:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19362997.svg)](https://doi.org/10.5281/zenodo.19362997)
