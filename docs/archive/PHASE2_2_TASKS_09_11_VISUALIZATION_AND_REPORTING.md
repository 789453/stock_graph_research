# PHASE 2.2 任务 09-11：多样化中文可视化、图表与最终报告

## 0. 中文可视化总原则

Phase 2.2 的图表必须服务研究判断，而不是只展示漂亮图片。每张图必须满足：

- 有清晰中文标题；
- 轴标签完整；
- 图例清楚；
- 显示样本数或统计口径；
- 文件名英文；
- 图中文字使用中文字体；
- 同时保存 PNG 与对应 CSV/JSON；
- 图表不得直接从临时 DataFrame 绘制，必须从已保存结果文件读取。

推荐字体优先级：

```python
font_candidates = [
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS"
]
```

绘图脚本启动时必须检查字体：

```python
import matplotlib.font_manager as fm
available = {f.name for f in fm.fontManager.ttflist}
if not any(x in available for x in font_candidates):
    raise RuntimeError("No Chinese font found. Install Noto Sans CJK SC or SimHei.")
```

## T2.2.9 图表清单

### A. 数据健康与修复状态

| 图名 | 文件 |
|---|---|
| 多 view 数据审计通过率热力图 | `audit_pass_heatmap.png` |
| 每个 view 的 self-edge / reverse-score / mutual 检查 | `edge_sanity_dashboard.png` |
| near duplicate 数量柱状图 | `near_duplicate_count_by_view.png` |
| market matched nodes 仪表图 | `market_profile_match_rate.png` |
| manifest 完整性热力图 | `manifest_completeness_heatmap.png` |

### B. 分数结构

| 图名 | 文件 |
|---|---|
| 各 view score 分布直方图 | `score_distribution_by_view.png` |
| rank 到 mean score 曲线 | `score_by_rank_mean_curve.png` |
| rank 到 p25/p50/p75 区间 | `score_by_rank_quantile_band.png` |
| rank band score violin/box | `score_by_rank_band_boxplot.png` |
| Top1 vs Top100 score gap | `top1_top100_gap_by_view.png` |

### C. 行业与随机基准

| 图名 | 文件 |
|---|---|
| same L1/L2/L3 ratio by rank | `industry_same_ratio_by_rank.png` |
| same L3 lift vs global random | `same_l3_lift_vs_global_random.png` |
| cross L1 ratio by view | `cross_l1_ratio_by_view.png` |
| source L1 -> target L1 热力图 | `l1_to_l1_edge_heatmap.png` |
| view × rank band 行业纯度热力图 | `view_rank_industry_purity_heatmap.png` |

### D. H5 市场共振

| 图名 | 文件 |
|---|---|
| raw vs residual correlation 对比 | `raw_vs_residual_corr_by_view.png` |
| semantic vs random delta heatmap | `h5_delta_heatmap.png` |
| rank band residual corr 曲线 | `residual_corr_by_rank_band.png` |
| permutation p-value heatmap | `h5_pvalue_heatmap.png` |
| effect size heatmap | `h5_effect_size_heatmap.png` |
| bootstrap CI forest plot | `h5_bootstrap_ci_forest.png` |

### E. lead-lag

| 图名 | 文件 |
|---|---|
| lead-lag asymmetry by lag | `lead_lag_asymmetry_by_lag.png` |
| source leads target vs random | `source_leads_target_vs_random.png` |
| chain_text cross-L1 lead-lag heatmap | `chain_cross_l1_lead_lag_heatmap.png` |
| top lead-lag edges table image | `top_lead_lag_edges_table.png` |

### F. shock 与极端共现

| 图名 | 文件 |
|---|---|
| 成交额 shock 共现率 | `amount_shock_cooccurrence.png` |
| 换手 shock 共现率 | `turnover_shock_cooccurrence.png` |
| 极端上涨共现率 | `extreme_up_cooccurrence.png` |
| 极端下跌共现率 | `extreme_down_cooccurrence.png` |
| theme_text 中等边题材共现图 | `theme_mid_rank_shock_cooccurrence.png` |

### G. hub / bridge

| 图名 | 文件 |
|---|---|
| in-degree 分布 | `hub_indegree_distribution.png` |
| hub score vs 行业熵 | `hub_score_vs_industry_entropy.png` |
| cross-industry bridge heatmap | `cross_industry_bridge_heatmap.png` |
| L1 -> L1 Sankey 数据表 | `l1_bridge_sankey_data.csv` |
| 典型 bridge ego network | `bridge_ego_network_examples.png` |

### H. 多 view overlap

| 图名 | 文件 |
|---|---|
| view edge overlap heatmap | `view_edge_overlap_heatmap.png` |
| multi-view consensus level 分布 | `consensus_level_distribution.png` |
| consensus level vs residual corr | `consensus_level_vs_residual_corr.png` |
| view-specific edge H5 对比 | `view_specific_h5_comparison.png` |

### I. regime stability

| 图名 | 文件 |
|---|---|
| H5 delta across regime | `h5_delta_across_regimes.png` |
| bull/bear residual corr | `bull_bear_residual_corr.png` |
| high/low volatility comparison | `volatility_regime_comparison.png` |
| time rolling H5 metric | `rolling_h5_metric.png` |

## T2.2.10 绘图数据契约

每张 PNG 必须对应一个数据文件：

```text
outputs/plots/phase2_2/{view}/{plot_name}.png
outputs/plots/phase2_2/{view}/{plot_name}.csv
outputs/plots/phase2_2/{view}/{plot_name}.json
```

跨 view 图：

```text
outputs/plots/phase2_2/multi_view/{plot_name}.png
outputs/plots/phase2_2/multi_view/{plot_name}.csv
outputs/plots/phase2_2/multi_view/{plot_name}.json
```

JSON 至少包含：

```json
{
  "plot_name": "...",
  "phase": "phase2_2",
  "source_csv": "...",
  "source_metrics": [],
  "generated_at": "...",
  "view_name": "...",
  "rank_band": "...",
  "caption": "...",
  "interpretation": "...",
  "warnings": []
}
```

## T2.2.11 最终报告

输出：

```text
outputs/reports/phase2_2/PHASE2_2_RESEARCH_SUMMARY.md
outputs/reports/phase2_2/PHASE2_2_RESEARCH_SUMMARY.json
outputs/reports/phase2_2/PHASE2_2_H5_DECISION_TABLE.csv
outputs/reports/phase2_2/PHASE2_2_VISUALIZATION_INDEX.md
```

最终报告结构：

1. 数据与代码状态；
2. Phase 2.1 遗留问题是否全部解决；
3. 四 view 图结构；
4. 行业/市值/流动性基准；
5. 月度面板质量；
6. H5 原始收益相关；
7. H5 残差收益相关；
8. H5 shock 共现；
9. H5 lead-lag；
10. Hub/Bridge 稳健性；
11. 去 near duplicate 稳健性；
12. 多 view consensus；
13. 失败假设；
14. 可进入下一阶段的结论；
15. 禁止进入下一阶段的结论。

结论必须是可证伪的，例如：

```text
H5.1 在 main_business_detail 的 rank_001_005 层上，仅 raw return 显著，L3 residual 后不显著，判定为行业暴露驱动，不支持市场共振增量。

H5.4 在 chain_text 的 cross-L1 rank_021_050 层上，src_leads_dst_1m 显著高于 cross_l1_same_size_liquidity_random，且去 hub 后仍保留，判定为部分支持产业链 lead-lag。
```
