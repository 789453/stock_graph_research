# PHASE2_3_TASKS_09_11_VISUALIZATION_AND_REPORTING

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## Task 09 — Generate high-value visualizations

### Goal

Replace low-value or redundant plots with a focused visualization set that explains data coverage, industry/fundamental structure, graph metrics, cross-industry bridges, time-series market behavior, and baseline residuals.

### Inputs

```text
node_feature_profile.parquet
edge_candidates_k100_repaired.parquet
edges_with_industry_fundamental.parquet
node_graph_metrics_k020.parquet
node_graph_metrics_k050.parquet
node_graph_metrics_k100.parquet
node_neighbor_fundamental_summary.parquet
baseline_residual_summary.parquet
node_market_annual_panel.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/plots/**/*.png
cache/semantic_graph/<run_id>/phase2_3/tables/table_06_plot_registry.csv
outputs/reports/phase2_3/PHASE2_3_VISUALIZATION_APPENDIX.md
```

### Plot style rules

1. Use English titles, axis labels, legends, and filenames by default.
2. Use Chinese stock names only if a CJK font is configured and verified.
3. Prefer readable top-N, heatmap, small-multiple, ridge/box/violin, and scatter-density charts.
4. Avoid label-heavy all-node scatterplots unless labels are suppressed.
5. Never show mechanical out-degree distribution as a main figure.
6. Every plot must have a caption answering: "what decision does this figure support?"

### Must-have plot groups

#### A. Data coverage and profile

- Node coverage by SW L1 industry.
- Missing-rate heatmap for PE/PB/market-cap/liquidity/basic snapshot fields.
- Market board distribution by SW L1.
- Listing age distribution by market board.

#### B. Rank and industry structure

- Same L1/L2/L3 ratio by rank 1..100.
- Same L3 ratio by exclusive rank band and by semantic view.
- Cross-L1 edge heatmap by source and target industry.
- Rank-band score distribution with industry overlap overlay.

#### C. Fundamentals

- Market-cap bucket composition by rank band.
- PE/PB distribution by SW L1.
- Edge-level absolute PB gap by rank band.
- Edge-level absolute log market-cap gap by rank band.
- Semantic neighbor median PB vs ego PB scatter-density.
- Semantic neighbor market-cap dispersion vs in-degree.

#### D. Graph structure

- In-degree distribution with hub threshold.
- Mutual ratio by rank band.
- In-degree vs neighbor L1 entropy.
- Bridge score vs weighted in-degree.
- Hub taxonomy scatter: in-degree, entropy, market cap, PB.
- Component size distribution for mutual graph.

#### E. Market time-series descriptive plots

- Annual return by hub decile.
- Annual volatility by bridge-score decile.
- Shock day count by graph metric decile.
- Time-series coverage by year and industry.
- Return/volatility gap by rank band.

#### F. Baselines and residuals

- Semantic vs random same-L3 ratio by rank band.
- Semantic vs matched random PB gap by rank band.
- Semantic residual score distribution by industry pair.
- Cross-industry bridge residual heatmap.
- Random baseline confidence interval plot.

### Plots to delete or move to appendix

Move these out of the main report unless they are improved:

- duplicate score histogram if another figure already shows score by rank;
- fixed out-degree distribution in a KNN graph;
- ego-neighbor examples with unreadable Chinese tofu boxes;
- PCA scatter without quantitative explanation;
- any plot whose legend has too many categories to read;
- any plot with more than 30 text labels overlapping.

---

## Task 10 — Generate report tables

### Goal

Create stable CSV tables used by the final Markdown report.

### Required tables

```text
table_01_data_coverage.csv
table_02_rank_band_industry_fundamental_summary.csv
table_03_graph_metric_summary.csv
table_04_cross_industry_bridge_summary.csv
table_05_baseline_residual_summary.csv
table_06_plot_registry.csv
```

### Table 02 required columns

```text
rank_band
edge_count
score_mean
score_median
mutual_ratio
same_l1_ratio
same_l2_ratio
same_l3_ratio
cross_l1_ratio
abs_log_total_mv_gap_mean
abs_pb_gap_median
abs_pe_ttm_gap_median
same_market_cap_bucket_ratio
same_pb_bucket_ratio
same_liquidity_bucket_ratio
return_gap_mean
volatility_gap_mean
amount_gap_mean
```

### Table 03 required columns

```text
k
node_count
edge_count
mutual_edge_count
mean_in_degree
p95_in_degree
p99_in_degree
hub_threshold
component_count_weak
largest_component_ratio_weak
component_count_mutual
largest_component_ratio_mutual
mean_neighbor_l1_entropy
mean_bridge_score
```

### Table 04 required columns

```text
src_l1_name
dst_l1_name
edge_count
mean_score
mutual_ratio
mean_bridge_score
mean_abs_pb_gap
mean_abs_log_total_mv_gap
top_src_stock
top_dst_stock
interpretation_note
```

### Table 05 required columns

```text
metric
semantic_value
global_random_mean
global_random_ci_low
global_random_ci_high
same_l3_random_mean
matched_random_mean
lift_vs_global
delta_vs_matched
interpretation
```

---

## Task 11 — Generate Phase 2.3 final report

### Output

```text
outputs/reports/phase2_3/PHASE2_3_RESEARCH_SUMMARY.md
```

### Required report structure

```text
# PHASE2_3_RESEARCH_SUMMARY

## 1. Executive conclusion
## 2. What changed from Phase 2.2
## 3. Data and cache audit
## 4. Edge construction and graph contract audit
## 5. Industry and fundamental enrichment
## 6. Graph-structure findings
## 7. Rank-band findings
## 8. Cross-industry bridge findings
## 9. Market behavior descriptive findings
## 10. Baseline and residual findings
## 11. Visualization interpretation
## 12. Remaining risks and invalid claims
## 13. Recommended next phase
```

### Required wording discipline

Allowed:

- "descriptive association"
- "candidate bridge"
- "graph-neighborhood concentration"
- "industry/fundamental residual"
- "hypothesis for further testing"

Forbidden unless later proven:

- "alpha"
- "predictive factor"
- "tradable edge"
- "causal chain"
- "market transmission proven"
- "GNN should be used"

### Report pass/fail criteria

The final report fails if:

- it claims H5 supported without residual time-series evidence;
- it treats cross-industry ratio alone as proof of supply-chain diffusion;
- it treats hub return difference as alpha;
- it hides invalid/negative results;
- it includes broken image links;
- it omits Tushare fundamental variables requested for Phase 2.3.
