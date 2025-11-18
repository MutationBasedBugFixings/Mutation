# Mutation-Based Bug Fixing Experiments

This repository contains a small, self-contained toolkit for running
**mutation-based experiments on Defects4J projects** and analysing the
resulting patches.

The workflow is:

1. Export **developer patches** (buggy vs fixed diffs).
2. Run **MAJOR + PIT** mutation analysis on Defects4J bugs.
3. Summarise mutation results per project / per bug.
4. Analyse **plausible mutants per operator**.
5. (Optional) Evaluate generated patches vs developer patches.

All functionality lives in the `scripts/` directory.

---

## 1. Environment & Dependencies

### Requirements

- Linux (tested on Ubuntu-like systems)
- Python ≥ 3.8
- Java 8 (for MAJOR compilation)
- Java 11 (for Defects4J CLI and PIT runtime)
- [Defects4J](https://github.com/rjust/defects4j) installed and working

### Environment variables

Set these before running the scripts (adapt paths to your machine):

```bash
export D4J_HOME=/home1/yourname/tools_and_libs/defects4j
export EXPERIMENT_ROOT=/home1/yourname/my_mutation_experiments

export JAVA11_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export JAVA8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export MAJOR_JAVA_HOME="$JAVA8_HOME"
````

Check that Defects4J works:

```bash
$D4J_HOME/framework/bin/defects4j info -p Lang -b 1
```

---

## 2. Scripts Overview

All scripts live in `scripts/`:

* **`run_one_project_both_final.py`**
  Runs **MAJOR** and **PIT** for a given Defects4J project (and set of bugs)
  on the **fixed** revision, with support for parallelism and memory tuning.
  Produces `mutants.log`, `kill.csv` and per-bug summary CSVs.

* **`export_dev_patches.py`**
  Exports **developer patches** as unified diffs (`diff -ruN`) between
  buggy and fixed revisions for each bug.

* **`summarize_mutation_by_project.py`**
  Scans the mutation logs and builds **CSV summaries**:

  * per-project mutation statistics
  * per-bug mutation statistics

* **`compute_patches.py`**
  Reads `kill.csv` and `mutants.log` for each bug and computes:

  * number of mutants
  * number of *plausible* mutants (status = `LIVE`)
  * aggregate per-project counts
  * per-operator plausible usage counts

* **`evaluate_patches.py`**
  Helper script for further analysis/evaluation of patches
  (for example, comparing generated patches against developer patches).
  Run with `-h` to see its current options.

---

## 3. Typical Workflow

### Step 1 – Export developer patches

This uses Defects4J checkouts (buggy vs fixed) and writes `.diff` files.

```bash
cd scripts

# List available Defects4J projects detected under $D4J_HOME/framework/projects
python3 export_dev_patches.py --list

# Export all diffs for one or more projects
python3 export_dev_patches.py Lang
python3 export_dev_patches.py Lang Mockito --force  # overwrite existing diffs
```

Output (example):

```text
$EXPERIMENT_ROOT/results/dev_patches/Lang/Lang-1.diff
$EXPERIMENT_ROOT/results/dev_patches/Lang/Lang-2.diff
...
```

---

### Step 2 – Run MAJOR + PIT on a project

This script checks out the **fixed** revision of each bug, compiles it,
and then runs both mutation engines.

```bash
cd scripts

# Run on all bugs of a project
python3 run_one_project_both_final.py Lang --jobs 4 --threads 8 --forks 2 --jvm-xmx 8g

# Run on a single bug
python3 run_one_project_both_final.py Lang 2 --threads 6 --forks 2

# Run on a selected subset of bugs
python3 run_one_project_both_final.py Lang --bugs 1,5,9,12
```

Key options (from the script):

* `project` (positional) – Defects4J project name (e.g., `Lang`, `Math`)
* `bug_id` (optional positional) – single bug id
* `--list-bugs` – print all active Defects4J bug IDs for that project
* `--bugs` – comma-separated list of bug IDs
* `--jobs` – number of bugs to run in parallel (process-level)
* `--threads` – PIT worker threads
* `--forks` – PIT fork count
* `--jvm-xmx` – heap size for Java processes (e.g., `8g`)

Outputs for each bug go under:

```text
$EXPERIMENT_ROOT/logs/<Project>-<Bug>/
  ├── mutants.log
  ├── kill.csv
  ├── major_summary.csv
  └── pit_summary.csv
```

---

### Step 3 – Summarise mutation results

Once the mutation runs have completed, summarise across bugs/projects:

```bash
cd scripts

# Basic usage: log root typically $EXPERIMENT_ROOT/logs
python3 summarize_mutation_by_project.py $EXPERIMENT_ROOT/logs --outdir $EXPERIMENT_ROOT/results
```

This writes CSVs such as:

* `mutation_summary_by_project.csv`
* `mutation_summary_by_bug.csv`

containing, for each engine:

* project, bug
* total mutants
* killed, survived
* kill rate

---

### Step 4 – Compute plausible mutants per operator

This script looks at `kill.csv` (`LIVE` status) and `mutants.log`
(operator encoded per mutant ID).

```bash
cd scripts

# Process a single logs root
python3 compute_patches.py --logs-root $EXPERIMENT_ROOT/logs

# Or process all logs_* directories under the current folder
python3 compute_patches.py --all-projects
```

Outputs (per project) under `results/<Project>/`, for example:

* `per_bug_summary.csv` – mutants & plausible counts per bug
* `per_project_summary.csv` – aggregated per-project numbers
* `operator_usage.csv` – **operator → plausible mutant count**

These files were used for the operator-level RQ analysis in the paper.

---

### Step 5 – Evaluate patches (optional / custom analysis)

The `evaluate_patches.py` script is meant for follow-up analysis, e.g.:

* comparing generated patches with developer patches
* filtering by plausibility / correctness
* exporting additional tables for the paper

Run:

```bash
cd scripts
python3 evaluate_patches.py -h
```

to see the available options in your current version.

---

## 4. Reproducing the Paper’s Main Numbers (High-Level)

1. Configure Java + Defects4J and set environment variables.
2. Export developer diffs:
   `python3 export_dev_patches.py <Project>`
3. Run mutation analysis:
   `python3 run_one_project_both_final.py <Project> --jobs N`
4. Summarise mutation results:
   `python3 summarize_mutation_by_project.py $EXPERIMENT_ROOT/logs`
5. Compute plausible mutants and operator usage:
   `python3 compute_patches.py --logs-root $EXPERIMENT_ROOT/logs`
6. (Optional) Use `evaluate_patches.py` to replicate specific tables/figures.

---

🧩 5. Repository Structure
Mutation/
│
├── scripts/
│   ├── run_one_project_both_final.py     # Run MAJOR + PIT mutation analysis
│   ├── export_dev_patches.py             # Export developer patches (diffs)
│   ├── summarize_mutation_by_project.py  # Summaries of mutation results
│   ├── compute_patches.py                # Operator-level plausible usage & per-bug stats
│   ├── evaluate_patches.py               # Optional: evaluate or compare patches
│   └── README.md                          # (This file)
│
├── logs/                                  # Mutation engine outputs (created automatically)
│   ├── Lang-1/
│   │   ├── mutants.log
│   │   ├── kill.csv
│   │   ├── major_summary.csv
│   │   └── pit_summary.csv
│   └── <Project>-<Bug>/ ...
│
├── results/                               # Aggregated experiment results
│   ├── mutation_summary_by_project.csv
│   ├── mutation_summary_by_bug.csv
│   ├── <Project>/                         # Per-project summaries
│   │   ├── per_bug_summary.csv
│   │   ├── per_project_summary.csv
│   │   └── operator_usage.csv
│   └── dev_patches/
│       ├── Lang/Lang-1.diff
│       ├── Lang/Lang-2.diff
│       └── ...
│
├── d4j_work/                              # Temporary Defects4J checkout dirs
│   ├── Lang-1-fixed/
│   ├── Lang-1-buggy/
│   └── ...
│
└── (optional) d4j_work_diff/              # Used by export_dev_patches.py

