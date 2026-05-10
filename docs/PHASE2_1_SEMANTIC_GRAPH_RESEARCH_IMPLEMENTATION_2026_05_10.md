# PHASE2_1_SEMANTIC_GRAPH_RESEARCH_IMPLEMENTATION_2026_05_10.md

## 1. 实施目标

本文是 Phase 2.1 的实施补充文档，承接完整主规格，但更强调任务落地、脚本命名和结果组织。Phase 2.1 的实施目标是：在不工程化、不做 GNN、不做回测、不做图因子的前提下，修复旧 Phase 2 的错误，实现四 view 语义图研究，并以月度时序和严格 matched baseline 检验金融解释力。

---

## 2. 推荐脚本命名

```text
scripts/16_phase2_old_results_audit.py
scripts/17_audit_multi_view_semantic_data.py
scripts/18_build_multi_view_knn.py
scripts/19_build_fixed_edge_candidates.py
scripts/20_multi_view_industry_baselines.py
scripts/21_repair_size_liquidity_profile.py
scripts/22_domain_baseline_comparison.py
scripts/23_score_size_liquidity_regression.py
scripts/24_multi_view_hub_bridge.py
scripts/25_build_monthly_market_panel.py
scripts/26_monthly_pair_corr_and_lead_lag.py
scripts/27_multi_view_summary_report.py
```

---

## 3. 推荐源码文件

保持研究脚本优先，但可增加轻量工具模块：

```text
src/semantic_graph_research/phase2_1_view_loader.py
src/semantic_graph_research/phase2_1_mutual.py
src/semantic_graph_research/phase2_1_edge_layers.py
src/semantic_graph_research/phase2_1_baselines.py
src/semantic_graph_research/phase2_1_market_panel.py
src/semantic_graph_research/phase2_1_pair_corr.py
src/semantic_graph_research/phase2_1_reporting.py
```

这些模块只做薄封装，不追求生产系统架构。

---

## 4. 实施原则

1. 先修 bug，再做新研究。
2. 先四 view audit，再建图。
3. 先 edge candidates 正确，再做 baselines。
4. 先 size/liquidity 修复，再做 market behavior。
5. 先 monthly panel 缓存，再做 pair corr。
6. 先 view report，再 multi-view summary。
7. 任何失败都要显式写 failed manifest。

---

## 5. IO 原则

- 大 parquet 读取优先 DuckDB 或 Polars lazy；
- 只读必要列；
- 使用日期谓词下推；
- 使用股票代码 join 限制 universe；
- 中间结果保存 parquet；
- 报告和图表只读缓存；
- 避免重复读取原始 NPY；
- 避免重复读取全量行情数据。

---

## 6. 数据读取口径

### 6.1 语义 view

每个 view：

```text
a_share_semantic_dataset/npy/{view}/{view}-all.npy
a_share_semantic_dataset/npy/{view}/{view}-all.meta.json
```

实际本地路径以配置文件为准。

### 6.2 市场数据

使用：

- `stock_daily.parquet`
- `stock_daily_basic.parquet`
- `stock_sw_member.parquet`

2018-01-01 至 2026-04-23 为 Phase 2.1 主窗口。

---

## 7. 输出原则

每个任务输出：

- manifest json；
- summary json；
- summary md；
- log；
- csv/parquet；
- png 图表，如果有图；
- warnings；
- invalidation 状态。

---

## 8. 质量门槛

任务必须失败的条件：

- view audit 不通过；
- k100 self-neighbor 存在；
- mutual ratio 等于 1；
- reverse_score 全 0；
- matched market nodes 小于 5400；
- industry_comparison 为空；
- monthly matrix node order 不一致；
- summary 缺关键字段；
- 图表脚本重跑上游计算。

---

## 9. 最终产物

最终至少生成：

```text
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.md
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.json
outputs/plots/phase2_1/multi_view/view_comparison_dashboard.png
PROJECT_STATE.md 更新
```

如果这些不存在，Phase 2.1 不算完成。
