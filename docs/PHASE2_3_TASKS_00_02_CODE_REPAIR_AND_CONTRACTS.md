# PHASE2_3_TASKS_00_02_CODE_REPAIR_AND_CONTRACTS

> Project: `789453/stock_graph_research`
> Phase: `phase2.3`
> Role: research engineering specification, code repair plan, data enrichment plan, visualization/reporting contract
> Scope: semantic stock graph research on A-share company business semantics, industry/fundamental/market/graph structure statistics
> Non-goals: no backtest, no alpha claim, no GNN, no production trading system, no mock data, no replacing real 1024-d embeddings with TF-IDF/PCA


## Task 00 — Audit latest commit and invalidate unsafe legacy outputs

### Goal

Create a machine-readable audit of the current repository state and explicitly mark which Phase 2 / Phase 2.1 / Phase 2.2 outputs are safe to reuse.

### Inputs

```text
git log -1
PROJECT_STATE.md
outputs/reports/
cache/semantic_graph/*/phase2*/
scripts/
src/semantic_graph_research/
tests/
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/audits/latest_commit_audit.json
cache/semantic_graph/<run_id>/phase2_3/audits/legacy_output_validity_matrix.csv
outputs/reports/phase2_3/PHASE2_3_ENGINEERING_AUDIT.md
```

### Required logic

1. Read `git log -1 --format=%H%n%s%n%ci%n%an`.
2. Store full SHA, short SHA, commit message, author, commit time, dirty-worktree status.
3. Read known Phase 2/2.1/2.2 output directories.
4. Mark each legacy output as:
   - `safe_reuse`: usable without recomputation;
   - `recompute_required`: old logic or missing manifest;
   - `appendix_only`: useful for human context but not evidence;
   - `invalid`: known incorrect.
5. Known invalid or suspicious classes:
   - outputs depending on pre-repair `reverse_score`;
   - outputs using ambiguous `core/strong/stable` rank-band names;
   - plots with missing images or invalid paths;
   - reports containing contradictory H5 interpretation;
   - market/fundamental tables without key-alignment audit.

### Validation

Fail if current commit cannot be recorded.

### Implementation notes

Use a `ValidityReason` enum rather than free text. This makes future report generation deterministic.

---

## Task 01 — Repair and harden edge candidate contracts

### Goal

Ensure every edge-level downstream analysis uses a repaired, explicit, auditable edge candidate table.

### Inputs

```text
cache/semantic_graph/<run_id>/phase2_2_or_latest/edge_candidates_k100.parquet
cache/semantic_graph/<run_id>/phase2_2_or_latest/nodes.parquet
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/edge_metrics/edge_candidates_k100_repaired.parquet
cache/semantic_graph/<run_id>/phase2_3/audits/self_edge_audit.csv
cache/semantic_graph/<run_id>/phase2_3/audits/near_duplicate_edge_audit.csv
cache/semantic_graph/<run_id>/phase2_3/manifests/t01_edge_repair_manifest.json
```

### Required edge logic

1. Enforce node index:
   - `node_id` must be unique;
   - sorted `node_id` must equal `[0, n-1]`;
   - DataFrame index must not be relied on unless explicitly set.
2. Self-edge validation:
   - no same `node_id`;
   - no same `ts_code`;
   - no same `record_id`.
3. Reverse-edge logic:
   - build reverse table by swapping source and destination;
   - merge to original edge table on `(src_node_id, dst_node_id)`;
   - compute `is_mutual`, `reverse_rank`, `reverse_score`, `score_mean_if_mutual`.
4. Rank-band logic:
   - create exclusive and cumulative flags;
   - forbid ambiguous `core/strong/stable`.
5. Near duplicate logic:
   - output all edges with `score >= 0.999999`;
   - include source/target names, industry, text-view ID if available;
   - classify later, do not delete automatically.

### Expected columns

See `PHASE2_3_CACHE_SCHEMA_AND_OUTPUT_CONTRACTS.md`.

### Validation

Fail if:

- total edge count is not `node_count * 100` for k=100;
- any self-edge count is non-zero;
- any mutual edge has null reverse score;
- mutual ratio is exactly 0 or exactly 1;
- rank range is outside 1..100;
- any score is non-finite.

### Potential hidden bug to fix

If old code uses `score_dict = {i: score}` and then queries by `(dst, src)`, reverse score is wrong. Replace all such logic with a reverse self-merge.

---

## Task 02 — Validate cache, reports, and plotting contracts

### Goal

Stop the project from silently producing incomplete reports or broken images.

### Inputs

```text
outputs/reports/
outputs/plots/
cache/semantic_graph/<run_id>/phase2_3/
```

### Outputs

```text
cache/semantic_graph/<run_id>/phase2_3/audits/report_consistency_audit.json
cache/semantic_graph/<run_id>/phase2_3/tables/table_06_plot_registry.csv
```

### Required checks

#### Report checks

- no contradictory H5 status;
- no `N/A` in required metrics;
- every image path exists;
- every table path exists;
- every cited cache artifact has a manifest entry;
- old ambiguous band labels are mapped or removed.

#### Plot checks

- filename has no spaces;
- image extension is `.png` or `.svg`;
- plot size is at least 1400x900 for main figures;
- no unreadable Chinese tofu boxes in final plots unless CJK font is configured;
- every plot has a caption and source table.

#### Cache checks

- every manifest output exists;
- output row counts match actual files;
- all fingerprints are present;
- scripts record parameters.

### Recommended implementation

Create one reusable validator:

```python
def validate_artifact_registry(registry: pd.DataFrame, strict: bool = True) -> ValidationResult:
    ...
```

The final report generator must call the validator before writing the report.
