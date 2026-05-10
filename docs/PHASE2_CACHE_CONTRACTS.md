# PHASE2_CACHE_CONTRACTS

## 1. 缓存原则

Phase 2 的缓存不是为了生产系统，而是为了研究复利。任何大 IO、候选边、基准样本、市场行为统计都必须落盘。图表和报告只读缓存，不重跑上游。

## 2. 目录

```text
cache/semantic_graph/2eebde04e582/phase2/
  manifests/
  edge_layers/
  baselines/
  hub_bridge/
  market_behavior/
  reports/
outputs/plots/phase2/
outputs/reports/phase2/
logs/phase2/
```

## 3. manifest 标准字段

每个任务必须写 manifest：

```json
{
  "task_id": "T2.x",
  "task_name": "",
  "phase1_cache_key": "2eebde04e582",
  "started_at": "",
  "finished_at": "",
  "status": "success|failed",
  "inputs": [],
  "outputs": [],
  "parameters": {},
  "row_counts": {},
  "warnings": [],
  "error": null
}
```

## 4. 关键缓存文件

### edge_candidates_k100.parquet

| 字段 | 说明 |
|---|---|
| src_node_id | 源节点 |
| dst_node_id | 目标节点 |
| src_stock_code | 源股票 |
| dst_stock_code | 目标股票 |
| rank | 近邻名次 |
| score | cosine/inner product |
| is_mutual | 是否互惠 |
| reverse_rank | 反向 rank |
| reverse_score | 反向 score |
| rank_band | core/strong/stable/context/extended |
| score_quantile_global | 全局分数分位 |
| src_score_gap_from_top1 | 相对本节点 top1 的分数差 |

### node_size_liquidity_profile.parquet

| 字段 | 说明 |
|---|---|
| node_id | 节点 |
| stock_code | 股票 |
| median_total_mv | 2018-2026 中位总市值 |
| median_circ_mv | 2018-2026 中位流通市值 |
| median_turnover_rate | 中位换手 |
| median_amount | 中位成交额 |
| mv_bucket_10 | 市值十分位 |
| liquidity_bucket_10 | 流动性十分位 |

### pair_behavior_by_layer.parquet

| 字段 | 说明 |
|---|---|
| layer_name | 边层 |
| pair_id | 边 pair |
| src_stock_code | 源股票 |
| dst_stock_code | 目标股票 |
| same_l1/l2/l3 | 当前申万关系 |
| rank_band | rank 层 |
| score | 语义分数 |
| return_corr_daily | 日收益相关 |
| residual_return_corr_l1 | L1 残差收益相关 |
| volatility_corr | 波动相关 |
| amount_shock_corr | 成交冲击相关 |
| extreme_up_cooccurrence | 极端上涨共现 |
| extreme_down_cooccurrence | 极端下跌共现 |

## 5. 图表只读缓存

任何 `plot_phase2_*.py` 不允许读取原始 NPY，不允许重跑 FAISS，不允许读取全量 daily/basic 原表。只能读取 Phase 2 缓存 parquet/json。
