# PHASE2_3_TASKS_03_05_TUSHARE_DATA_ENRICHMENT

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## Task 03 — Build Tushare industry and basic snapshot profile

### Goal

Join semantic nodes to current SW industry membership and Tushare basic stock snapshot.

This task fixes the current underuse of `docs/tushare-data-README.md` data, especially:

- `stock_sw_member`
- `stock_basic_snapshot`

### Inputs

```text
cache/semantic_graph/<run_id>/phase2_3/edge_metrics/edge_candidates_k100_repaired.parquet
semantic nodes table
/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet
/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_basic_snapshot.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_industry_profile.parquet
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_basic_snapshot_profile.parquet
cache/semantic_graph/<run_id>/phase2_3/tables/table_01_data_coverage.csv
cache/semantic_graph/<run_id>/phase2_3/manifests/t03_industry_profile_manifest.json
```

### Required fields from `stock_sw_member`

```text
ts_code
name
l1_code
l1_name
l2_code
l2_name
l3_code
l3_name
in_date
```

### Required fields from `stock_basic_snapshot`

```text
ts_code
symbol
name
area
industry
fullname
market
exchange
list_status
list_date
delist_date
is_hs
act_name
act_ent_type
```

### Required transformations

1. Normalize stock key to `ts_code`.
2. Deduplicate `stock_sw_member`:
   - if multiple records exist for one `ts_code`, choose the latest `in_date`;
   - retain `sw_member_duplicate_count`.
3. Build `listing_age_years`:
   - use `snapshot_trade_date - list_date`;
   - null if `list_date` invalid.
4. Create categorical groups:
   - `board_group`: main board, ChiNext, STAR, BSE, CDR, unknown;
   - `region_group`: by `area`;
   - `ownership_group`: from `act_ent_type` where available.

### Required validation

- node coverage by `stock_sw_member` >= 95%;
- node coverage by `stock_basic_snapshot` >= 98%;
- no duplicated `node_id`;
- no many-to-many join explosion;
- report all missing stocks.

### Research outputs

- coverage by market board;
- coverage by SW L1/L2/L3;
- distribution of listing age;
- semantic graph node count by industry.

---

## Task 04 — Build fundamental snapshot from `stock_daily_basic`

### Goal

Create a node-level fundamental profile using valuation, market cap, share, and liquidity variables.

### Inputs

```text
/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet
node_industry_profile.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_fundamental_snapshot.parquet
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_feature_profile.parquet
cache/semantic_graph/<run_id>/phase2_3/tables/table_02_rank_band_industry_fundamental_summary.csv
cache/semantic_graph/<run_id>/phase2_3/manifests/t04_fundamental_profile_manifest.json
```

### Required fields

```text
ts_code
trade_date
close
turnover_rate
turnover_rate_f
volume_ratio
pe
pe_ttm
pb
ps
ps_ttm
dv_ratio
dv_ttm
total_share
float_share
free_share
total_mv
circ_mv
```

### Snapshot rule

Use the latest valid trade date at or before the project market end date, e.g. `20260423`.

For each stock:

1. prefer latest non-null `total_mv`, `circ_mv`, `pe_ttm`, `pb`;
2. if `pe_ttm <= 0`, keep raw value but create `pe_ttm_valid = false`;
3. if `pb <= 0`, keep raw value but create `pb_valid = false`;
4. winsorize only derived visualization variables, never overwrite raw columns.

### Derived variables

```text
log_total_mv
log_circ_mv
market_cap_bucket
circ_mv_bucket
pe_ttm_bucket
pb_bucket
turnover_bucket
valuation_style
```

Suggested `valuation_style`:

```text
large_low_pb
large_high_pb
small_low_pb
small_high_pb
negative_or_invalid_pe
normal
```

### Validation

- node coverage >= 95%;
- `total_mv` non-null coverage >= 90%;
- `pb` non-null coverage >= 80%;
- report negative PE and extreme PE counts;
- no division by zero in log variables.

### Important interpretation rule

Do not treat PE/PB as causal drivers. They are descriptive controls and graph-neighborhood descriptors.

---

## Task 05 — Build market time-series panel from `stock_daily`

### Goal

Create robust historical return, volatility, liquidity, and shock metrics for later graph analysis and visualization.

### Inputs

```text
/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily.parquet
node_feature_profile.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_market_timeseries_panel.parquet
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_market_annual_panel.parquet
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_feature_profile.parquet
cache/semantic_graph/<run_id>/phase2_3/manifests/t05_market_timeseries_manifest.json
```

### Required fields from `stock_daily`

```text
ts_code
trade_date
open
high
low
close
pre_close
pct_chg
vol
amount
```

### Required metrics

Node-level snapshot metrics:

```text
ret_20d
ret_60d
ret_252d
volatility_20d
volatility_60d
volatility_252d
amount_20d_avg
amount_60d_avg
vol_20d_avg
vol_60d_avg
max_drawdown_252d
shock_up_count_252d
shock_down_count_252d
```

Annual panel metrics:

```text
ts_code
year
trading_days
annual_return
annual_volatility
annual_amount_avg
annual_turnover_proxy
max_daily_return
min_daily_return
up_shock_days
down_shock_days
```

### Shock definitions

Use descriptive thresholds:

```text
up_shock: pct_chg >= 7
down_shock: pct_chg <= -7
extreme_abs_return: abs(pct_chg) >= 7
volume_shock: amount >= rolling_60d_amount_median * 3
```

Do not call these alpha signals.

### Validation

- date coverage by stock;
- missing close/amount rates;
- outlier count;
- suspended-day handling;
- annual panel has no impossible years.

### Performance implementation

Use DuckDB for column selection and date filtering. Avoid loading all columns into memory.

Example logic:

```sql
SELECT ts_code, trade_date, close, pct_chg, vol, amount
FROM read_parquet('stock_daily.parquet')
WHERE trade_date BETWEEN '20180101' AND '20260423'
  AND ts_code IN (...)
```
