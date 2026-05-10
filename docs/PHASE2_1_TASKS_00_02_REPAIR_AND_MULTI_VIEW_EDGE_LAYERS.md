# PHASE2_1_TASKS_00_02_REPAIR_AND_MULTI_VIEW_EDGE_LAYERS.md

## T2.1.0 旧结果冻结

### 目标

冻结 Phase 2 旧结果，明确哪些可参考、哪些被 bug invalidated、哪些只能作为 static proxy。

### 输入

- `PROJECT_STATE.md`
- `cache/semantic_graph/2eebde04e582/`
- `outputs/reports/phase2/`
- `src/semantic_graph_research/phase2_graph_layers.py`
- `scripts/10_size_liquidity_domain.py`
- `scripts/14_semantic_market_association.py`

### 输出

```text
outputs/reports/phase2_1/PHASE2_OLD_RESULTS_AUDIT.md
cache/semantic_graph/multi_view/manifests/phase2_old_result_audit.json
```

### 必须标记

- mutual_ratio=1.0：INVALIDATED_BY_BUG；
- reverse_score：INVALIDATED_BY_BUG；
- size_liquidity_summary：INVALIDATED_BY_BUG；
- old H5：REJECTED_STATIC_PROXY / NOT_RETESTED_MONTHLY；
- application_scenarios_json：HISTORICAL_SINGLE_VIEW_ONLY。

---

## T2.1.1 四 view 数据审计

### 目标

对 `main_business_detail`、`theme_text`、`chain_text`、`full_text` 四个 view 做完整审计，确认它们可以作为 Phase 2.1 主研究对象。

### 检查项

- npy 存在；
- meta 存在；
- shape = 5502 × 1024；
- dtype = float32；
- finite；
- no zero vector；
- L2 norm；
- row_ids count；
- row_ids unique；
- records record_id unique；
- stock_code unique；
- row_ids 与 records 集合一致；
- row_ids 与向量行顺序绑定；
- near duplicate pairs；
- as-of/fina 字段存在性检查。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/audit/semantic_audit.json
cache/semantic_graph/views/{view}/{view_key}/audit/alignment_diagnostics.json
cache/semantic_graph/views/{view}/{view_key}/audit/near_duplicate_pairs.csv
outputs/reports/phase2_1/{view}/view_audit_report.md
```

### 失败条件

- 任何 view shape 不符；
- row_ids 重复；
- records record_id 重复；
- stock_code 重复；
- row order binding 失败；
- finite 检查失败。

---

## T2.1.2 四 view k100 构图

### 目标

对四个 view 分别构建 k=100 语义候选图。

### 方法

- L2 normalize；
- FAISS GPU；
- IndexFlatIP；
- search k+1；
- 移除 self-neighbor；
- 每行必须填满 k；
- 保存 directed edges；
- 使用修复版 mutual 函数保存 mutual directed rows 和 unique mutual pairs。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/graph/neighbors_k100.npz
cache/semantic_graph/views/{view}/{view_key}/graph/edges_directed_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/graph/edges_mutual_directed_rows_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/graph/mutual_pairs_unique_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/graph/graph_summary.json
```

### 失败条件

- self-neighbor 存在；
- 每节点邻居数不等于 100；
- edge count 不等于 5502 × 100；
- mutual ratio 等于 1；
- reverse_score 无法计算。

---

## T2.1.3 修复版 edge candidates

### 目标

生成可用于 Phase 2.1 所有后续分析的统一 edge candidate 表。

### 必须字段

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

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_candidates_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_layer_summary.json
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_score_by_rank.csv
cache/semantic_graph/views/{view}/{view_key}/edge_layers/mutual_ratio_by_rank.csv
```

### 失败条件

- reverse_score 全空；
- mutual 全 True；
- rank band 命名混乱；
- topK 与 rank band 混写；
- src_stock_code 等于 dst_stock_code。
