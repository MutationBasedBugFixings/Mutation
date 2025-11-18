---

# **README.md**

# Mutation-Based Bug Fixing & Bug Injection

*A Unified Experimental Infrastructure for Defects4J Mutation Analysis*

This repository contains the full experimental pipeline used in the paper:


It provides **fully automated tools** to:

* run **MAJOR** and **PIT** mutation engines on **Defects4J** projects
* extract **developer patches** (diffs)
* compute **operator–patch mappings**
* aggregate **mutation results (per-bug and per-project)**
* perform **APR patch extraction & summarization**
* compute **plausible vs correct mutant patches**
* support **RQ1–RQ4** of the paper with reproducible data

The infrastructure has been tested on **15 Defects4J projects**, **771 bugs**, and produced over **700K mutants**.

---

# 🧩 **1. Repository Structure**

```
Mutation/
│
├── scripts/
│   ├── run_one_project_both.py          # MAJOR + PIT execution
│   ├── export_dev_patches_all.py        # export developer patches (diffs)
│   ├── scan_mutation_logs.py            # summary of mutants (project/bug)
│   ├── operator_usage_parser.py         # compute operator-level plausible usage
│   ├── apr_scan_combined.py             # combine APR + mutation summaries
│   └── utils/                           # shared helpers
│
├── logs/                                # mutation engine outputs
│   ├── Lang-1/
│   │   ├── mutants.log
│   │   ├── kill.csv
│   │   ├── major_summary.csv
│   │   └── pit_summary.csv
│   └── ...
│
├── results/
│   ├── mutation_summary_by_project.csv
│   ├── mutation_summary_by_bug.csv
│   ├── apr_summary_by_project.csv
│   ├── supervisor_table.csv
│   └── dev_patches/
│       ├── Lang/Lang-1.diff
│       └── ...
│
├── d4j_work/ / d4j_work_mockito/        # temporary checkouts
└── README.md
```

---

# ⚙️ **2. Environment Setup**

### **Requirements**

* Ubuntu 20.04 / 22.04 (recommended)
* Python ≥ 3.8
* Java 8 (for MAJOR compiler)
* Java 11 (for Defects4J + PIT)
* Defects4J ≥ 2.0.0
* MAJOR (included in D4J mutation wrapper)
* Maven + Ant available on PATH

### **Environment Variables**

Set these in your `~/.bashrc` or `env_java.sh`:

```bash
export D4J_HOME=/home1/yourname/tools_and_libs/defects4j
export EXPERIMENT_ROOT=/home1/yourname/my_mutation_experiments

export JAVA11_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export JAVA8_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export MAJOR_JAVA_HOME=$JAVA8_HOME
```

Confirm environment:

```bash
java -version
$D4J_HOME/framework/bin/defects4j info -p Lang -b 1
```

---

# 🚀 **3. Running Mutations (MAJOR + PIT)**

The main pipeline script is:

```
scripts/run_one_project_both_final.py
```

### **Run on a single project**

```bash
python3 scripts/run_one_project_both_final.py Lang --jobs 4 --threads 8 --forks 2 --jvm-xmx 8g
```

### **Run on a specific bug**

```bash
python3 scripts/run_one_project_both_final.py Lang 2 --threads 6 --forks 2
```

### **Run on selected bugs**

```bash
python3 scripts/run_one_project_both_final.py Lang --bugs 1,5,9,12
```

### **Features**

* Automatic JDK switching
* JDK8 compilation for MAJOR
* JDK11 runtime for PIT
* Skips bugs already processed
* Parallel bug execution (`--jobs`)
* Multi-threaded PIT execution (`--threads`, `--forks`)
* Writes:

  * `mutants.log`
  * `kill.csv`
  * `major_summary.csv`
  * `pit_summary.csv`

All results saved under:

```
logs/<Project>-<Bug>/
```

---

# 📝 **4. Exporting Developer Patches (Diffs)**

Script:

```
scripts/export_dev_patches_all.py
```

### **List available projects**

```bash
python3 scripts/export_dev_patches_all.py --list
```

### **Export diffs for a project**

```bash
python3 scripts/export_dev_patches_all.py Lang
```

Diffs stored in:

```
results/dev_patches/<Project>/<Project>-<Bug>.diff
```

---

# 📊 **5. Summarizing Mutation Results**

Script:

```
scripts/summarize_mutation_by_project.py
```

### **Compute per-project and per-bug summaries**

```bash
python3 scripts/run_one_project_both_final.py logs/
```

Outputs written to:

```
results/mutation_summary_by_project.csv
results/mutation_summary_by_bug.csv
```

Each row includes:

* mutants_total
* killed
* survived
* kill_rate
* engine (MAJOR or PIT)

---

# 🧪 **6. Operator-Level Plausible Patch Statistics**

Script:

```
scripts/operator_usage_parser.py
```

### **Compute operator-level usage (RQ4)**

```bash
python3 scripts/operator_usage_parser.py --logs-root logs/
```

Outputs:

```
results/<Project>/operator_usage.csv
```

This file maps:

```
Operator → Count of plausible (LIVE) mutants
```

Used in the paper’s RQ4 analysis.

---

Used for combining:

* mutation stats
* APR generated patches
* plausible/correct APR patches

### Example:

```bash
python3 scripts/apr_scan_combined.py logs/ --apr-root apr_results/ --gen-pattern "*.patch"
```

Outputs:

```
mutation_table.csv
apr_summary_by_project.csv
```

Used to compare APR vs mutation-based patch generation.

---

# 📦 **8. Reproducing Experiments (TOSEM Artifact Guide)**

To fully reproduce the paper:

### **Step 1 — Prepare environment**

Install JDK8, JDK11, Defects4J, Ant, Maven.

### **Step 2 — Run mutation pipeline**

```bash
python3 scripts/run_one_project_both.py <Project> --jobs 4
```

### **Step 3 — Export developer diffs**

```bash
python3 scripts/export_dev_patches_all.py <Project>
```

### **Step 4 — Generate mutation summaries**

```bash
python3 scripts/evaluate_patches.py logs/
```

### **Step 5 — Operator-level analysis**

```bash
python3 scripts/summarize_mutation_by_projects.py --logs-root logs/
```

### **Step 6 — APR + mutation merge**

```bash
python3 scripts/compute_patches.py logs/ --apr-root apr/
```

### **Step 7 — Use CSVs for RQ1–RQ4**

* mutation_summary_by_project.csv
* mutation_summary_by_bug.csv
* operator_usage.csv
* dev_patches/*.diff
* mutant_table.csv

---

# 🧪 **9. Tested Projects (Defects4J v2.0.x)**

| Project         | Bugs |
| --------------- | ---- |
| Cli             | 39   |
| Closure         | 174  |
| Codec           | 18   |
| Collections     | 28   |
| Compress        | 47   |
| Csv             | 7    |
| Gson            | 18   |
| JacksonCore     | 26   |
| JacksonDatabind | 112  |
| JacksonXml      | 6    |
| JxPath          | 22   |
| Jsoup           | 93   |
| Lang            | 65   |
| Math            | 106  |
| Time            | 27   |


Total: **771 bugs**





