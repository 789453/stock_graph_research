# PHASE2_3_RESEARCH_MASTER_SPEC

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## 1. Phase 2.3 positioning

Phase 2.3 should be treated as a "research infrastructure hardening + explanatory statistics expansion" phase.

It should not be marketed as Phase 3, because Phase 3 would imply a move toward predictive modeling, lead-lag testing, event studies, graph factors, or strategy research. Phase 2.3 is still pre-alpha. It exists to make sure that the semantic graph, industry/fundamental enrichment, graph structure metrics, and visualization layer are trustworthy enough to support later research.

## 2. Core research questions

### Q1. What does the semantic graph encode after controlling for industry, market cap, liquidity, and basic valuation?

Evidence required:

- same L1/L2/L3 ratio by exclusive rank band and cumulative top-K;
- comparison against global random, same-L3 random, same-size random, same-liquidity random, same-market-board random, and matched fundamental random;
- score and rank-band behavior after stratifying by industry and market-cap bucket;
- edge-level residual statistics: semantic score minus expected score under industry/fundamental domain.

### Q2. Do cross-industry semantic edges have interpretable structure?

Evidence required:

- cross-L1 and cross-L2 edge matrices;
- top cross-industry bridge pairs by score, mutual status, centrality, and industry entropy;
- bridge nodes with high cross-industry neighbor entropy but non-generic text;
- manual sample table for the strongest and most suspicious bridge edges.

### Q3. How do fundamental variables vary across semantic neighborhoods?

Evidence required:

- neighbor dispersion of total market value, circ market value, PE, PE TTM, PB, PS, turnover, amount, board, listing age, current Tushare industry, and SW L3 industry;
- comparison of ego node value vs neighbor median value;
- distribution of absolute valuation gap between source and target nodes by rank band;
- graph-neighborhood concentration by valuation buckets.

### Q4. Which graph structure features are meaningful and which are merely mechanical artifacts of kNN?

Evidence required:

- out-degree is fixed by K and should not be overinterpreted;
- in-degree, mutual degree, weighted in-degree, cross-industry in-degree, local clustering, component membership, PageRank/eigenvector-like centrality, bridge score, and entropy are meaningful;
- graph metrics must be computed separately for `k=20`, `k=50`, `k=100`, and for mutual-only graph where possible;
- the report must distinguish directed kNN graph, undirected mutual graph, weighted graph, and filtered research graph.

### Q5. Which plots are necessary?

High-value charts should answer one of these:

- Is the graph structurally non-random?
- Is it industry/fundamental/market-cap driven?
- Are cross-industry bridges interpretable?
- Are semantic neighborhoods fundamentally homogeneous or heterogeneous?
- Are time-series market behavior and graph features related descriptively?
- What should a human researcher inspect next?

Low-value charts should be deleted or moved to appendix if they only repeat score histograms, show mechanical out-degree, or produce unreadable label-heavy ego plots.

## 3. Hypothesis table for Phase 2.3

| Hypothesis | Phase 2.3 expected status | Required evidence |
|---|---|---|
| H1: Semantic graph is not only industry replication | Partial, not full | Industry lift plus residual/cross-industry structure. |
| H2: Rank bands represent different relationship types | Likely supported | Rank-band score, same-industry ratio, valuation gap, bridge ratio, mutual ratio. |
| H3: Hubs have multiple types | Must be refined | Hub taxonomy by industry entropy, in-degree, mutual degree, valuation, market cap, text duplicate risk. |
| H4: Cross-industry bridges are candidate supply-chain/theme links | Candidate only | Cross-industry edge matrix, bridge samples, residual baseline, no causal claim. |
| H5: Semantic graph explains market co-movement | Not proven | Needs residual return correlation, volatility shock co-occurrence, and matched random baselines. |
| H6: Medium-rank edges may capture theme diffusion better than strongest edges | Open | Needs rank_021_050 and rank_051_100 shock/time-series comparison. |

## 4. Required data sources

### Semantic graph inputs

```text
a_share_semantic_dataset/
├── parquet/records-all.parquet
└── npy/<view>/<view>-all.npy
```

At minimum Phase 2.3 should run on the current best view from Phase 2.2. If multiple views are already available, Phase 2.3 should support:

- `application_scenarios_json`
- `main_business_detail`
- `chain_text`
- `theme_text`
- `full_text`

The implementation must not assume all views exist. It should discover views from config and fail clearly when a declared view is missing.

### Tushare silver inputs

```text
/mnt/d/Trading/data_ever_26_3_14/data/silver/
├── stock_sw_member.parquet
├── stock_daily_basic.parquet
├── stock_daily.parquet
└── stock_basic_snapshot.parquet
```

Required fields:

- `stock_sw_member`: `ts_code`, `l1_code`, `l1_name`, `l2_code`, `l2_name`, `l3_code`, `l3_name`, `in_date`, `name`
- `stock_daily_basic`: `ts_code`, `trade_date`, `pe`, `pe_ttm`, `pb`, `ps`, `ps_ttm`, `turnover_rate`, `turnover_rate_f`, `volume_ratio`, `total_mv`, `circ_mv`, `total_share`, `float_share`, `free_share`
- `stock_daily`: `ts_code`, `trade_date`, `open`, `high`, `low`, `close`, `pre_close`, `pct_chg`, `vol`, `amount`
- `stock_basic_snapshot`: `ts_code`, `symbol`, `name`, `area`, `industry`, `market`, `exchange`, `list_status`, `list_date`, `delist_date`, `is_hs`, `act_name`, `act_ent_type`

## 5. Main outputs

```text
cache/semantic_graph/<run_id>/phase2_3/
├── manifests/
├── audits/
├── data_profiles/
├── graph_metrics/
├── edge_metrics/
├── baselines/
├── plots/
├── tables/
└── reports/
```

The final report should be:

```text
outputs/reports/phase2_3/PHASE2_3_RESEARCH_SUMMARY.md
```

It must explicitly separate:

1. confirmed engineering facts;
2. descriptive graph/fundamental facts;
3. candidate research interpretations;
4. unproven claims and next-step hypotheses.
