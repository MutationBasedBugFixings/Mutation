COST-AWARE MUTANT-OPERATOR SELECTION
============================================

Primary proxy: exponential tier costs 
(Low=1, Moderate=2, High=4, Extremely High=8).
Linear and steep mappings are included as sensitivity checks.

Interpretation:
- frequency: current baseline
- frequency_per_cost: cost-aware scheduling
- exact_cost_aware: selective invocation under a cost budget
- cheap_first: tests whether simple operators alone are sufficient
- random: no-ranking baseline

IMPORTANT LIMITATION:
The default tier costs are structural proxies, not measured runtime.
Runtime claims require operator-level timing or candidate-count data.
Supply operator_runtime_costs.csv to evaluate measured costs.

PRIMARY-SCHEME SUMMARY
--------------------------------------------
  language  budget_fraction           strategy  coverage_percent  mean_selected_count  mean_selected_cost
      Java             0.10        cheap_first             11.06                 7.00                7.00
      Java             0.10   exact_cost_aware             18.17                 3.20                7.00
      Java             0.10          frequency             20.85                 3.00                7.00
      Java             0.10 frequency_per_cost             20.85                 3.00                7.00
      Java             0.10             random              5.01                 4.38                7.00
      Java             0.20        cheap_first             12.80                14.00               14.00
      Java             0.20   exact_cost_aware             41.86                 4.00               15.00
      Java             0.20          frequency             41.86                 4.00               15.00
      Java             0.20 frequency_per_cost             33.18                 8.80               15.00
      Java             0.20             random             10.94                 7.47               15.00
      Java             0.30        cheap_first             23.06                18.00               22.00
      Java             0.30   exact_cost_aware             58.61                 9.40               23.00
      Java             0.30          frequency             46.29                 5.80               23.00
      Java             0.30 frequency_per_cost             57.66                 9.80               23.00
      Java             0.30             random             17.55                10.71               23.00
      Java             0.40        cheap_first             27.80                22.00               30.00
      Java             0.40   exact_cost_aware             65.09                13.00               31.00
      Java             0.40          frequency             64.61                10.00               31.00
      Java             0.40 frequency_per_cost             64.61                13.40               31.00
      Java             0.40             random             25.48                14.10               31.00
      Java             0.50        cheap_first             30.49                26.00               38.00
      Java             0.50   exact_cost_aware             69.19                16.40               39.00
      Java             0.50          frequency             69.35                11.00               39.00
      Java             0.50 frequency_per_cost             67.93                15.60               39.00
      Java             0.50             random             34.00                17.30               39.00
JavaScript             0.10        cheap_first             14.84                 7.00                7.00
JavaScript             0.10   exact_cost_aware             18.75                 6.00                7.00
JavaScript             0.10          frequency             14.84                 3.00                7.00
JavaScript             0.10 frequency_per_cost             18.75                 4.00                7.00
JavaScript             0.10             random              7.08                 4.35                7.00
JavaScript             0.20        cheap_first             23.44                14.00               14.00
JavaScript             0.20   exact_cost_aware             34.38                 9.20               15.00
JavaScript             0.20          frequency             28.91                 4.00               15.00
JavaScript             0.20 frequency_per_cost             33.59                 9.60               15.00
JavaScript             0.20             random             13.94                 7.48               15.00
JavaScript             0.30        cheap_first             33.59                18.00               22.00
JavaScript             0.30   exact_cost_aware             38.28                10.60               23.00
JavaScript             0.30          frequency             30.47                 5.00               23.00
JavaScript             0.30 frequency_per_cost             47.66                10.60               23.00
JavaScript             0.30             random             21.89                10.70               23.00
JavaScript             0.40        cheap_first             33.59                22.00               30.00
JavaScript             0.40   exact_cost_aware             42.19                11.60               31.00
JavaScript             0.40          frequency             51.56                 9.20               31.00
JavaScript             0.40 frequency_per_cost             49.22                11.60               31.00
JavaScript             0.40             random             30.67                14.08               31.00
JavaScript             0.50        cheap_first             35.16                26.00               38.00
JavaScript             0.50   exact_cost_aware             60.16                13.80               38.20
JavaScript             0.50          frequency             69.53                10.20               39.00
JavaScript             0.50 frequency_per_cost             64.84                15.80               39.00
JavaScript             0.50             random             39.80                17.39               39.00
    Python             0.10        cheap_first              2.58                 7.00                7.00
    Python             0.10   exact_cost_aware             27.84                 3.00                7.00
    Python             0.10          frequency             27.84                 3.00                7.00
    Python             0.10 frequency_per_cost             27.84                 3.00                7.00
    Python             0.10             random              4.71                 4.39                7.00
    Python             0.20        cheap_first              3.09                14.00               14.00
    Python             0.20   exact_cost_aware             40.21                 4.80               15.00
    Python             0.20          frequency             44.33                 4.00               15.00
    Python             0.20 frequency_per_cost             43.30                 8.00               15.00
    Python             0.20             random             10.89                 7.48               15.00
    Python             0.30        cheap_first             21.13                18.00               22.00
    Python             0.30   exact_cost_aware             66.49                 9.00               23.00
    Python             0.30          frequency             54.64                 5.60               23.00
    Python             0.30 frequency_per_cost             66.49                 9.00               23.00
    Python             0.30             random             18.59                10.77               23.00
    Python             0.40        cheap_first             24.23                22.00               30.00
    Python             0.40   exact_cost_aware             80.41                10.20               31.00
    Python             0.40          frequency             75.26                 9.40               31.00
    Python             0.40 frequency_per_cost             74.74                10.60               31.00
    Python             0.40             random             26.76                14.09               31.00
    Python             0.50        cheap_first             24.23                26.00               38.00
    Python             0.50   exact_cost_aware             87.11                14.00               39.00
    Python             0.50          frequency             79.38                10.40               39.00
    Python             0.50 frequency_per_cost             87.11                13.80               39.00
    Python             0.50             random             36.53                17.31               39.00

PAIRED BOOTSTRAP COMPARISONS
--------------------------------------------
  language cost_scheme  budget_fraction         strategy_a         strategy_b  paired_bugs  difference_percentage_points  ci_95_low  ci_95_high
      Java exponential             0.10   exact_cost_aware          frequency          633                         -2.69      -4.27       -1.11
      Java exponential             0.10   exact_cost_aware frequency_per_cost          633                         -2.69      -4.27       -1.11
      Java exponential             0.10          frequency        cheap_first          633                          9.79       6.00       13.59
      Java exponential             0.10 frequency_per_cost          frequency          633                          0.00       0.00        0.00
      Java exponential             0.20   exact_cost_aware          frequency          633                          0.00       0.00        0.00
      Java exponential             0.20   exact_cost_aware frequency_per_cost          633                          8.69       4.26       12.95
      Java exponential             0.20          frequency        cheap_first          633                         29.07      24.33       33.65
      Java exponential             0.20 frequency_per_cost          frequency          633                         -8.69     -12.95       -4.26
      Java exponential             0.30   exact_cost_aware          frequency          633                         12.32       9.32       15.48
      Java exponential             0.30   exact_cost_aware frequency_per_cost          633                          0.95      -0.63        2.53
      Java exponential             0.30          frequency        cheap_first          633                         23.22      18.01       28.12
      Java exponential             0.30 frequency_per_cost          frequency          633                         11.37       8.37       14.38
      Java exponential             0.40   exact_cost_aware          frequency          633                          0.47      -2.05        3.00
      Java exponential             0.40   exact_cost_aware frequency_per_cost          633                          0.47      -0.79        1.74
      Java exponential             0.40          frequency        cheap_first          633                         36.81      31.60       41.86
      Java exponential             0.40 frequency_per_cost          frequency          633                          0.00      -2.53        2.53
      Java exponential             0.50   exact_cost_aware          frequency          633                         -0.16      -3.48        3.32
      Java exponential             0.50   exact_cost_aware frequency_per_cost          633                          1.26      -0.63        3.32
      Java exponential             0.50          frequency        cheap_first          633                         38.86      33.33       44.23
      Java exponential             0.50 frequency_per_cost          frequency          633                         -1.42      -4.42        1.74
JavaScript exponential             0.10   exact_cost_aware          frequency          128                          3.91      -3.91       11.72
JavaScript exponential             0.10   exact_cost_aware frequency_per_cost          128                          0.00      -3.12        3.12
JavaScript exponential             0.10          frequency        cheap_first          128                          0.00      -9.38        8.59
JavaScript exponential             0.10 frequency_per_cost          frequency          128                          3.91      -3.12       10.94
JavaScript exponential             0.20   exact_cost_aware          frequency          128                          5.47      -4.69       15.62
JavaScript exponential             0.20   exact_cost_aware frequency_per_cost          128                          0.78      -1.56        3.12
JavaScript exponential             0.20          frequency        cheap_first          128                          5.47      -7.03       17.97
JavaScript exponential             0.20 frequency_per_cost          frequency          128                          4.69      -4.69       14.84
JavaScript exponential             0.30   exact_cost_aware          frequency          128                          7.81       0.78       14.84
JavaScript exponential             0.30   exact_cost_aware frequency_per_cost          128                         -9.38     -15.62       -3.12
JavaScript exponential             0.30          frequency        cheap_first          128                         -3.12     -15.62        9.38
JavaScript exponential             0.30 frequency_per_cost          frequency          128                         17.19      10.16       24.24
JavaScript exponential             0.40   exact_cost_aware          frequency          128                         -9.38     -16.41       -3.12
JavaScript exponential             0.40   exact_cost_aware frequency_per_cost          128                         -7.03     -13.28       -1.56
JavaScript exponential             0.40          frequency        cheap_first          128                         17.97       6.25       29.69
JavaScript exponential             0.40 frequency_per_cost          frequency          128                         -2.34      -6.25        0.78
JavaScript exponential             0.50   exact_cost_aware          frequency          128                         -9.38     -17.97       -0.78
JavaScript exponential             0.50   exact_cost_aware frequency_per_cost          128                         -4.69      -8.59       -1.56
JavaScript exponential             0.50          frequency        cheap_first          128                         34.38      21.09       46.88
JavaScript exponential             0.50 frequency_per_cost          frequency          128                         -4.69     -14.06        4.69
    Python exponential             0.10   exact_cost_aware          frequency          194                          0.00       0.00        0.00
    Python exponential             0.10   exact_cost_aware frequency_per_cost          194                          0.00       0.00        0.00
    Python exponential             0.10          frequency        cheap_first          194                         25.26      19.07       31.96
    Python exponential             0.10 frequency_per_cost          frequency          194                          0.00       0.00        0.00
    Python exponential             0.20   exact_cost_aware          frequency          194                         -4.12      -7.73       -0.52
    Python exponential             0.20   exact_cost_aware frequency_per_cost          194                         -3.09     -10.31        4.12
    Python exponential             0.20          frequency        cheap_first          194                         41.24      33.51       48.97
    Python exponential             0.20 frequency_per_cost          frequency          194                         -1.03      -9.28        7.22
    Python exponential             0.30   exact_cost_aware          frequency          194                         11.86       5.15       18.57
    Python exponential             0.30   exact_cost_aware frequency_per_cost          194                          0.00       0.00        0.00
    Python exponential             0.30          frequency        cheap_first          194                         33.51      24.23       42.78
    Python exponential             0.30 frequency_per_cost          frequency          194                         11.86       5.15       18.57
    Python exponential             0.40   exact_cost_aware          frequency          194                          5.15       1.55        8.76
    Python exponential             0.40   exact_cost_aware frequency_per_cost          194                          5.67       2.06        9.79
    Python exponential             0.40          frequency        cheap_first          194                         51.03      42.27       59.79
    Python exponential             0.40 frequency_per_cost          frequency          194                         -0.52      -5.15        4.12
    Python exponential             0.50   exact_cost_aware          frequency          194                          7.73       2.06       13.40
    Python exponential             0.50   exact_cost_aware frequency_per_cost          194                          0.00      -2.06        2.06
    Python exponential             0.50          frequency        cheap_first          194                         55.15      45.88       63.92
    Python exponential             0.50 frequency_per_cost          frequency          194                          7.73       2.06       13.40