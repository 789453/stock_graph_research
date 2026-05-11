# PHASE 2.2 任务 00-02：代码一致性修复、边表冻结与缓存契约

## T2.2.0 代码/测试/报告一致性审计

### 背景

Phase 2.1 报告声称 mutual、reverse_score、rank band、node index 等问题已修复；同时测试文件引用了：

- `derive_mutual_edges_fast`
- `assign_rank_band_exclusive`
- `build_edge_candidates_fixed`
- `prepare_nodes_index`

Phase 2.2 必须先确认这些函数在实际源码中存在且被脚本主路径调用。如果测试引用的函数不存在，或源码仍保留旧主逻辑，则 Phase 2.1 的报告不能作为可复现事实，只能作为“目标状态描述”。

### 必须检查

```bash
grep -R "def derive_mutual_edges_fast" -n src tests scripts
grep -R "def assign_rank_band_exclusive" -n src tests scripts
grep -R "def build_edge_candidates_fixed" -n src tests scripts
grep -R "def prepare_nodes_index" -n src tests scripts
grep -R "score_dict = {i:" -n src scripts
grep -R "rank_band_exclusive" -n src scripts tests
```

### 失败条件

以下任意条件出现，T2.2.0 失败：

- 测试 import 的函数不存在；
- 主脚本仍调用旧 `build_edge_candidates`；
- `score_dict = {i: ...}` 仍存在于主路径；
- reverse_score 不是由 self-merge 或 `(src,dst)` 键查找得到；
- `rank_band` 仍输出 `core/strong/stable/context/extended`；
- `nodes.loc[src_node_ids]` 未经过 node_id index validation；
- 报告说 FIXED，但代码和测试不能证明。

### 输出

```text
outputs/reports/phase2_2/T2_2_0_CODE_CONSISTENCY_AUDIT.md
outputs/reports/phase2_2/T2_2_0_CODE_CONSISTENCY_AUDIT.json
```

JSON schema：

```json
{
  "task_id": "T2.2.0",
  "status": "success|failed",
  "checked_commit": "...",
  "required_functions": {
    "derive_mutual_edges_fast": true,
    "assign_rank_band_exclusive": true,
    "build_edge_candidates_fixed": true,
    "prepare_nodes_index": true
  },
  "forbidden_patterns": {
    "score_dict_integer_key_reverse_score": false,
    "legacy_rank_band_names_in_main_path": false
  },
  "blocking_errors": []
}
```

## T2.2.1 修复建议：统一图构造核心函数

### `derive_mutual_edges_fast`

必须替换旧 O(E²) 写法。推荐实现：

```python
def derive_mutual_edges_fast(edges: pd.DataFrame):
    req = {"src_node_id", "dst_node_id", "rank", "score"}
    missing = req - set(edges.columns)
    if missing:
        raise ValueError(f"missing columns: {missing}")

    x = edges[["src_node_id", "dst_node_id", "rank", "score"]].copy()
    x["src_node_id"] = x["src_node_id"].astype("int32")
    x["dst_node_id"] = x["dst_node_id"].astype("int32")
    x["rank"] = x["rank"].astype("int16")
    x["score"] = x["score"].astype("float32")

    rev = x.rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score"
    })

    merged = x.merge(rev, on=["src_node_id", "dst_node_id"], how="left", validate="one_to_one")
    merged["is_mutual"] = merged["reverse_rank"].notna()
    mutual_directed = merged[merged["is_mutual"]].copy()
    mutual_directed["score_mean"] = (
        mutual_directed["score"].astype("float32") + mutual_directed["reverse_score"].astype("float32")
    ) / 2

    mutual_directed["u_node_id"] = np.minimum(mutual_directed["src_node_id"], mutual_directed["dst_node_id"])
    mutual_directed["v_node_id"] = np.maximum(mutual_directed["src_node_id"], mutual_directed["dst_node_id"])
    mutual_pairs = (
        mutual_directed
        .sort_values(["u_node_id", "v_node_id", "src_node_id"])
        .drop_duplicates(["u_node_id", "v_node_id"])
        .copy()
    )
    return mutual_directed, mutual_pairs
```

### `assign_rank_band_exclusive`

```python
def assign_rank_band_exclusive(rank: np.ndarray) -> np.ndarray:
    r = np.asarray(rank)
    out = np.full(r.shape, "out_of_range", dtype=object)
    out[(r >= 1) & (r <= 5)] = "rank_001_005"
    out[(r >= 6) & (r <= 10)] = "rank_006_010"
    out[(r >= 11) & (r <= 20)] = "rank_011_020"
    out[(r >= 21) & (r <= 50)] = "rank_021_050"
    out[(r >= 51) & (r <= 100)] = "rank_051_100"
    return out
```

### `prepare_nodes_index`

```python
def prepare_nodes_index(nodes: pd.DataFrame, n: int) -> pd.DataFrame:
    if "node_id" not in nodes.columns:
        raise ValueError("nodes must contain node_id")
    out = nodes.set_index("node_id", drop=False).sort_index()
    expected = np.arange(n)
    if not np.array_equal(out.index.to_numpy(), expected):
        raise ValueError("nodes index must be exactly 0..n-1")
    if out["stock_code"].isna().any():
        raise ValueError("nodes contains missing stock_code")
    if out["stock_code"].duplicated().any():
        raise ValueError("duplicated stock_code in nodes")
    if "record_id" in out.columns and out["record_id"].duplicated().any():
        raise ValueError("duplicated record_id in nodes")
    return out
```

## T2.2.2 四 view 边表冻结

### 输入

```text
cache/semantic_graph/views/{view}/{view_key}/graph/neighbors_k100.npz
cache/semantic_graph/views/{view}/{view_key}/graph/graph_summary.json
cache/semantic_graph/views/{view}/{view_key}/audit/alignment_diagnostics.json
```

### 输出

```text
cache/semantic_graph/views/{view}/{view_key}/phase2_2/edge_layers/edge_candidates_k100_fixed.parquet
cache/semantic_graph/views/{view}/{view_key}/phase2_2/edge_layers/edge_candidates_k100_fixed.csv.gz
cache/semantic_graph/views/{view}/{view_key}/phase2_2/edge_layers/edge_layer_summary.json
outputs/reports/phase2_2/{view}/edge_layer_freeze_report.md
```

### 必须字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `src_node_id` | int32 | 源节点 |
| `dst_node_id` | int32 | 目标节点 |
| `src_stock_code` | string | 源股票 |
| `dst_stock_code` | string | 目标股票 |
| `src_record_id` | string | 源 record |
| `dst_record_id` | string | 目标 record |
| `rank` | int16 | 1-100 |
| `score` | float32 | 余弦相似度 |
| `rank_band_exclusive` | category | 互斥 rank band |
| `top_001_005` 等 | bool | cumulative topK flag |
| `is_mutual` | bool | 是否互惠 |
| `reverse_rank` | int16/null | 反向 rank |
| `reverse_score` | float32/null | 反向 score |
| `score_mean_if_mutual` | float32/null | 互惠均值 |
| `src_score_gap_from_top1` | float32 | 与 top1 差距 |
| `duplicate_risk_flag` | bool | 近重复风险 |

### Sanity check

- 每 view 行数必须为 `5502 * 100 = 550200`；
- `src_node_id != dst_node_id`；
- `src_stock_code != dst_stock_code`；
- `src_record_id != dst_record_id`；
- `reverse_score_nonnull_ratio` 在 mutual 边中应为 1；
- `0 < mutual_ratio < 1`；
- `rank_band_exclusive` 不允许出现旧命名；
- `score` 必须 finite；
- `rank` 必须在 1-100。

## T2.2.3 缓存 manifest 统一

每个任务输出一个 manifest：

```json
{
  "phase": "phase2_2",
  "task_id": "T2.2.x",
  "view_name": "chain_text",
  "view_key": "58563ca7113f",
  "status": "success",
  "commit_sha": "...",
  "config_path": "configs/phase2_2_market_resonance.yaml",
  "config_sha256": "...",
  "started_at": "...",
  "finished_at": "...",
  "elapsed_seconds": 0.0,
  "inputs": [],
  "outputs": [],
  "row_counts": {},
  "parameters": {},
  "warnings": [],
  "blocking_errors": [],
  "safe_to_continue": true
}
```

最终汇总：

```text
cache/semantic_graph/phase2_2/manifests/phase2_2_master_manifest.json
outputs/reports/phase2_2/PHASE2_2_RUN_MANIFEST.md
```
