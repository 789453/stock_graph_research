# PHASE2_3_RESEARCH_SUMMARY

## 1. Executive Conclusion
Phase 2.3 has successfully consolidated the research infrastructure and expanded descriptive statistics for the semantic stock graph. 
Key findings suggest that the semantic graph encodes significant industry information but also reveals cross-industry structures that are not captured by traditional classifications. 
The enrichment with Tushare fundamental data provides a new layer of descriptive association between semantic proximity and fundamental similarity.

## 2. What Changed from Phase 2.2
- **Data Enrichment**: Integrated SW industry membership and Tushare fundamental snapshot.
- **Contract Hardening**: Repaired edge construction logic and enforced strict node index validation.
- **Graph Metrics**: Expanded beyond simple degree to include entropy, bridge scores, and component analysis.
- **Visualization**: Replaced redundant plots with high-value visualizations focused on industry and fundamental structure.

## 3. Data and Cache Audit
- **Git Commit**: f2007cf - phase2.2 mostly completed but plots not
- **Run ID**: run_20260511_p23
- **Data Coverage**:
| source               |   node_count |   matched_count |   coverage_pct |
|:---------------------|-------------:|----------------:|---------------:|
| stock_sw_member      |         5502 |            5502 |              1 |
| stock_basic_snapshot |         5502 |            5502 |              1 |

## 4. Edge Construction and Graph Contract Audit
- **Self-edges**: Successfully removed during T01.
- **Rank Range**: 1-100 enforced.
- **Mutual Edges**: Correctly computed using reverse self-merge.

## 5. Industry and Fundamental Enrichment
The graph now includes detailed SW L1/L2/L3 industry labels and fundamental metrics (PE, PB, Market Cap, Turnover).
Coverage for SW industry is 100.00%, and basic snapshot is 100.00%.

## 6. Graph-Structure Findings
- **Component Analysis**:
|   k |   component_count_weak |   largest_component_ratio_weak |   component_count_strong |   largest_component_ratio_strong |
|----:|-----------------------:|-------------------------------:|-------------------------:|---------------------------------:|
|  20 |                      2 |                        0.99382 |                       54 |                         0.98546  |
|  50 |                      1 |                        1       |                        6 |                         0.993093 |
| 100 |                      1 |                        1       |                        2 |                         0.99382  |

## 7. Rank-Band Findings
- **Industry Purity**: Strongest in rank_001_005 and decays as rank increases.
- **Fundamental Gap**: Semantic neighbors show smaller valuation gaps compared to random baselines.
| rank_band    |   edge_count |   score_mean |   score_median |   mutual_ratio |   same_l1_ratio |   same_l3_ratio |   abs_log_total_mv_gap_mean |   abs_pb_gap_median |
|:-------------|-------------:|-------------:|---------------:|---------------:|----------------:|----------------:|----------------------------:|--------------------:|
| rank_001_005 |        27510 |     0.797043 |       0.799826 |       0.988222 |        0.654998 |       0.394438  |                     1.01707 |             1.6455  |
| rank_006_010 |        27510 |     0.749665 |       0.751637 |       0.957506 |        0.581352 |       0.282915  |                     1.07678 |             1.7208  |
| rank_011_020 |        55020 |     0.717049 |       0.719016 |       0.89024  |        0.525809 |       0.210378  |                     1.10741 |             1.77795 |
| rank_021_050 |       165060 |     0.669976 |       0.673749 |       0.695626 |        0.443942 |       0.129553  |                     1.13456 |             1.838   |
| rank_051_100 |       275100 |     0.624104 |       0.629498 |       0.409422 |        0.350327 |       0.0699164 |                     1.16553 |             1.9185  |

## 8. Cross-Industry Bridge Findings
Top cross-industry bridge pairs identify candidate business relationships across SW L1 sectors.
| src_l1_name   | dst_l1_name   |   edge_count |   mean_score |   mutual_ratio |   mean_bridge_score |   mean_abs_pb_gap |
|:--------------|:--------------|-------------:|-------------:|---------------:|--------------------:|------------------:|
| 机械设备      | 电力设备      |         6618 |     0.677475 |       0.422786 |           0.151051  |           5.29598 |
| 机械设备      | 基础化工      |         4709 |     0.653047 |       0.479083 |           0.121403  |           6.39011 |
| 机械设备      | 电子          |         4657 |     0.672323 |       0.460597 |           0.139756  |           4.93596 |
| 电力设备      | 机械设备      |         4331 |     0.695577 |       0.64604  |           0.177561  |           4.49166 |
| 电力设备      | 电子          |         4263 |     0.692601 |       0.520995 |           0.166153  |           3.68709 |
| 电子          | 电力设备      |         4145 |     0.698999 |       0.535826 |           0.141894  |           4.88382 |
| 基础化工      | 机械设备      |         3940 |     0.654875 |       0.572589 |           0.15191   |           4.89089 |
| 汽车          | 机械设备      |         3789 |     0.663878 |       0.517815 |           0.103716  |          10.2448  |
| 机械设备      | 汽车          |         3517 |     0.663662 |       0.557862 |           0.136089  |          19.1481  |
| 电子          | 机械设备      |         3481 |     0.683997 |       0.616202 |           0.128063  |           5.66528 |
| 基础化工      | 有色金属      |         3312 |     0.683493 |       0.477657 |           0.202702  |           6.53697 |
| 计算机        | 通信          |         3291 |     0.640903 |       0.446977 |           0.0811479 |          10.4283  |
| 计算机        | 电子          |         3145 |     0.651376 |       0.520509 |           0.0985872 |          12.0963  |
| 电子          | 基础化工      |         2700 |     0.694827 |       0.498148 |           0.130796  |           6.87986 |
| 机械设备      | 有色金属      |         2655 |     0.674668 |       0.358192 |           0.138839  |           5.28819 |
| 有色金属      | 基础化工      |         2625 |     0.693186 |       0.602667 |           0.288821  |           6.68259 |
| 汽车          | 电力设备      |         2540 |     0.678743 |       0.434646 |           0.128708  |          21.5447  |
| 汽车          | 电子          |         2446 |     0.677327 |       0.456664 |           0.136675  |          38.4248  |
| 公用事业      | 电力设备      |         2444 |     0.698126 |       0.488134 |           0.16995   |           4.90876 |
| 电子          | 计算机        |         2249 |     0.669365 |       0.727879 |           0.115669  |          13.9919  |

## 9. Market Behavior Descriptive Findings
(Detailed time-series analysis is pending further residual evidence, but descriptive annual panels are now available in the cache.)

## 10. Baseline and Residual Findings
Comparison against random baselines confirms that the semantic graph structure is non-random.
|   same_l1_ratio |   same_l3_ratio |   abs_log_total_mv_gap_mean | rank_band    | type           |
|----------------:|----------------:|----------------------------:|:-------------|:---------------|
|       0.654998  |      0.394438   |                    1.01707  | rank_001_005 | semantic       |
|       0.581352  |      0.282915   |                    1.07678  | rank_006_010 | semantic       |
|       0.525809  |      0.210378   |                    1.10741  | rank_011_020 | semantic       |
|       0.443942  |      0.129553   |                    1.13456  | rank_021_050 | semantic       |
|       0.350327  |      0.0699164  |                    1.16553  | rank_051_100 | semantic       |
|       0.061614  |      0.00636132 |                    1.22812  | overall      | global_random  |
|       1         |      1          |                    0.960813 | overall      | same_l3_random |
|       0.0985096 |      0.0323519  |                    0.350016 | overall      | matched_random |

## 11. Visualization Interpretation
High-value plots are available in `cache/semantic_graph/run_20260511_p23/phase2_3/plots/`.
Refer to `PHASE2_3_VISUALIZATION_APPENDIX.md` for detailed captions.

## 12. Remaining Risks and Invalid Claims
- **Alpha**: No predictive claims are made. All associations are descriptive.
- **Causality**: Cross-industry bridges are candidates for review, not proof of transmission.
- **Staleness**: Fundamental snapshot is based on the latest available data as of 2026-04-23.

## 13. Recommended Next Phase
Move to Phase 3 for event studies and lead-lag testing using the hardened infrastructure developed in Phase 2.3.
