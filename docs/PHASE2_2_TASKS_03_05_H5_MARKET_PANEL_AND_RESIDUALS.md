# PHASE 2.2 任务 03-05：H5 市场共振、月度面板与收益残差分解

## T2.2.3 构造月度节点市场面板

### 目标

将 2018-01-01 至 2026-04-23 的日频数据压缩为节点级月度面板，供边级市场共振计算使用。

### 输入

```text
stock_daily.parquet
stock_daily_basic.parquet
stock_sw_member.parquet
records-all.parquet
node_size_liquidity_profile.parquet
```

### 节点级月度字段

| 字段 | 说明 |
|---|---|
| `stock_code` | 股票代码 |
| `month` | 月份，YYYY-MM |
| `monthly_return` | 月末复权价格 / 上月末复权价格 - 1 |
| `monthly_log_return` | log return |
| `monthly_volatility` | 日收益标准差 |
| `monthly_downside_volatility` | 负日收益标准差 |
| `monthly_max_drawdown` | 月内最大回撤 |
| `monthly_amount` | 月成交额均值或中位数 |
| `monthly_amount_z` | 成交额月度横截面 z-score |
| `monthly_turnover` | 换手率均值或中位数 |
| `monthly_turnover_z` | 换手率月度横截面 z-score |
| `extreme_up_flag` | 月收益位于全市场 top 5% |
| `extreme_down_flag` | 月收益位于全市场 bottom 5% |
| `amount_shock_flag` | 成交额 z-score > 2 |
| `turnover_shock_flag` | 换手率 z-score > 2 |
| `valid_trading_days` | 当月有效交易日数 |

### 推荐实现

- 使用 DuckDB 或 Polars lazy scan；
- 只读取必要列；
- 先按股票、日期排序；
- 用月末复权价格计算收益；
- 日收益、波动和最大回撤在月内计算；
- 月度矩阵再统一 pivot 成 `N x T`。

### 输出

```text
cache/semantic_graph/phase2_2/market_panel/node_monthly_panel.parquet
cache/semantic_graph/phase2_2/market_panel/node_monthly_panel.csv.gz
cache/semantic_graph/phase2_2/market_panel/node_monthly_panel_summary.json
outputs/reports/phase2_2/market_panel_node_summary.md
```

### 必须检查

- 覆盖股票数 >= 5400；
- 月份数 >= 96；
- 每月有效股票数 >= 5000；
- `monthly_return` 非 finite 比例不得超过 5%；
- 极端收益 flag 每月比例应接近 5%，但允许因并列值略偏；
- 不允许把停牌/缺失硬填成 0 收益。

## T2.2.4 收益残差分解

### 目标

将个股月度收益拆解成多层残差，避免把行业或市场暴露误读为语义边共振。

### 残差层级

1. **Raw return**  
   原始月度收益，只用于参考。

2. **Market residual**  
   每月：
   ```text
   r_i,t - mean_market_return_t
   ```

3. **L1 residual**  
   每月每个申万一级行业：
   ```text
   r_i,t - mean_l1_return_{industry,t}
   ```

4. **L3 residual**  
   每月每个申万三级行业：
   ```text
   r_i,t - mean_l3_return_{industry,t}
   ```

5. **Size/liquidity residual**  
   每月横截面回归：
   ```text
   r_i,t = a_t + b1_t * log_total_mv_i + b2_t * log_amount_i + b3_t * turnover_i + eps_i,t
   ```

6. **Full neutral residual**  
   每月横截面回归：
   ```text
   r_i,t = industry_dummies + log_total_mv + log_amount + turnover + eps
   ```

### 推荐实现

为了减少工程复杂度，Phase 2.2 可以先使用“逐月横截面 OLS + numpy/pandas”实现，不需要引入复杂风险模型。

伪代码：

```python
def residualize_by_month(panel, y_col, x_cols, group_dummies=None):
    out = []
    for month, g in panel.groupby("month"):
        use = g[[y_col] + x_cols].replace([np.inf, -np.inf], np.nan).dropna()
        if len(use) < 100:
            continue
        X = use[x_cols].to_numpy("float64")
        X = np.column_stack([np.ones(len(X)), X])
        y = use[y_col].to_numpy("float64")
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        resid = y - X @ beta
        tmp = g.loc[use.index, ["stock_code", "month"]].copy()
        tmp["resid"] = resid.astype("float32")
        out.append(tmp)
    return pd.concat(out, ignore_index=True)
```

### 输出矩阵

```text
cache/semantic_graph/phase2_2/market_panel/matrices/months.json
cache/semantic_graph/phase2_2/market_panel/matrices/stock_codes.json
cache/semantic_graph/phase2_2/market_panel/matrices/monthly_return.npy
cache/semantic_graph/phase2_2/market_panel/matrices/ret_resid_market.npy
cache/semantic_graph/phase2_2/market_panel/matrices/ret_resid_l1.npy
cache/semantic_graph/phase2_2/market_panel/matrices/ret_resid_l3.npy
cache/semantic_graph/phase2_2/market_panel/matrices/ret_resid_size_liquidity.npy
cache/semantic_graph/phase2_2/market_panel/matrices/ret_resid_full_neutral.npy
cache/semantic_graph/phase2_2/market_panel/matrices/volatility.npy
cache/semantic_graph/phase2_2/market_panel/matrices/amount_z.npy
cache/semantic_graph/phase2_2/market_panel/matrices/turnover_z.npy
cache/semantic_graph/phase2_2/market_panel/matrices/extreme_up.npy
cache/semantic_graph/phase2_2/market_panel/matrices/extreme_down.npy
```

矩阵 shape 必须为：

```text
n_nodes x n_months
```

节点顺序必须与 `nodes.node_id` 一致，月份顺序必须写入 `months.json`。

## T2.2.5 边级 H5 市场共振计算

### 目标

对每个语义边和每个随机控制边，计算两端股票在时间序列上的市场共振。

### 边级指标

| 指标 | 说明 |
|---|---|
| `corr_raw_return` | 原始月收益相关 |
| `corr_resid_market` | 市场残差相关 |
| `corr_resid_l1` | 申万一级残差相关 |
| `corr_resid_l3` | 申万三级残差相关 |
| `corr_resid_size_liquidity` | 规模流动性残差相关 |
| `corr_resid_full_neutral` | 完整中性残差相关 |
| `corr_volatility` | 波动率相关 |
| `corr_amount_z` | 成交额 shock 相关 |
| `corr_turnover_z` | 换手 shock 相关 |
| `cooccur_extreme_up` | 极端上涨共现率 |
| `cooccur_extreme_down` | 极端下跌共现率 |
| `src_leads_dst_1m` | 源节点领先目标 1 月相关 |
| `dst_leads_src_1m` | 目标领先源节点 1 月相关 |
| `lead_lag_asymmetry_1m` | 两方向差异 |
| `common_months` | 两端共同有效月份数 |

### 向量化实现

不要对每条边循环做 pandas groupby。应将矩阵载入为 `float32`，对边分块计算。

```python
def pair_corr_for_edges(matrix, src, dst, min_common=24, block=200000):
    rows = []
    for lo in range(0, len(src), block):
        hi = min(lo + block, len(src))
        X = matrix[src[lo:hi]]
        Y = matrix[dst[lo:hi]]

        valid = np.isfinite(X) & np.isfinite(Y)
        n = valid.sum(axis=1)

        X0 = np.where(valid, X, 0.0)
        Y0 = np.where(valid, Y, 0.0)

        sx = X0.sum(axis=1)
        sy = Y0.sum(axis=1)
        mx = sx / np.maximum(n, 1)
        my = sy / np.maximum(n, 1)

        Xc = np.where(valid, X - mx[:, None], 0.0)
        Yc = np.where(valid, Y - my[:, None], 0.0)

        cov = (Xc * Yc).sum(axis=1)
        vx = (Xc * Xc).sum(axis=1)
        vy = (Yc * Yc).sum(axis=1)
        corr = cov / np.sqrt(np.maximum(vx * vy, 1e-12))
        corr[n < min_common] = np.nan

        rows.append(corr.astype("float32"))
    return np.concatenate(rows)
```

### lead-lag

对 lag=1/2/3：

```text
src_leads_dst_lag = corr(src[t], dst[t+lag])
dst_leads_src_lag = corr(dst[t], src[t+lag])
asymmetry = src_leads_dst_lag - dst_leads_src_lag
```

### 输出

每个 view 输出：

```text
cache/semantic_graph/views/{view}/{view_key}/phase2_2/market_behavior/edge_market_metrics.parquet
cache/semantic_graph/views/{view}/{view_key}/phase2_2/market_behavior/edge_market_metrics_by_layer.csv
cache/semantic_graph/views/{view}/{view_key}/phase2_2/market_behavior/edge_market_metrics_summary.json
outputs/reports/phase2_2/{view}/h5_market_resonance_report.md
```

### H5 通过标准

H5 不以单个指标通过，而以多层证据判断：

- residual correlation 高于 matched random；
- bootstrap CI 不跨 0；
- permutation p-value < 0.05；
- 不被 near duplicate 或 hub top 1% 驱动；
- 在至少两个 view 或多个 rank band 稳定；
- 在行业中性后仍保留部分增量。

如果只在 raw return 上显著，H5 不通过。
