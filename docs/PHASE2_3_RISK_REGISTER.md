# PHASE2_3_RISK_REGISTER

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## 1. Major correctness risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| Reverse score or mutual edge logic is wrong | Corrupts hub, bridge, mutual graph, and score statistics. | Use reverse self-merge and explicit tests. |
| Ambiguous rank-band names | Causes misleading interpretation of top-K vs rank interval. | Use `rank_001_005` and `top_001_005` style names. |
| Industry membership is current, not historical | Can overstate historical explanatory value. | Label every industry plot as current SW classification. |
| Stock code join mismatch | Silently drops nodes or creates wrong joins. | Canonical `ts_code`, coverage audit, no many-to-many join. |
| PE/PB extreme or invalid values | Distorts charts and summaries. | Preserve raw values, use winsorized display variables, report invalid counts. |
| Plot paths broken | Report appears complete but visual evidence missing. | Plot registry and Markdown link validator. |
| Low-value plots crowd out evidence | Readers confuse diagnostics with research proof. | Main/appendix plot classification. |
| Hub return difference overinterpreted | May be industry/size/time-period artifact. | No alpha claim; add matched baseline and decile plots. |
| Cross-industry ratio overinterpreted | Cross-industry does not prove supply-chain diffusion. | Add residual heatmaps and manual bridge samples. |
| H5/H6 overclaimed | Market co-movement requires time-series residual evidence. | Conservative wording and report consistency tests. |

## 2. Data insufficiency risks

### Fundamental snapshot may be stale or single-date biased

Mitigation:

- store `snapshot_trade_date`;
- optionally compute quarterly or annual averages;
- do not compare single-date PE/PB to long historical returns without warning.

### `stock_sw_member` may have duplicates

Mitigation:

- choose latest `in_date`;
- store duplicate count;
- report stocks with multiple memberships.

### `stock_basic_snapshot` may include delisted or inactive stocks

Mitigation:

- keep `list_status`;
- analyze active and inactive separately if needed;
- do not silently drop delisted stocks without reporting.

### Static semantic graph vs historical market panel

Mitigation:

- every market-behavior chart should say static semantic graph and historical market window;
- avoid causal claims.

## 3. Visualization risks

### Unreadable Chinese labels

Mitigation:

- default to English labels or stock codes;
- only use Chinese names when CJK font is configured.

### Too many categories

Mitigation:

- top-N plus Other for visualization only;
- preserve raw categories in data.

### Misleading color scale

Mitigation:

- use centered color scale for residuals;
- use sequential scale for counts/ratios;
- annotate normalizations.

## 4. Recommended manual inspection samples

Produce CSVs for manual review:

```text
top_100_near_duplicate_edges.csv
top_100_cross_l1_bridge_edges.csv
top_100_hubs_by_indegree.csv
top_100_hubs_by_bridge_score.csv
top_100_high_residual_edges.csv
top_100_large_fundamental_gap_high_score_edges.csv
```

Each sample should include:

```text
src_ts_code
src_name
dst_ts_code
dst_name
score
rank
is_mutual
src_l1_name
dst_l1_name
src_l3_name
dst_l3_name
src_total_mv
dst_total_mv
src_pe_ttm
dst_pe_ttm
src_pb
dst_pb
reason_for_selection
```

## 5. Red-line claims to avoid

Do not write:

- "semantic graph predicts returns";
- "bridge edges prove theme transmission";
- "hub stocks have alpha";
- "GNN is the next required step";
- "H6 is validated" unless time-series lead-lag evidence is added.

Acceptable alternatives:

- "semantic graph identifies candidate relationships";
- "cross-industry bridge edges are candidates for human review";
- "hub nodes show descriptive differences that require matched controls";
- "H6 remains an open hypothesis for later event/time-series tests".
