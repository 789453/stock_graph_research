# PHASE 2.2 缓存、CSV/JSON/YAML/Parquet/PNG 输出契约

## 0. 目录结构

```text
cache/semantic_graph/phase2_2/
  manifests/
  market_panel/
    node_monthly_panel.parquet
    matrices/
  multi_view/
    comparisons/
    stat_tests/
    visual_data/
  views/
    {view}/{view_key}/
      edge_layers/
      baselines/
      market_behavior/
      stat_tests/
      hub_bridge/
      plots_data/

outputs/reports/phase2_2/
outputs/plots/phase2_2/
logs/phase2_2/
configs/phase2_2_market_resonance.yaml
```

## 1. YAML 配置模板

```yaml
project:
  phase: phase2_2
  research_name: semantic_graph_market_resonance_and_temporal_decomposition
  start_date: "20180101"
  end_date: "20260423"
  frequency: monthly
  allow_gnn: false
  allow_backtest: false
  allow_graph_factor: false
  allow_new_embedding: false

views:
  - main_business_detail
  - theme_text
  - chain_text
  - full_text

graph:
  k: 100
  metric: inner_product_on_l2_normalized
  require_fixed_edge_candidates: true
  require_no_legacy_rank_names: true

rank_layers:
  exclusive:
    rank_001_005: [1, 5]
    rank_006_010: [6, 10]
    rank_011_020: [11, 20]
    rank_021_050: [21, 50]
    rank_051_100: [51, 100]
  cumulative:
    top_001_005: [1, 5]
    top_001_010: [1, 10]
    top_001_020: [1, 20]
    top_001_050: [1, 50]
    top_001_100: [1, 100]

market_panel:
  min_common_months: 24
  residuals:
    raw: true
    market: true
    sw_l1: true
    sw_l3: true
    size_liquidity: true
    full_neutral: true
  shock:
    amount_z_threshold: 2.0
    turnover_z_threshold: 2.0
    extreme_quantile: 0.05

baselines:
  random_seed: 20260510
  n_random_repeats: 200
  baseline_types:
    - global_random
    - same_l3_random
    - same_l3_same_size_random
    - same_l3_same_liquidity_random
    - same_l3_same_size_liquidity_random
    - cross_l1_random
    - cross_l1_same_size_liquidity_random
    - degree_matched_random

performance:
  pair_block_size: 200000
  matrix_dtype: float32
  parquet_compression: zstd
  use_duckdb: true
  use_projection_pushdown: true
  cache_intermediate_matrices: true

visualization:
  language: zh_CN
  require_chinese_font: true
  dpi: 160
  save_png: true
  save_svg: false
```

## 2. CSV 契约

### `h5_metric_tests.csv`

| 字段 | 类型 |
|---|---|
| `view_name` | string |
| `view_key` | string |
| `rank_layer_type` | string |
| `rank_layer` | string |
| `edge_set_type` | string |
| `baseline_type` | string |
| `metric` | string |
| `semantic_n_edges` | int |
| `semantic_mean` | float |
| `semantic_median` | float |
| `random_mean_mean` | float |
| `random_mean_std` | float |
| `delta_mean` | float |
| `lift` | float |
| `effect_size_cohens_d` | float |
| `permutation_p_value` | float |
| `bootstrap_ci_low` | float |
| `bootstrap_ci_high` | float |
| `fdr_q_value` | float |
| `decision` | string |

### `edge_market_metrics_by_layer.csv`

| 字段 | 类型 |
|---|---|
| `view_name` | string |
| `rank_band_exclusive` | string |
| `n_edges` | int |
| `corr_raw_return_mean` | float |
| `corr_resid_market_mean` | float |
| `corr_resid_l1_mean` | float |
| `corr_resid_l3_mean` | float |
| `corr_resid_full_neutral_mean` | float |
| `corr_amount_z_mean` | float |
| `cooccur_extreme_up_mean` | float |
| `src_leads_dst_1m_mean` | float |
| `dst_leads_src_1m_mean` | float |
| `lead_lag_asymmetry_1m_mean` | float |
| `common_months_mean` | float |

## 3. JSON 契约

### `PHASE2_2_RESEARCH_SUMMARY.json`

```json
{
  "phase": "phase2_2",
  "status": "success|failed|partial",
  "commit_sha": "...",
  "config_sha256": "...",
  "h5_overall_decision": "supported_with_controls|partially_supported|rejected_after_monthly_test|inconclusive",
  "view_decisions": {
    "main_business_detail": {},
    "theme_text": {},
    "chain_text": {},
    "full_text": {}
  },
  "blocking_errors": [],
  "warnings": [],
  "required_outputs": {
    "market_panel": true,
    "edge_metrics": true,
    "random_baselines": true,
    "stat_tests": true,
    "visualizations": true
  }
}
```

## 4. Parquet 契约

### `edge_market_metrics.parquet`

必须保留边级明细，但可以按 view 分区。

字段：

```text
src_node_id
dst_node_id
src_stock_code
dst_stock_code
rank
score
rank_band_exclusive
is_mutual
baseline_type
edge_set_type
corr_raw_return
corr_resid_market
corr_resid_l1
corr_resid_l3
corr_resid_size_liquidity
corr_resid_full_neutral
corr_volatility
corr_amount_z
corr_turnover_z
cooccur_extreme_up
cooccur_extreme_down
src_leads_dst_1m
dst_leads_src_1m
lead_lag_asymmetry_1m
src_leads_dst_2m
dst_leads_src_2m
lead_lag_asymmetry_2m
src_leads_dst_3m
dst_leads_src_3m
lead_lag_asymmetry_3m
common_months
```

## 5. PNG 契约

每个 PNG 同目录必须有：

- `.csv`
- `.json`
- 可选 `.md` 图注

图注字段：

```json
{
  "title": "中文标题",
  "question": "这张图回答什么研究问题",
  "method": "如何计算",
  "key_reading": "如何解读",
  "caveat": "注意事项",
  "source_files": []
}
```

## 6. 失败阻断

任何任务如果出现以下情况，不允许写 success：

- 空 CSV；
- 空 JSON；
- 关键字段全为 NaN；
- H5 决策缺失；
- manifest 缺失；
- view_key 不一致；
- 输入文件 fingerprint 不一致；
- 边数不等于预期；
- self-edge > 0；
- reverse_score 缺失；
- 中文字体缺失但仍生成中文图。
