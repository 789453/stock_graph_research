# PHASE2_3_TEST_EXECUTION_CHECKLIST

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## 1. Test philosophy

Phase 2.3 tests should verify research correctness, not only Python syntax.

The project should fail early when a downstream report would be misleading.

## 2. Unit tests

### Edge construction tests

```text
tests/phase2_3/test_edge_candidates_repaired_contract.py
```

Required assertions:

- no self node edges;
- no self stock edges;
- no self record edges;
- rank range is 1..100;
- scores are finite;
- mutual edges have non-null reverse rank/score;
- mutual ratio is not exactly 0 or 1;
- exclusive rank bands are correct;
- cumulative top-K flags are correct.

### Key alignment tests

```text
tests/phase2_3/test_tushare_key_alignment.py
```

Required assertions:

- semantic stock codes convert to Tushare `ts_code`;
- no many-to-many explosion after joins;
- industry coverage threshold met;
- fundamental snapshot coverage threshold met;
- missing stocks are reported.

### Graph metric tests

```text
tests/phase2_3/test_graph_metrics_contract.py
```

Required assertions:

- directed KNN out-degree equals K before filtering;
- entropy values are non-negative;
- bridge score finite;
- hub score finite;
- component summary row counts match graph.

### Baseline tests

```text
tests/phase2_3/test_random_baseline_contract.py
```

Required assertions:

- random seed stored;
- no self-pairs in random edges;
- constrained baselines obey constraints;
- repeated baseline confidence intervals are valid;
- matched random sample count is sufficient.

### Plot tests

```text
tests/phase2_3/test_plot_registry_contract.py
```

Required assertions:

- every main report plot exists;
- every plot has a registry row;
- every registry row has a caption;
- no filename contains spaces;
- no broken Markdown image links.

### Report consistency tests

```text
tests/phase2_3/test_report_consistency.py
```

Required assertions:

- no contradictory H5 status;
- no forbidden alpha/tradability language;
- no required field reported as `N/A`;
- every table referenced in report exists;
- manifest references are complete.

## 3. Integration execution checklist

Run in this order:

```bash
python scripts/phase2_3/00_audit_latest_commit_and_inputs.py
python scripts/phase2_3/01_repair_edge_candidate_contracts.py
python scripts/phase2_3/02_validate_cache_and_report_consistency.py
python scripts/phase2_3/03_build_tushare_industry_profile.py
python scripts/phase2_3/04_build_tushare_fundamental_profile.py
python scripts/phase2_3/05_build_market_time_series_panel.py
python scripts/phase2_3/06_compute_graph_structure_metrics.py
python scripts/phase2_3/07_compute_baseline_and_residual_metrics.py
python scripts/phase2_3/08_compute_neighbor_fundamental_statistics.py
python scripts/phase2_3/09_generate_phase2_3_plots.py
python scripts/phase2_3/10_generate_phase2_3_report_tables.py
python scripts/phase2_3/11_generate_phase2_3_final_report.py
pytest tests/phase2_3 -q
```

## 4. Manual review checklist

Before merging Phase 2.3:

- inspect top 100 near-duplicate edges;
- inspect top 50 bridge edges;
- inspect top 50 hubs by in-degree and by bridge score;
- verify whether high-score cross-industry edges are real business relationships or generic text artifacts;
- verify that all final report plots are visually readable;
- verify that PE/PB extreme values are not dominating visuals;
- verify that low-value plots were not silently retained in the main report.

## 5. Acceptance criteria

Phase 2.3 can be considered complete when:

- all tests pass;
- all manifests exist;
- final report renders without broken images;
- final plot registry has no failed main plot;
- Tushare industry/fundamental data are used in both node and edge analysis;
- graph metrics appear in final tables and visualizations;
- H5/H6 are handled conservatively;
- no unproven trading claim is made.
