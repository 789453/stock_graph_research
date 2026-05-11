# PHASE2_3_CACHE_SCHEMA_AND_OUTPUT_CONTRACTS

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## 1. Design principle

Every Phase 2.3 artifact must be reproducible from cached inputs and must be explainable by a manifest.

A file without a manifest entry is not allowed in the final report.

## 2. Directory layout

```text
cache/semantic_graph/<run_id>/phase2_3/
├── manifests/
│   ├── phase2_3_run_manifest.json
│   ├── t00_input_audit_manifest.json
│   ├── t01_edge_repair_manifest.json
│   ├── t03_industry_profile_manifest.json
│   ├── t04_fundamental_profile_manifest.json
│   ├── t06_graph_metrics_manifest.json
│   ├── t07_baseline_residual_manifest.json
│   ├── t09_plot_manifest.json
│   └── t11_final_report_manifest.json
├── audits/
│   ├── latest_commit_audit.json
│   ├── input_file_fingerprints.json
│   ├── row_alignment_audit.json
│   ├── self_edge_audit.csv
│   ├── near_duplicate_edge_audit.csv
│   └── report_consistency_audit.json
├── data_profiles/
│   ├── node_industry_profile.parquet
│   ├── node_basic_snapshot_profile.parquet
│   ├── node_fundamental_snapshot.parquet
│   ├── node_market_timeseries_panel.parquet
│   ├── node_market_annual_panel.parquet
│   └── node_feature_profile.parquet
├── graph_metrics/
│   ├── node_graph_metrics_k020.parquet
│   ├── node_graph_metrics_k050.parquet
│   ├── node_graph_metrics_k100.parquet
│   ├── component_summary_k020.json
│   ├── component_summary_k050.json
│   ├── component_summary_k100.json
│   └── graph_metric_summary.json
├── edge_metrics/
│   ├── edge_candidates_k100_repaired.parquet
│   ├── edges_with_industry_fundamental.parquet
│   ├── edge_neighbor_fundamental_gaps.parquet
│   ├── edge_market_behavior_panel.parquet
│   └── edge_metric_summary.json
├── baselines/
│   ├── random_edge_baselines.parquet
│   ├── matched_random_edge_baselines.parquet
│   ├── industry_residual_summary.parquet
│   ├── fundamental_residual_summary.parquet
│   └── baseline_summary.json
├── plots/
│   ├── data_coverage/
│   ├── industry/
│   ├── fundamentals/
│   ├── graph_structure/
│   ├── market_timeseries/
│   ├── baselines/
│   └── examples/
├── tables/
│   ├── table_01_data_coverage.csv
│   ├── table_02_rank_band_industry_fundamental_summary.csv
│   ├── table_03_graph_metric_summary.csv
│   ├── table_04_cross_industry_bridge_summary.csv
│   ├── table_05_baseline_residual_summary.csv
│   └── table_06_plot_registry.csv
└── reports/
    ├── PHASE2_3_RESEARCH_SUMMARY.md
    ├── PHASE2_3_ENGINEERING_AUDIT.md
    └── PHASE2_3_VISUALIZATION_APPENDIX.md
```

## 3. Manifest schema

Every task manifest must include:

```json
{
  "phase": "phase2_3",
  "task_id": "t04",
  "task_name": "build_tushare_fundamental_profile",
  "status": "success",
  "created_at": "ISO-8601 timestamp",
  "git": {
    "repo": "789453/stock_graph_research",
    "branch": "main",
    "commit_sha": "required",
    "commit_message": "required"
  },
  "inputs": [
    {
      "path": "string",
      "exists": true,
      "rows": 0,
      "columns": [],
      "fingerprint": "sha256 or fast hash",
      "min_date": "YYYYMMDD or null",
      "max_date": "YYYYMMDD or null"
    }
  ],
  "outputs": [
    {
      "path": "string",
      "rows": 0,
      "columns": [],
      "fingerprint": "sha256 or fast hash"
    }
  ],
  "parameters": {},
  "validation": {
    "row_count_ok": true,
    "null_rate_ok": true,
    "key_uniqueness_ok": true,
    "self_edge_count": 0,
    "warnings": []
  }
}
```

## 4. Key conventions

### 4.1 Stock code key

Use `ts_code` as the canonical market-data key. Semantic records may contain `stock_code`; convert and validate it to `ts_code`.

Allowed formats:

```text
000001.SZ
600000.SH
```

Do not join on raw six-digit `symbol` unless the exchange suffix has been reconstructed and audited.

### 4.2 Dates

Use string `YYYYMMDD` for raw Tushare `trade_date`; create `date` as parsed date only for time-series transformations.

Required date columns:

- `snapshot_trade_date`: the chosen latest trade date for fundamental snapshot;
- `window_start`;
- `window_end`;
- `asof_date` for semantic records;
- `list_date` for listing age.

### 4.3 Rank bands

Use both exclusive and cumulative forms, never ambiguous names:

Exclusive:

```text
rank_001_005
rank_006_010
rank_011_020
rank_021_050
rank_051_100
```

Cumulative:

```text
top_001_005
top_001_010
top_001_020
top_001_050
top_001_100
```

The final report must never use `core`, `strong`, `stable`, `context`, or `extended` unless those labels are explicitly mapped to exclusive rank ranges.

### 4.4 Required edge columns

`edge_candidates_k100_repaired.parquet` must contain:

```text
src_node_id
dst_node_id
src_ts_code
dst_ts_code
src_name
dst_name
rank
score
exclusive_rank_band
top_005
top_010
top_020
top_050
top_100
reverse_rank
reverse_score
is_mutual
score_mean_if_mutual
src_record_id
dst_record_id
```

Validation:

- `src_node_id != dst_node_id`;
- `src_ts_code != dst_ts_code`;
- `src_record_id != dst_record_id`;
- `rank in [1, 100]`;
- `score` finite;
- if `is_mutual == true`, `reverse_rank` and `reverse_score` are not null;
- if `is_mutual == false`, `score_mean_if_mutual` is null or equals `score` only if explicitly defined.

### 4.5 Required node profile columns

`node_feature_profile.parquet` must contain:

```text
node_id
record_id
ts_code
stock_name
asof_date
l1_code
l1_name
l2_code
l2_name
l3_code
l3_name
basic_industry
area
market
exchange
list_status
list_date
listing_age_years
is_hs
act_ent_type
snapshot_trade_date
close
pe
pe_ttm
pb
ps
ps_ttm
turnover_rate
turnover_rate_f
volume_ratio
total_mv
circ_mv
amount_20d_avg
vol_20d_avg
ret_20d
ret_60d
ret_252d
volatility_60d
market_cap_bucket
circ_mv_bucket
liquidity_bucket
pe_bucket
pb_bucket
```

## 5. Plot output rules

Each plot must have:

- English filename;
- English chart title and axis labels by default;
- optional Chinese labels only if CJK font is explicitly configured;
- a row in `table_06_plot_registry.csv`;
- a caption in `PHASE2_3_VISUALIZATION_APPENDIX.md`;
- source data path recorded in manifest.

Plot filename pattern:

```text
<domain>__<short_description>__<view_or_k>.<png|svg>
```

Example:

```text
industry__same_l3_ratio_by_rank__application_scenarios_json.png
fundamentals__pe_pb_neighbor_gap_by_rank_band__k100.png
graph_structure__in_degree_vs_industry_entropy__k100.png
market_timeseries__annual_return_by_hub_decile__2018_2026.png
```

## 6. Report consistency checks

Fail the report if:

- H5 is marked both supported and rejected;
- any required metric is `N/A` when its source table exists;
- `core/strong/stable` appear without explicit mapping;
- a figure path in Markdown does not exist;
- a plot was generated but not registered;
- a report table is older than the input cache;
- row counts differ across node-level tables without a documented reason;
- `industry_comparison` is empty;
- random baseline seed is missing.
