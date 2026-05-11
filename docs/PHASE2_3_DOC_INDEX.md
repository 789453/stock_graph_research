# PHASE2_3_DOC_INDEX

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## 1. Why Phase 2.3 exists

Phase 2.3 is a consolidation and expansion phase after `phase2.2 mostly completed but plots not`.

Its primary purpose is not to add a flashy model. Its purpose is to make the project harder to misread and easier to extend:

1. repair remaining correctness risks in edge construction, market/fundamental alignment, rank-band semantics, cache contracts, report consistency, and plotting;
2. enrich the graph research with Tushare-derived industry and fundamental data, especially `stock_sw_member`, `stock_daily_basic`, `stock_daily`, and `stock_basic_snapshot`;
3. expand graph-structure metrics beyond degree/hub counts, including component structure, reciprocity, industry assortativity, weighted centrality, local density, bridge score, cross-industry entropy, and neighborhood fundamental dispersion;
4. replace low-value or redundant plots with fewer but more informative, multi-feature, cross-industry, time-series, and graph-structure visualizations;
5. define a strict input/output contract so Phase 2.3 can be implemented as a set of repeatable scripts and tests.

## 2. Document map

| File | Purpose |
|---|---|
| `PHASE2_3_RESEARCH_MASTER_SPEC.md` | Master research design, hypotheses, evidence standards, and non-goals. |
| `PHASE2_3_CACHE_SCHEMA_AND_OUTPUT_CONTRACTS.md` | Exact cache layout, manifest schema, input/output file contracts, naming rules, and validation rules. |
| `PHASE2_3_TASKS_00_02_CODE_REPAIR_AND_CONTRACTS.md` | Priority repairs: commit audit, edge correctness, rank-band semantics, alignment, plotting defects, report consistency. |
| `PHASE2_3_TASKS_03_05_TUSHARE_DATA_ENRICHMENT.md` | Build industry/fundamental/market profile tables from `stock_sw_member`, `stock_daily_basic`, `stock_daily`, `stock_basic_snapshot`. |
| `PHASE2_3_TASKS_06_08_GRAPH_METRICS_AND_BASELINES.md` | Graph metrics, null models, industry/fundamental baselines, edge-level residual statistics. |
| `PHASE2_3_TASKS_09_11_VISUALIZATION_AND_REPORTING.md` | High-value visualization suite, plot aesthetics, plot deletion list, report generation. |
| `PHASE2_3_PLOT_CATALOG.md` | The exact chart catalog: keep/delete/new plots, required columns, recommended encodings, output paths. |
| `PHASE2_3_TEST_EXECUTION_CHECKLIST.md` | Tests and execution checklist for code, data, cache, metrics, plots, and final report. |
| `PHASE2_3_IMPLEMENTATION_ORDER.md` | Recommended implementation order and dependency graph. |
| `PHASE2_3_RISK_REGISTER.md` | Known risks, likely hidden bugs, and mitigation rules. |

## 3. Recommended script sequence

Phase 2.3 should be implemented as scripts under `scripts/phase2_3/`:

```text
scripts/phase2_3/
├── 00_audit_latest_commit_and_inputs.py
├── 01_repair_edge_candidate_contracts.py
├── 02_validate_cache_and_report_consistency.py
├── 03_build_tushare_industry_profile.py
├── 04_build_tushare_fundamental_profile.py
├── 05_build_market_time_series_panel.py
├── 06_compute_graph_structure_metrics.py
├── 07_compute_baseline_and_residual_metrics.py
├── 08_compute_neighbor_fundamental_statistics.py
├── 09_generate_phase2_3_plots.py
├── 10_generate_phase2_3_report_tables.py
└── 11_generate_phase2_3_final_report.py
```

## 4. Completion criteria

Phase 2.3 is complete only when all of the following are true:

- every output has a manifest containing input file fingerprints, script name, parameters, commit SHA, row counts, and validation status;
- every chart used in the final report is generated from cache, not directly from raw ad hoc script state;
- graph metrics and fundamental statistics are joined at both node level and edge level;
- `stock_sw_member`, `stock_daily_basic`, `stock_daily`, and `stock_basic_snapshot` are all used and audited;
- all plot captions explicitly say whether they describe current industry labels, historical market data, static semantic graph structure, or time-series statistics;
- report tables contain no `N/A` for fields that should be computable;
- H5 and H6 are still treated conservatively unless supported by time-series residual evidence;
- the project does not claim alpha, tradability, causal influence, or strategy validity.
