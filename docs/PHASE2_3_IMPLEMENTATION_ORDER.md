# PHASE2_3_IMPLEMENTATION_ORDER

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## 1. Dependency graph

```text
T00 audit latest commit
  └── T01 repair edge candidates
        ├── T03 industry/basic snapshot profile
        │     └── T04 fundamental snapshot
        │           └── T05 market time-series panel
        ├── T06 graph metrics
        └── T07 baselines/residuals
              └── T08 neighbor fundamental statistics
                    ├── T09 plots
                    ├── T10 tables
                    └── T11 final report
```

## 2. Recommended implementation sequence

### Step 1: Freeze evidence base

Do not generate new plots or new research tables before the latest commit, input files, and existing output validity are audited.

### Step 2: Repair edge table

Every downstream task depends on a reliable edge candidate table.

### Step 3: Build node profile

Industry, basic snapshot, fundamental snapshot, and market time-series profile should be joined into a single `node_feature_profile.parquet`.

### Step 4: Join node profile to edges

Create `edges_with_industry_fundamental.parquet` by joining source and target node profiles.

### Step 5: Compute graph metrics

Compute graph metrics at K=20, K=50, and K=100. Store metrics separately by K.

### Step 6: Compute baselines

Only after node and edge profiles are reliable should random and matched baselines be generated.

### Step 7: Compute neighbor statistics

Use edge profiles and graph metrics to summarize each node's semantic neighborhood.

### Step 8: Generate plots

Generate fewer but stronger plots. Use plot registry.

### Step 9: Generate tables

Tables should be produced from cache, not from plot code.

### Step 10: Generate final report

The final report is a rendering of audited cache results, not a place to compute results.

## 3. Minimum viable Phase 2.3

If implementation time is limited, the minimum acceptable version is:

1. T00 audit;
2. T01 repaired edge table;
3. T03 industry/basic snapshot;
4. T04 fundamental snapshot;
5. T06 graph metrics;
6. T09 high-value plots;
7. T11 final report.

Do not skip T01.
