# RQ5 Replication Package

This directory contains the data, result tables, figures, and audit artifacts for RQ5 of **An Empirical Study of Mutant Operators for Injecting and Fixing Real-World Defects**.

> **Scope.** RQ5 measures complete-fix structural representability from annotated bug-to-operator mappings. It does not execute an APR system, generate executable patches, establish semantic correctness, measure test-suite adequacy, or report repair runtime.

## 1. Final mapping cohort

The canonical mapping file is `data/strict_bug_operator_mappings.csv`.

| Language | Original annotation records | Eligible mappings |
|---|---:|---:|
| Java (Defects4J) | 835 | 633 |
| Python (BugsInPy) | 300 | 194 |
| JavaScript (BugsJS) | 219 | 128 |
| **Total** | **1,354** | **955** |

The canonical file contains 955 unique `mapping_id` values. Its key identity is language–project–bug. The `operators` field stores semicolon-separated canonical operator-family codes; `operator_set` is the parsed representation retained by the cleaning pipeline.

A mapping is eligible when it is operator-representable, has at least one canonical operator family, and has no unresolved labels. Coverage is conditional on these annotated operator sets.

## 2. Complete-fix coverage

For a selected operator set `S`, a bug fix is covered only if every operator family annotated for that fix is contained in `S`:

`Coverage(S, B) = |{b in B : R_b is a subset of S}| / |B|`.

This is a structural representability measure, not a measure of executable patch generation or successful automated repair.

## 3. Analyses and reported outputs

### 3.1 Fixed operator-count evaluation

The source-level evaluation compares:
- **Frequency-based:** ranks operators by the number of training fixes containing each operator.
- **Composition-aware:** selects a size-k operator set maximizing complete-fix coverage on training fixes; frequency is a secondary tie-breaker.
- **Random/no-ranking:** mean held-out coverage over 1,000 uniformly sampled size-k operator sets.

Budgets: `k = 1, 3, 5, 10`.

For within-language evaluation, each language uses five project-grouped folds. Four folds train the operator portfolio and the remaining fold is held out. Held-out coverage is pooled across folds. The fold-assignment CSVs in `audit/` were reconstructed from the saved 955-mapping input using the same `GroupKFold` grouping configuration; they are not original archived train/test-index logs.

Results:
- `results/source_level/within_language_project_cv_summary.csv`
- `results/source_level/within_language_project_cv_folds.csv`
- `results/source_level/selected_portfolios_within_language.csv`
- `results/source_level/cross_language_transfer.csv`

Cross-language portfolios are trained on the full source-language cohort and transferred unchanged to the target language. These results are not directly equivalent to within-language project-held-out estimates.

### 3.2 Cost-aware selection

The cost-aware analysis compares five strategies:
- Frequency
- Frequency-per-cost
- Exact cost-aware
- Cheap-first
- Random

The proxy-cost schemes are:
| Scheme | Low | Moderate | High | Extremely High |
|---|---:|---:|---:|---:|
| Linear | 1 | 2 | 3 | 4 |
| Exponential (primary) | 1 | 2 | 4 | 8 |
| Steep | 1 | 3 | 6 | 10 |

Budgets: 10%, 20%, 30%, 40%, and 50% of the total proxy cost of the operator vocabulary. The cost values are structural proxies derived from RQ3 complexity tiers, not measured runtime, candidate counts, or validation costs.

Archived outputs:
- `results/cost_aware/primary_scheme_summary.csv`
- `results/cost_aware/heldout_summary.csv`
- `results/cost_aware/selected_portfolios.csv`
- `results/cost_aware/paired_comparisons.csv`
- `results/cost_aware/README_RESULTS.txt`
- `results/cost_aware/coverage_java.svg`
- `results/cost_aware/coverage_python.svg`
- `results/cost_aware/coverage_javascript.svg`

The archived `paired_comparisons.csv` contains 180 rows: 3 cost schemes × 5 budgets × 3 languages × 4 pairwise comparisons. Each pairwise comparison therefore has 45 language–budget–scheme records.

**Bootstrap interval counts (verified against the latest evidence archive):** The paired-comparison CSV from `rq5_evidence_to_share.zip` was used because its counts match the user's latest server-side terminal output. It contains 180 rows, with 45 records per comparison. Applying the rule—positive if `ci_95_low > 0`, negative if `ci_95_high < 0`, and otherwise includes zero—gives:

| Comparison | Positive | Negative | Includes zero |
|---|---:|---:|---:|
| Frequency-per-cost minus Frequency | 13 | 6 | 26 |
| Exact cost-aware minus Frequency | 13 | 9 | 23 |
| Frequency minus Cheap-first | 35 | 2 | 8 |

The manuscript has been corrected from `13, 8, 24` to `13, 9, 23` for exact cost-aware minus frequency. The earlier `RQ5_FINAL_955_RESULTS.zip` contained a different/stale paired-comparison CSV (13/8/24); it has been superseded in this release by the CSV matching the latest evidence archive and server output. The intervals resample bugs rather than project clusters and are not adjusted for multiple comparisons; inferential comparisons should therefore be treated as exploratory.

### 3.3 Cross-language transfer

See `results/source_level/cross_language_transfer.csv`. The source-language portfolio is transferred unchanged to each target language. Reported values should be regenerated from this CSV, not manually retyped.

### 3.4 PraPR supplementary comparison

See `results/prapr/prapr_supplementary_comparison.csv` and `results/prapr/prapr_mapped_ranking.csv`.

This is a taxonomy-mapped comparison of published bytecode-level mutator priorities against the source-level operator-family taxonomy on the 633 Java mappings. It is **not** a run or reproduction of PraPR's APR pipeline and should be described as a supplementary cross-abstraction/transfer-utility comparison, not a direct like-for-like baseline.

## 4. Audit artifacts

- `results/source_level/cleaning_audit_all_rows.csv`: source-record cleaning/eligibility audit.
- `results/source_level/rows_requiring_manual_review.csv`: records flagged for manual review; inspect its row count and contents when reproducing.
- `results/source_level/dataset_count_audit.csv`: per-language original and eligible counts.
- `results/source_level/project_fold_audit.csv`: project-level cohort counts.
- `audit/project_fold_assignments_reconstructed.csv`: one row per language/project with reconstructed fold and held-out bug count.
- `audit/bug_level_fold_assignments_reconstructed.csv`: one row per eligible mapping with reconstructed fold.
- `audit/bootstrap_interval_counts_from_archived_csv.csv`: interval sign counts derived from the archived paired-comparison output.

The reconstructed fold files are derived from the canonical mapping CSV and the `GroupKFold` configuration. They document the deterministic allocation produced by that reconstruction, but do not replace saved historical split indices if those are available.

## 5. Reproduction environment

The experiment scripts used in the research workspace are:
- `rq5_source_level_portfolio_analysis_corrected.py`
- `cost_aware_operator_selection.py`
- `complexity_popularity.py`
- `prapr_comparison/run_prapr_comparison.py`

**Important release note:** The present archive includes the final data and result artifacts, but does not include these executable source scripts because their exact release copies were not available in the supplied ZIP/CSV materials at package assembly time. Add the exact, reviewed scripts to `scripts/` before describing this as a fully executable, self-contained replication package. Do not substitute older script variants.

Expected Python dependencies, based on the experiment implementation and repository documentation, include Python 3.10+, pandas, NumPy, SciPy (including `scipy.optimize.milp` for the exact cost-aware optimization), scikit-learn, and Matplotlib. Record the exact Python and package versions used for the archived run in the final release.

Once the exact scripts are added, the intended commands from this directory are:

```bash
python scripts/rq5_source_level_portfolio_analysis_corrected.py
python scripts/cost_aware_operator_selection.py
python scripts/complexity_popularity.py
python scripts/prapr_comparison/run_prapr_comparison.py
```

Before executing, verify the scripts use paths relative to `Path(__file__).resolve().parent` and write outputs within this package. Running the scripts may overwrite result files; preserve a backup of the archived outputs first.

## 6. Suggested release structure

```text
RQ5/
├── README.md
├── data/
│   ├── strict_bug_operator_mappings.csv
│   ├── Defects4j_full.xlsx
│   ├── BugInPy.xlsx
│   ├── bugjs_manual.csv
│   └── prapr_mapped_ranking.csv
├── scripts/                  # Add exact reviewed source scripts
├── results/
│   ├── source_level/
│   ├── cost_aware/
│   └── prapr/
└── audit/
    ├── project_fold_assignments_reconstructed.csv
    ├── bug_level_fold_assignments_reconstructed.csv
    └── bootstrap_interval_counts_from_archived_csv.csv
```

## 7. Release checklist

- [x] Canonical cohort has 955 unique mappings (633 Java, 194 Python, 128 JavaScript).
- [x] Within-language, cross-language, cost-aware, and PraPR result tables included.
- [x] Cost-aware SVG figures included.
- [x] Fold assignments reconstructed and included as explicitly labelled derived audit files.
- [ ] Add the exact final experiment scripts; do not use older variants.
- [x] Reconcile bootstrap interval counts against the archived paired-comparison CSV; manuscript corrected to 13/9/23 for exact cost-aware minus frequency.
- [ ] Record exact dependency versions and solver details.
- [ ] Verify all paths are repository-relative and test reproduction from a clean clone.
- [ ] Tag/version the final release after the above checks.

## Citation and scope

Please cite the associated paper when using this package. This package documents the RQ5 source-level operator-selection analyses and supplementary PraPR mapping. It does not claim to reproduce PraPR itself.
