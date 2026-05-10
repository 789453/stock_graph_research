# PHASE2_1_TASKS_06_09_HUB_BRIDGE_MARKET_BEHAVIOR.md

## T2.1.8 multi-view hub and bridge

### 目标

研究四个 view 的 hub 与跨行业桥，判断 hub 是真实经济中心、题材中心、产业链枢纽，还是文本泛化噪声。

### 指标

- in_degree_k100；
- mutual_in_degree；
- cross_l1_in_degree；
- cross_l3_in_degree；
- neighbor_l3_entropy；
- score concentration；
- bridge node score；
- hub type candidate。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/hub_bridge/node_hub_scores.parquet
cache/semantic_graph/views/{view}/{view_key}/hub_bridge/top_hubs.csv
cache/semantic_graph/views/{view}/{view_key}/hub_bridge/cross_industry_bridge_edges.parquet
cache/semantic_graph/views/{view}/{view_key}/hub_bridge/cross_industry_bridge_edges_sample.csv
cache/semantic_graph/multi_view/comparisons/hub_overlap_by_view.csv
```

### 去 hub 稳健性

必须输出：

```text
hub_removed_industry_lift.csv
hub_removed_monthly_corr.csv
hub_removed_lead_lag.csv
hub_removed_baseline_delta.csv
```

对比：

- all_edges；
- remove_top_1pct_hub_edges；
- remove_top_5pct_hub_edges。

---

## T2.1.9 monthly market panel

### 目标

构造 2018 年以来的月度市场行为矩阵，为 pair correlation 和 lead-lag 提供统一输入。

### 指标

- monthly_return；
- monthly_volatility；
- monthly_amount_change；
- monthly_turnover_change；
- market_return；
- l1_return；
- l3_return；
- residual_market_return；
- residual_l1_return；
- residual_l3_return；
- amount_shock；
- turnover_shock；
- extreme_up；
- extreme_down。

### 输出

```text
cache/semantic_graph/multi_view/market_behavior/monthly_panel.parquet
cache/semantic_graph/multi_view/market_behavior/monthly_ret_matrix.npy
cache/semantic_graph/multi_view/market_behavior/monthly_ret_resid_market.npy
cache/semantic_graph/multi_view/market_behavior/monthly_ret_resid_l1.npy
cache/semantic_graph/multi_view/market_behavior/monthly_ret_resid_l3.npy
cache/semantic_graph/multi_view/market_behavior/monthly_amount_z_matrix.npy
cache/semantic_graph/multi_view/market_behavior/monthly_vol_matrix.npy
cache/semantic_graph/multi_view/market_behavior/monthly_matrices_manifest.json
```

### 失败条件

- 矩阵列顺序与 node_id 不一致；
- 月份数量不足；
- 大量节点全空；
- 未保存 manifest。

---

## T2.1.10 monthly pair corr and lead-lag

### 目标

对每个 view、每个边层、每个 matched random baseline 计算月度市场行为关联。

### 指标

- same_month_return_corr；
- market_residual_corr；
- l1_residual_corr；
- l3_residual_corr；
- amount_shock_corr；
- volatility_corr；
- src_leads_dst_1m；
- dst_leads_src_1m；
- src_leads_dst_2m；
- dst_leads_src_2m；
- src_leads_dst_3m；
- dst_leads_src_3m；
- lead_lag_asymmetry。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/market_behavior/monthly_pair_corr_by_layer.parquet
cache/semantic_graph/views/{view}/{view_key}/market_behavior/monthly_lead_lag_by_layer.parquet
cache/semantic_graph/views/{view}/{view_key}/market_behavior/monthly_baseline_comparison.json
outputs/reports/phase2_1/{view}/monthly_market_behavior_report.md
```

### 解释纪律

- lead-lag 是描述性关联；
- 不写 predictor；
- 不写 alpha；
- 不写 signal；
- 不生成回测曲线。

---

## T2.1.11 multi-view summary

### 目标

汇总四个 view 的行业解释力、跨行业桥、hub、月度残差相关和 lead-lag，形成最终研究判断。

### 输出

```text
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.md
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.json
outputs/plots/phase2_1/multi_view/view_comparison_dashboard.png
```

### 必须回答

1. 哪个 view 行业解释力最强？
2. 哪个 view 跨行业桥最强？
3. theme_text 是否解释成交冲击？
4. chain_text 是否解释 lead-lag？
5. main_business_detail 是否适合 peer？
6. full_text 是否 hub 污染明显？
7. matched random 后是否有增量？
8. H5 最终状态是什么？
9. 是否允许 Phase 3？

---

## T2.1.12 project state update

### 目标

更新 `PROJECT_STATE.md`，使项目状态与 Phase 2.1 结果一致。

### 必须写入

- 旧 Phase 2 invalidated 结果；
- 四 view 完成状态；
- H5 状态；
- Phase 3 是否允许；
- 下一步推荐。
