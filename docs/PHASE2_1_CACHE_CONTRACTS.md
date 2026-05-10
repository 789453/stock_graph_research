# PHASE2_1_CACHE_CONTRACTS.md

## 1. 缓存哲学

Phase 2.1 的缓存不是生产系统缓存，而是研究证据缓存。任何耗时计算、关键中间结果、随机基准、月度矩阵、hub 分析和报告摘要都必须落盘。图表和总结报告必须只读缓存，不重跑上游。

缓存的目的：

- 防止重复 IO；
- 防止 AI 反复重算导致口径漂移；
- 让失败结果也可复盘；
- 让每个 view 的结果可独立验证；
- 让 multi-view 比较有统一输入。

---

## 2. 顶层目录

```text
cache/semantic_graph/
  views/
    main_business_detail/
    theme_text/
    chain_text/
    full_text/
  multi_view/
outputs/
  reports/
    phase2_1/
  plots/
    phase2_1/
logs/
  phase2_1/
```

---

## 3. view 目录结构

每个 view 使用：

```text
cache/semantic_graph/views/{view}/{view_key}/
  audit/
  graph/
  edge_layers/
  baselines/
  hub_bridge/
  market_behavior/
  reports/
  manifests/
```

`view_key` 由以下字段生成：

- view name；
- npy path；
- meta path；
- row_ids hash；
- vector shape；
- vector file checksum；
- config version。

---

## 4. manifest 标准

每个任务必须写 manifest：

```json
{
  "phase": "phase2_1",
  "task_id": "T2.1.x",
  "task_name": "",
  "view_name": "",
  "view_key": "",
  "status": "success|failed",
  "started_at": "",
  "finished_at": "",
  "elapsed_seconds": 0,
  "inputs": [],
  "outputs": [],
  "parameters": {},
  "row_counts": {},
  "warnings": [],
  "error": null,
  "safe_to_continue": true
}
```

multi-view 任务可将 `view_name` 写为 `multi_view`。

---

## 5. audit 缓存

```text
audit/semantic_audit.json
audit/alignment_diagnostics.json
audit/near_duplicate_pairs.csv
audit/near_duplicate_summary.json
audit/view_manifest.json
```

`alignment_diagnostics.json` 必须包含：

```json
{
  "n_vectors": 5502,
  "dim": 1024,
  "dtype": "float32",
  "row_ids_count": 5502,
  "row_ids_unique_count": 5502,
  "records_record_id_unique_count": 5502,
  "stock_code_unique_count": 5502,
  "row_order_binding_ok": true,
  "missing_in_records_count": 0,
  "extra_in_records_count": 0
}
```

---

## 6. graph 缓存

```text
graph/neighbors_k100.npz
graph/edges_directed_k100.parquet
graph/edges_mutual_directed_rows_k100.parquet
graph/mutual_pairs_unique_k100.parquet
graph/graph_summary.json
```

`graph_summary.json` 必须包含：

- n_nodes；
- k；
- n_directed_edges；
- n_mutual_directed_rows；
- n_mutual_pairs_unique；
- reciprocity_ratio；
- score quantiles；
- self_neighbor_count；
- duplicate_stock_edge_count。

---

## 7. edge_layers 缓存

```text
edge_layers/edge_candidates_k100.parquet
edge_layers/edge_layer_summary.json
edge_layers/edge_score_by_rank.csv
edge_layers/mutual_ratio_by_rank.csv
edge_layers/rank_band_summary.csv
```

`edge_candidates_k100.parquet` 必须包含：

- src_node_id；
- dst_node_id；
- src_stock_code；
- dst_stock_code；
- src_record_id；
- dst_record_id；
- rank；
- score；
- is_mutual；
- reverse_rank；
- reverse_score；
- score_mean_if_mutual；
- rank_band_exclusive；
- top_001_005；
- top_001_010；
- top_001_020；
- top_001_050；
- top_001_100；
- src_top1_score；
- src_score_gap_from_top1；
- duplicate_risk_flag。

---

## 8. baselines 缓存

```text
baselines/industry_by_rank.csv
baselines/domain_baseline_comparison.parquet
baselines/industry_comparison.json
baselines/score_size_liquidity_regression.csv
baselines/random_baseline_manifest.json
```

`industry_comparison.json` 不允许为空对象。至少包含：

```json
{
  "global_random": {},
  "same_l3_random": {},
  "same_l3_same_size_random": {},
  "same_l3_same_liquidity_random": {},
  "cross_l1_random": {},
  "cross_l1_same_size_liquidity_random": {}
}
```

---

## 9. multi_view baselines

```text
cache/semantic_graph/multi_view/baselines/node_size_liquidity_profile.parquet
cache/semantic_graph/multi_view/baselines/size_liquidity_summary.json
cache/semantic_graph/multi_view/comparisons/industry_view_comparison.csv
cache/semantic_graph/multi_view/comparisons/domain_view_comparison.csv
```

`size_liquidity_summary.json` 必须包含：

```json
{
  "matched_market_nodes": 0,
  "unmatched_nodes": 0,
  "min_required_matched_nodes": 5400,
  "status": "success|failed",
  "fields": [
    "median_total_mv",
    "median_circ_mv",
    "median_turnover_rate",
    "median_amount"
  ]
}
```

如果 `matched_market_nodes < 5400`，状态必须 failed。

---

## 10. hub_bridge 缓存

```text
hub_bridge/node_hub_scores.parquet
hub_bridge/top_hubs.csv
hub_bridge/cross_industry_bridge_edges.parquet
hub_bridge/cross_industry_bridge_edges_sample.csv
hub_bridge/hub_removed_industry_lift.csv
hub_bridge/hub_removed_monthly_corr.csv
hub_bridge/hub_removed_lead_lag.csv
```

必须区分：

- all_edges；
- remove_top_1pct_hub_edges；
- remove_top_5pct_hub_edges。

---

## 11. market_behavior 缓存

multi-view 共享月度矩阵：

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

每个 view：

```text
market_behavior/monthly_pair_corr_by_layer.parquet
market_behavior/monthly_lead_lag_by_layer.parquet
market_behavior/monthly_baseline_comparison.json
market_behavior/monthly_market_behavior_summary.json
```

---

## 12. reports 缓存

每个 view：

```text
outputs/reports/phase2_1/{view}/VIEW_RESEARCH_REPORT.md
outputs/reports/phase2_1/{view}/VIEW_RESEARCH_REPORT.json
```

multi-view：

```text
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.md
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.json
```

报告生成脚本只读缓存，不重跑计算。

---

## 13. 图表缓存

每个 view 图表目录：

```text
outputs/plots/phase2_1/{view}/
```

multi-view 图表目录：

```text
outputs/plots/phase2_1/multi_view/
```

图表命名必须包含 view 或 multi_view。所有图中文字使用英文。

---

## 14. 缓存失败规则

以下情况不允许写 success manifest：

- mutual ratio 为 1.0；
- reverse_score 全 0；
- matched_market_nodes 小于 5400；
- industry_comparison 为空；
- monthly matrix 节点顺序不匹配；
- report summary 缺关键字段；
- 出现裸 `N/A`；
- 四 view 输出路径覆盖。
