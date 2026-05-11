# PHASE2_3_TASKS_06_08_GRAPH_METRICS_AND_BASELINES

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## Task 06 — Compute graph structure metrics

### Goal

Move beyond simple degree distribution and produce graph metrics that can support industry, fundamental, and bridge interpretation.

### Inputs

```text
edge_candidates_k100_repaired.parquet
node_feature_profile.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/graph_metrics/node_graph_metrics_k020.parquet
cache/semantic_graph/<run_id>/phase2_3/graph_metrics/node_graph_metrics_k050.parquet
cache/semantic_graph/<run_id>/phase2_3/graph_metrics/node_graph_metrics_k100.parquet
cache/semantic_graph/<run_id>/phase2_3/graph_metrics/component_summary_k020.json
cache/semantic_graph/<run_id>/phase2_3/graph_metrics/component_summary_k050.json
cache/semantic_graph/<run_id>/phase2_3/graph_metrics/component_summary_k100.json
cache/semantic_graph/<run_id>/phase2_3/tables/table_03_graph_metric_summary.csv
```

### Required metrics

For each K in 20, 50, 100:

```text
in_degree
out_degree
mutual_in_degree
mutual_out_degree
weighted_in_degree_sum
weighted_in_degree_mean
weighted_out_degree_sum
weighted_out_degree_mean
cross_l1_in_degree
cross_l2_in_degree
cross_l3_in_degree
same_l3_in_degree
neighbor_l1_entropy
neighbor_l2_entropy
neighbor_l3_entropy
neighbor_market_cap_entropy
neighbor_pb_entropy
bridge_score
hub_score
local_reciprocity
local_score_dispersion
```

Optional but useful:

```text
pagerank
weighted_pagerank
betweenness_approx
eigenvector_centrality
community_id_louvain_or_leiden
community_size
```

### Bridge score definition

A simple first version:

```text
bridge_score =
  normalized_in_degree
  * neighbor_l1_entropy
  * cross_l1_neighbor_ratio
  * mean_edge_score
```

Also store components separately. Do not rely only on the composite score.

### Hub score definition

```text
hub_score =
  rank_percentile(in_degree)
  + rank_percentile(weighted_in_degree_sum)
  + rank_percentile(mutual_in_degree)
```

### Validation

- out-degree should equal K in the directed kNN graph;
- out-degree should not be interpreted as a discovered metric;
- metric values are finite;
- entropy values are non-negative;
- component counts are sensible;
- strongly connected and weakly connected components are reported separately for directed graph.

---

## Task 07 — Compute industry/fundamental baselines and residuals

### Goal

Quantify how much of semantic graph structure is explained by industry and fundamentals.

### Inputs

```text
edges_with_industry_fundamental.parquet
node_feature_profile.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/baselines/random_edge_baselines.parquet
cache/semantic_graph/<run_id>/phase2_3/baselines/matched_random_edge_baselines.parquet
cache/semantic_graph/<run_id>/phase2_3/baselines/industry_residual_summary.parquet
cache/semantic_graph/<run_id>/phase2_3/baselines/fundamental_residual_summary.parquet
cache/semantic_graph/<run_id>/phase2_3/tables/table_05_baseline_residual_summary.csv
```

### Baseline types

1. `global_random`: random target from all stocks.
2. `same_l3_random`: random target from same SW L3.
3. `same_l2_random`: random target from same SW L2.
4. `cross_l1_random`: random target from different SW L1.
5. `same_market_cap_bucket_random`: random target from same market-cap bucket.
6. `same_liquidity_bucket_random`: random target from same liquidity bucket.
7. `same_l3_and_cap_bucket_random`: random target matched on both L3 and cap bucket.
8. `same_board_random`: random target from same market board.
9. `fundamental_matched_random`: random target matched on cap bucket, PB bucket, and turnover bucket.

### Required statistics by rank band

```text
same_l1_ratio
same_l2_ratio
same_l3_ratio
cross_l1_ratio
score_mean
score_median
score_std
abs_log_total_mv_gap_mean
abs_log_circ_mv_gap_mean
abs_pb_gap_mean
abs_pe_ttm_gap_median
abs_turnover_gap_mean
return_corr_mean
volatility_gap_mean
amount_gap_mean
```

### Residual score concept

For edge `i -> j`, estimate expected score from industry/fundamental domain:

```text
expected_score = mean(score | src_l3, dst_l3, src_cap_bucket, dst_cap_bucket, rank_band)
semantic_residual_score = score - expected_score
```

This is not a causal residual. It is a descriptive residual against grouped baseline expectation.

### Validation

- use fixed random seed;
- store number of random repetitions;
- store confidence interval if repeated sampling is used;
- do not compare a constrained random baseline on its constrained dimension as if it were an empirical discovery;
- example: `same_l3_random` has same-L3 ratio equal to 1 by construction.

---

## Task 08 — Compute neighbor fundamental statistics

### Goal

Describe each node's semantic neighborhood in terms of valuation, size, liquidity, industry, market board, and graph structure.

### Inputs

```text
edge_candidates_k100_repaired.parquet
node_feature_profile.parquet
node_graph_metrics_k100.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/edge_metrics/edge_neighbor_fundamental_gaps.parquet
cache/semantic_graph/<run_id>/phase2_3/data_profiles/node_neighbor_fundamental_summary.parquet
cache/semantic_graph/<run_id>/phase2_3/tables/table_04_cross_industry_bridge_summary.csv
```

### Edge-level gap columns

```text
abs_log_total_mv_gap
abs_log_circ_mv_gap
abs_pe_ttm_gap
abs_pb_gap
abs_ps_ttm_gap
abs_turnover_gap
same_market_cap_bucket
same_pb_bucket
same_pe_bucket
same_board
same_area
same_actual_industry
same_sw_l1
same_sw_l2
same_sw_l3
```

### Node-level neighborhood columns

```text
neighbor_total_mv_median
neighbor_total_mv_iqr
neighbor_pb_median
neighbor_pb_iqr
neighbor_pe_ttm_median
neighbor_pe_ttm_valid_ratio
neighbor_turnover_median
neighbor_amount_median
neighbor_l1_mode
neighbor_l1_entropy
neighbor_l3_mode
neighbor_l3_entropy
neighbor_board_entropy
neighbor_cross_l1_ratio
neighbor_cross_l3_ratio
neighbor_large_cap_ratio
neighbor_low_pb_ratio
neighbor_invalid_pe_ratio
```

### Research uses

These statistics should support questions such as:

- Do semantic hubs mainly connect large caps?
- Are cross-industry bridges valuation-homogeneous or valuation-heterogeneous?
- Are theme-like neighborhoods high PB/high PE clusters?
- Do rank 21-50 edges have larger industry dispersion but similar business/fundamental profiles?
- Do mutual edges have lower fundamental dispersion than non-mutual edges?

### Validation

- node count equals semantic node count;
- for K=100, each node should have up to 100 neighbors unless filtered;
- null rates are reported;
- invalid PE/PB is handled explicitly, not silently dropped.
