# PHASE2_3_PLOT_CATALOG

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## 1. Plot philosophy

Phase 2.3 should reduce the number of low-value plots while increasing the information density of retained charts.

A good Phase 2.3 plot should combine at least two of these dimensions:

- rank or score;
- industry hierarchy;
- fundamental variable;
- graph metric;
- time dimension;
- baseline comparison.

A plot that only shows one already-known distribution should be moved to appendix unless it is required for data quality.

## 2. Main report plot catalog

| ID | Filename | Source table | Purpose | Required visual form |
|---|---|---|---|---|
| P01 | `data_coverage__node_coverage_by_sw_l1.png` | `node_feature_profile.parquet` | Check industry coverage. | Horizontal bar chart. |
| P02 | `data_coverage__fundamental_missing_rate_heatmap.png` | `node_feature_profile.parquet` | Show PE/PB/market-cap/liquidity coverage. | Heatmap. |
| P03 | `industry__same_l1_l2_l3_ratio_by_rank.png` | `edges_with_industry_fundamental.parquet` | Show industry purity decay from rank 1 to 100. | Multi-line chart. |
| P04 | `industry__cross_l1_edge_heatmap_k100.png` | `edges_with_industry_fundamental.parquet` | Show cross-industry bridge map. | Heatmap, optionally normalized by source industry. |
| P05 | `fundamentals__market_cap_bucket_by_rank_band.png` | `edge_neighbor_fundamental_gaps.parquet` | Test whether semantic neighbors cluster by market cap. | Stacked bar chart. |
| P06 | `fundamentals__pb_gap_by_rank_band.png` | `edge_neighbor_fundamental_gaps.parquet` | Show valuation similarity or dispersion. | Box/violin plot. |
| P07 | `fundamentals__neighbor_pb_vs_ego_pb_density.png` | `node_neighbor_fundamental_summary.parquet` | Show neighborhood valuation relation. | Scatter-density or hexbin. |
| P08 | `graph_structure__in_degree_distribution_k100.png` | `node_graph_metrics_k100.parquet` | Show hub tail. | Histogram with p95/p99 threshold. |
| P09 | `graph_structure__in_degree_vs_l1_entropy.png` | `node_graph_metrics_k100.parquet` | Separate pure hubs from bridge hubs. | Scatter-density, size by market cap. |
| P10 | `graph_structure__bridge_score_vs_weighted_indegree.png` | `node_graph_metrics_k100.parquet` | Identify bridge/hub taxonomy. | Scatter-density with quadrant labels. |
| P11 | `graph_structure__mutual_ratio_by_rank_band.png` | `edge_candidates_k100_repaired.parquet` | Validate relation strength. | Bar + point chart. |
| P12 | `market_timeseries__annual_return_by_hub_decile.png` | `node_market_annual_panel.parquet` + graph metrics | Descriptive hub/return relation. | Boxplot by year and decile. |
| P13 | `market_timeseries__shock_count_by_bridge_decile.png` | annual panel + graph metrics | Explore shock exposure. | Bar/box chart. |
| P14 | `baselines__same_l3_semantic_vs_random_by_rank_band.png` | baseline summary | Compare semantic graph against random baselines. | Point-range with CI. |
| P15 | `baselines__pb_gap_semantic_vs_matched_random.png` | baseline summary | See if valuation similarity exceeds matched random. | Point-range with CI. |
| P16 | `baselines__semantic_residual_score_by_industry_pair.png` | residual summary | Find industry pairs with excess semantic affinity. | Heatmap. |
| P17 | `examples__top_bridge_edges_table.png` | bridge summary table | Human inspectability. | Rendered table or Markdown table, not huge network plot. |
| P18 | `examples__hub_taxonomy_top_examples.png` | hub taxonomy table | Show hub types. | Small multiples or table. |

## 3. Appendix-only plots

| Plot type | Reason |
|---|---|
| Raw score histogram only | Useful sanity check but not enough for main report. |
| PCA scatter with all L1 colors | Often visually overloaded; keep only if paired with quantitative interpretation. |
| Ego neighbor bar chart for arbitrary examples | Useful for debugging, not main evidence. |
| Fixed out-degree distribution | Mechanical artifact of kNN. |
| Giant labeled network graph | Usually unreadable for 5,502 nodes. |

## 4. Aesthetic requirements

- Main figure size: at least 12 x 7 inches or equivalent high-resolution output.
- Use tight layout and readable fonts.
- Avoid more than 12 legend categories in a main plot.
- For industry heatmaps, group small industries into `Other` only for visualization; never alter source data.
- For valuation variables, use winsorized display columns but keep raw values available.
- Use log scale for market cap and amount where appropriate.
- Include data window in subtitle, for example: `Market window: 2018-01-01 to 2026-04-23`.
- Include `Static semantic graph; current SW classification` where applicable.

## 5. Plot registry schema

```text
plot_id
plot_path
plot_title
source_table
source_rows
created_at
script
parameters_json
caption
main_or_appendix
status
```

Status values:

```text
generated
skipped_no_data
failed
deprecated
```
