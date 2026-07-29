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
      Java             0.10        cheap_first             10.18                 7.00                7.00
      Java             0.10   exact_cost_aware             19.71                 3.00                7.00
      Java             0.10          frequency             21.81                 3.00                7.00
      Java             0.10 frequency_per_cost             21.81                 3.00                7.00
      Java             0.10             random              4.88                 4.38                7.00
      Java             0.20        cheap_first             11.79                14.00               14.00
      Java             0.20   exact_cost_aware             43.46                 4.00               15.00
      Java             0.20          frequency             43.46                 4.00               15.00
      Java             0.20 frequency_per_cost             33.28                 8.40               15.00
      Java             0.20             random             10.68                 7.47               15.00
      Java             0.30        cheap_first             22.29                18.00               22.00
      Java             0.30   exact_cost_aware             59.45                 9.20               23.00
      Java             0.30          frequency             48.79                 5.80               23.00
      Java             0.30 frequency_per_cost             58.97                 9.40               23.00
      Java             0.30             random             17.09                10.71               23.00
      Java             0.40        cheap_first             25.36                22.00               30.00
      Java             0.40   exact_cost_aware             65.59                13.00               31.00
      Java             0.40          frequency             65.75                10.00               31.00
      Java             0.40 frequency_per_cost             65.59                13.80               31.00
      Java             0.40             random             24.94                14.10               31.00
      Java             0.50        cheap_first             28.59                26.00               38.00
      Java             0.50   exact_cost_aware             70.76                16.40               39.00
      Java             0.50          frequency             69.95                11.40               39.00
      Java             0.50 frequency_per_cost             69.95                15.80               39.00
      Java             0.50             random             33.46                17.30               39.00
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
    Python             0.10        cheap_first              1.69                 7.00                7.00
    Python             0.10   exact_cost_aware             29.78                 3.00                7.00
    Python             0.10          frequency             29.78                 3.00                7.00
    Python             0.10 frequency_per_cost             29.78                 3.00                7.00
    Python             0.10             random              4.83                 4.39                7.00
    Python             0.20        cheap_first              2.25                14.00               14.00
    Python             0.20   exact_cost_aware             42.70                 4.80               15.00
    Python             0.20          frequency             47.75                 4.00               15.00
    Python             0.20 frequency_per_cost             43.82                 8.00               15.00
    Python             0.20             random             11.35                 7.48               15.00
    Python             0.30        cheap_first             19.66                18.00               22.00
    Python             0.30   exact_cost_aware             68.54                 9.00               23.00
    Python             0.30          frequency             61.24                 5.00               23.00
    Python             0.30 frequency_per_cost             69.10                 9.00               23.00
    Python             0.30             random             19.32                10.77               23.00
    Python             0.40        cheap_first             24.16                22.00               30.00
    Python             0.40   exact_cost_aware             84.83                10.00               31.00
    Python             0.40          frequency             77.53                 8.80               31.00
    Python             0.40 frequency_per_cost             84.83                10.00               31.00
    Python             0.40             random             27.64                14.09               31.00
    Python             0.50        cheap_first             24.16                26.00               38.00
    Python             0.50   exact_cost_aware             89.33                14.40               38.80
    Python             0.50          frequency             92.13                13.00               39.00
    Python             0.50 frequency_per_cost             90.45                13.80               39.00
    Python             0.50             random             37.76                17.31               39.00

PAIRED BOOTSTRAP COMPARISONS
--------------------------------------------
  language cost_scheme  budget_fraction         strategy_a         strategy_b  paired_bugs  difference_percentage_points  ci_95_low  ci_95_high
      Java exponential             0.10   exact_cost_aware          frequency          619                         -2.10      -3.55       -0.65
      Java exponential             0.10   exact_cost_aware frequency_per_cost          619                         -2.10      -3.55       -0.65
      Java exponential             0.10          frequency        cheap_first          619                         11.63       8.07       15.35
      Java exponential             0.10 frequency_per_cost          frequency          619                          0.00       0.00        0.00
      Java exponential             0.20   exact_cost_aware          frequency          619                          0.00       0.00        0.00
      Java exponential             0.20   exact_cost_aware frequency_per_cost          619                         10.18       5.65       14.54
      Java exponential             0.20          frequency        cheap_first          619                         31.66      26.97       36.35
      Java exponential             0.20 frequency_per_cost          frequency          619                        -10.18     -14.54       -5.65
      Java exponential             0.30   exact_cost_aware          frequency          619                         10.66       7.59       13.73
      Java exponential             0.30   exact_cost_aware frequency_per_cost          619                          0.48      -0.48        1.45
      Java exponential             0.30          frequency        cheap_first          619                         26.49      21.32       31.18
      Java exponential             0.30 frequency_per_cost          frequency          619                         10.18       7.11       13.25
      Java exponential             0.40   exact_cost_aware          frequency          619                         -0.16      -2.75        2.26
      Java exponential             0.40   exact_cost_aware frequency_per_cost          619                          0.00      -1.13        1.13
      Java exponential             0.40          frequency        cheap_first          619                         40.39      35.38       45.40
      Java exponential             0.40 frequency_per_cost          frequency          619                         -0.16      -2.75        2.42
      Java exponential             0.50   exact_cost_aware          frequency          619                          0.81      -2.26        4.04
      Java exponential             0.50   exact_cost_aware frequency_per_cost          619                          0.81      -0.97        2.58
      Java exponential             0.50          frequency        cheap_first          619                         41.36      36.03       46.53
      Java exponential             0.50 frequency_per_cost          frequency          619                          0.00      -2.75        2.91
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
    Python exponential             0.10   exact_cost_aware          frequency          178                          0.00       0.00        0.00
    Python exponential             0.10   exact_cost_aware frequency_per_cost          178                          0.00       0.00        0.00
    Python exponential             0.10          frequency        cheap_first          178                         28.09      21.35       35.39
    Python exponential             0.10 frequency_per_cost          frequency          178                          0.00       0.00        0.00
    Python exponential             0.20   exact_cost_aware          frequency          178                         -5.06      -8.43       -2.25
    Python exponential             0.20   exact_cost_aware frequency_per_cost          178                         -1.12      -8.99        6.18
    Python exponential             0.20          frequency        cheap_first          178                         45.51      37.64       53.37
    Python exponential             0.20 frequency_per_cost          frequency          178                         -3.93     -12.36        4.49
    Python exponential             0.30   exact_cost_aware          frequency          178                          7.30      -1.12       15.73
    Python exponential             0.30   exact_cost_aware frequency_per_cost          178                         -0.56      -1.69        0.00
    Python exponential             0.30          frequency        cheap_first          178                         41.57      31.46       51.69
    Python exponential             0.30 frequency_per_cost          frequency          178                          7.87      -0.56       16.85
    Python exponential             0.40   exact_cost_aware          frequency          178                          7.30       3.37       11.24
    Python exponential             0.40   exact_cost_aware frequency_per_cost          178                          0.00      -1.69        1.69
    Python exponential             0.40          frequency        cheap_first          178                         53.37      43.82       62.92
    Python exponential             0.40 frequency_per_cost          frequency          178                          7.30       3.37       11.24
    Python exponential             0.50   exact_cost_aware          frequency          178                         -2.81      -6.18        0.56
    Python exponential             0.50   exact_cost_aware frequency_per_cost          178                         -1.12      -3.93        1.69
    Python exponential             0.50          frequency        cheap_first          178                         67.98      60.11       75.28
    Python exponential             0.50 frequency_per_cost          frequency          178                         -1.69      -3.93        0.00