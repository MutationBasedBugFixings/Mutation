Which supplied files should be included?

Include

rq5_source_level_operator_sets_fixed.py in the main RQ5 replication folder, because this is the corrected script that reproduces the strict counts 619/178/128. Rename it to a clean name such as run_rq5_source_level_analysis.py before publishing.

prapr_supplementary_comparison.csv, because it contains the manuscript values 54, 76, 180, and 333.

The corrected 619-row Java subset from rq5_results/strict_bug_operator_mappings.csv. This package includes that subset as data/strict_java_bug_operator_mappings.csv.

prapr_mapped_ranking.csv and prapr_mapping_audit.csv, but use the cleaned and expanded versions provided in this package.

Do not include as final evidence

The following uploaded copies came from an older run and should not be published as final RQ5 results:

dataset_count_audit(1).csv — reports Python = 187 instead of 178.

strict_bug_operator_mappings(1).csv — contains Python = 187 and duplicate Java mapping identifiers.

cleaning_audit_all_rows(1).csv

rows_requiring_manual_review(1).csv

within_language_project_cv_folds(1).csv

within_language_project_cv_summary(1).csv

selected_portfolios_within_language(1).csv

cross_language_transfer(3).csv

rq5_source_level_portfolio_analysis(1).py

rq5_source_level_portfolio_analysis(1)(1).py

rq5_source_level_portfolio_analysis_fixed(1).py — despite its name, it only changes paths and retains the old parsing logic.

Replace those files with outputs generated on the server by rq5_source_level_operator_sets_fixed.py, where the dataset audit is exactly:

Java: 619

Python: 178

JavaScript: 128

Unknown project rows: 0
