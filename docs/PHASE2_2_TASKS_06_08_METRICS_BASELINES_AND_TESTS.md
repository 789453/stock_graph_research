# PHASE 2.2 任务 06-08：指标、随机基准、显著性与稳健性检验

## T2.2.6 多层随机控制组

### 原则

随机基准不是为了“让语义边赢”，而是为了判断语义边是否超越容易解释的结构：

- 行业；
- 市值；
- 流动性；
- 共同市场暴露；
- 节点度数；
- hub；
- near duplicate。

### 控制组类型

| 控制组 | 用途 |
|---|---|
| `global_random` | 全市场基本随机基准 |
| `same_l3_random` | 控制三级行业 |
| `same_l3_same_size_random` | 控制三级行业 + 市值桶 |
| `same_l3_same_liquidity_random` | 控制三级行业 + 流动性桶 |
| `same_l3_same_size_liquidity_random` | 控制行业 + size + liquidity |
| `cross_l1_random` | 跨一级行业随机基准 |
| `cross_l1_same_size_liquidity_random` | 跨行业 + size/liquidity matched |
| `degree_matched_random` | 控制目标节点入度分布 |
| `hub_removed_semantic` | 移除入度 top 1% hub 后的语义边 |
| `near_duplicate_removed_semantic` | 移除近重复边后的语义边 |

### 抽样要求

- 每个 view、每个 rank band、每个控制组至少重复 200 次；
- 保持 src_node_id 的边数分布；
- 随机样本输出 seed；
- 如果候选池不足，应记录 `pool_shortage_ratio`，不能静默减少样本；
- 对同 L3 控制组，不再比较 same-L3 ratio，而比较市场行为指标；
- 对 cross-L1 控制组，不再比较 cross-L1 ratio，而比较 residual co-movement。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/phase2_2/baselines/random_edges/{baseline_type}/repeat_{000..199}.parquet
cache/semantic_graph/views/{view}/{view_key}/phase2_2/baselines/random_baseline_manifest.json
cache/semantic_graph/views/{view}/{view_key}/phase2_2/baselines/random_pool_shortage.csv
```

## T2.2.7 统计检验

### 主要比较

对每个 view、rank band、指标：

```text
semantic_metric_mean - random_metric_mean
```

### 推荐统计量

| 统计量 | 说明 |
|---|---|
| `semantic_mean` | 语义边均值 |
| `random_mean_mean` | 多次随机均值的均值 |
| `random_mean_std` | 多次随机均值的标准差 |
| `delta_mean` | 语义 - 随机 |
| `lift` | 语义 / 随机 |
| `z_score` | delta / random std |
| `permutation_p_value` | 随机均值 >= 语义均值 的比例 |
| `bootstrap_ci_low/high` | 语义边 bootstrap 置信区间 |
| `effect_size_cohens_d` | 标准化差异 |
| `n_edges` | 语义边数量 |
| `n_random_repeats` | 随机次数 |

### 注意

- 不要只看 p-value；
- 样本巨大时很小差异也可能显著；
- 必须同时报告 effect size；
- 对相关系数应用 Fisher z transformation 后再聚合更稳健；
- 对月度时间序列必须考虑自相关，可增加 block bootstrap；
- 对多重检验建议输出 FDR q-value。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/phase2_2/stat_tests/h5_metric_tests.csv
cache/semantic_graph/views/{view}/{view_key}/phase2_2/stat_tests/h5_metric_tests.json
cache/semantic_graph/multi_view/phase2_2/stat_tests/h5_multi_view_summary.csv
outputs/reports/phase2_2/{view}/h5_statistical_tests_report.md
```

## T2.2.8 稳健性检验

### 8.1 去 hub

对每个 view：

- 计算 target in-degree；
- 移除 top 0.5%、1%、2%、5% hub；
- 重算 H5 关键指标；
- 如果效果完全由 top hub 驱动，则标记为 `hub_driven`。

输出：

```text
hub_removed_sensitivity.csv
hub_removed_sensitivity.json
```

### 8.2 去 near duplicate

- 移除 `score >= 0.999999` 边；
- 移除同一 near duplicate component 内的边；
- 重算行业纯度、residual correlation、lead-lag；
- 若结果消失，标记为 `duplicate_driven`。

输出：

```text
near_duplicate_removed_sensitivity.csv
near_duplicate_removed_sensitivity.json
```

### 8.3 分 regime

建议先做四个 regime：

1. 全样本；
2. 高波动月份；
3. 低波动月份；
4. 市场上涨月份；
5. 市场下跌月份；
6. 成交额放大月份；
7. 指数极端月份。

输出：

```text
regime_h5_metrics.csv
regime_h5_metrics.json
```

### 8.4 分 view

比较：

- `main_business_detail`
- `theme_text`
- `chain_text`
- `full_text`
- multi-view consensus
- view-specific only

输出：

```text
view_comparison_h5_metrics.csv
view_overlap_h5_metrics.csv
```

### 8.5 分 rank band

必须同时输出 exclusive band 和 cumulative topK：

```text
rank_001_005
rank_006_010
rank_011_020
rank_021_050
rank_051_100

top_001_005
top_001_010
top_001_020
top_001_050
top_001_100
```

## H5 最终判定规则

```yaml
h5_decision_rules:
  supported_with_controls:
    required:
      - corr_resid_full_neutral_delta_mean > 0
      - permutation_p_value < 0.05
      - effect_size_cohens_d >= 0.10
      - stable_after_hub_removal: true
      - stable_after_duplicate_removal: true
  partially_supported:
    required_any:
      - shock_cooccurrence_supported
      - cross_l1_lead_lag_supported
      - view_consensus_supported
    forbidden:
      - raw_return_only
  rejected_after_monthly_test:
    condition:
      - all_controlled_metrics_close_to_random
  inconclusive:
    condition:
      - insufficient_common_months
      - too_many_missing_values
      - unstable_across_regime
```

最终报告不得使用含糊措辞，比如“看起来有效”。必须明确：

- 哪个 view；
- 哪个 layer；
- 哪个指标；
- 相比哪个 random；
- delta 多大；
- CI 与 p-value；
- 是否通过稳健性。
