# PHASE2_1_TASKS_03_05_BASELINES_AND_DOMAINS.md

## T2.1.4 四 view 行业基准

### 目标

比较四个 view 的 L1/L2/L3 行业解释力，明确每个 view 是同行业 peer、更偏主题，还是更偏产业链跨行业关系。

### 指标

- same_l1_ratio_by_rank；
- same_l2_ratio_by_rank；
- same_l3_ratio_by_rank；
- same_l3_lift_by_rank；
- cross_l1_ratio_by_rank；
- exclusive rank band；
- cumulative topK。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/baselines/industry_by_rank.csv
cache/semantic_graph/multi_view/comparisons/industry_view_comparison.csv
outputs/plots/phase2_1/multi_view/same_l3_lift_by_view.png
outputs/plots/phase2_1/multi_view/cross_l1_ratio_by_view.png
```

### 解释原则

- main_business_detail 预期 same L3 lift 较高；
- theme_text 预期 cross L1 更多；
- chain_text 的同业纯度低不一定是失败；
- full_text 必须检查 hub 和 near duplicate。

---

## T2.1.5 市值/流动性 profile 修复

### 目标

修复旧 `nodes_with_market_data=0` 问题，构造真实的 size/liquidity/amount profile。

### 字段

从 `stock_daily_basic` 读取：

- total_mv；
- circ_mv；
- turnover_rate。

从 `stock_daily` 读取：

- amount。

窗口：2018-01-01 至 2026-04-23。

### 输出字段

- median_total_mv；
- median_circ_mv；
- median_turnover_rate；
- median_amount；
- log_total_mv；
- log_amount；
- size_bucket_10；
- liquidity_bucket_10；
- amount_bucket_10。

### 输出

```text
cache/semantic_graph/multi_view/baselines/node_size_liquidity_profile.parquet
cache/semantic_graph/multi_view/baselines/size_liquidity_summary.json
outputs/reports/phase2_1/size_liquidity_repair_report.md
```

### 失败条件

- matched_market_nodes < 5400；
- matched_market_nodes = 0；
- 字段名混用 total_mv/total_market_cap；
- 读取全量 parquet 后再筛选，且未记录原因。

---

## T2.1.6 domain and matched random baselines

### 目标

检验语义边是否在行业、市值、流动性基准之外保留增量。

### 必须输出

- same_size_bucket_ratio_by_rank；
- same_liquidity_bucket_ratio_by_rank；
- same_amount_bucket_ratio_by_rank；
- semantic vs global random；
- same L3 semantic vs same L3 random；
- same L3 + same size semantic vs matched random；
- same L3 + same liquidity semantic vs matched random；
- cross L1 semantic vs cross L1 random；
- cross L1 + size/liquidity matched random。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/baselines/domain_baseline_comparison.parquet
cache/semantic_graph/views/{view}/{view_key}/baselines/industry_comparison.json
outputs/reports/phase2_1/{view}/domain_baseline_report.md
```

### 失败条件

- industry_comparison 为空；
- random baseline 没有 manifest；
- src distribution 没有匹配；
- cross L1 只统计数量，不与 random 比较。

---

## T2.1.7 score exposure regression

### 目标

检验语义 score 是否被行业、市值、流动性机械解释。

### 回归变量

被解释变量：

- score；
- rank-adjusted score；
- local score percentile；
- mutual flag。

解释变量：

- same_l1；
- same_l3；
- abs log market cap diff；
- abs log amount diff；
- same_size_bucket；
- same_liquidity_bucket；
- turnover difference；
- amount difference。

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/baselines/score_size_liquidity_regression.csv
outputs/reports/phase2_1/{view}/score_exposure_regression_report.md
outputs/plots/phase2_1/{view}/score_exposure_regression_coefficients_{view}.png
```

### 解释原则

回归不是因子模型，不是预测模型，只是判断语义图是否混入规模/流动性结构。
