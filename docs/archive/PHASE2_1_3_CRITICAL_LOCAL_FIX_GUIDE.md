# PHASE2_1_3_CRITICAL_LOCAL_FIX_GUIDE.md

## 0. 文档定位

本文件是 Phase 2.1 中最关键的本地修复指导文档，专门对应 `T2.1.3 fixed edge candidates` 及其前后依赖问题。它不是泛泛的设计文档，而是面向本地代码修改的执行说明。

这份文档聚焦以下 9 个必须修复的问题：

1. `phase2_graph_layers.py` 中 `build_edge_candidates` 的 mutual 方向性错误；
2. `reverse_score` 字典 key 错误；
3. `graph_builder.py` 中 `derive_mutual_edges` 的 O(E²) 性能隐患；
4. `nodes.loc[...]` 隐式依赖 index 恰好等于 node_id；
5. rank band 命名混乱，exclusive band 与 cumulative topK 混写；
6. 多个 band 的 max score=1.0000，需要 near duplicate 与 self-edge 审计；
7. `nodes_with_market_data=0` 与分桶并存，size/liquidity 字段口径错误；
8. `industry_comparison:{}` 为空，说明行业、市值、流动性之外的增量未被验证；
9. H5 口径冲突，旧 Phase 2 静态 proxy 不能写成市场行为共振支持。

这 9 个问题中，前 6 个直接影响 `T2.1.3` 的边表正确性；第 7、8、9 个影响后续所有金融解释和报告结论。建议本地修复顺序为：

```text
P0 修 graph_builder.py 的 mutual 快速实现
P1 修 phase2_graph_layers.py 的 build_edge_candidates_fixed
P2 新增 T2.1.3 小样本单元测试
P3 重新生成 edge_candidates_k100 和 edge_layer_summary
P4 修 size/liquidity profile
P5 补 industry_comparison matched random
P6 修 H5 summary/report schema
```

没有 P0—P3，后面的 hub、bridge、adaptive edge layer、市场行为都不可信。没有 P4—P6，后面的金融解释都不严谨。

---

## 1. 当前仓库中已确认的问题位置

### 1.1 `src/semantic_graph_research/phase2_graph_layers.py`

当前文件中存在以下关键代码口径：

```python
def assign_rank_band(rank: int) -> str:
    if rank <= 5:
        return "core"
    elif rank <= 10:
        return "strong"
    elif rank <= 20:
        return "stable"
    elif rank <= 50:
        return "context"
    else:
        return "extended"
```

这个命名并非绝对错误，但后续报告中容易把 `strong` 理解为 top10，而它实际是 rank 6—10。Phase 2.1 必须改为明确的 `rank_006_010`。

当前 `build_edge_candidates` 中使用：

```python
nodes.loc[src_node_ids, "stock_code"].values
nodes.loc[dst_node_ids, "stock_code"].values
```

这隐含要求 `nodes.index == node_id`。本地目前可能刚好成立，但 parquet 读写、排序、筛选后非常容易失效。

当前 mutual 逻辑是：

```python
key = (edges.iloc[i]["dst_node_id"], edges.iloc[i]["src_node_id"])
reverse_map[key] = edges.iloc[i]["rank"]

src_dst_pairs = list(zip(edges["dst_node_id"], edges["src_node_id"]))
is_mutual_arr = np.array([key in reverse_map for key in src_dst_pairs], dtype=bool)
```

这会将每条边错误地命中自己登记过的 `(dst, src)` key，导致 `mutual_ratio=1.0`。

当前 reverse score 逻辑是：

```python
score_dict = {i: edges.iloc[i]["score"] for i in range(len(edges))}
score_dict.get((edges.iloc[i]["dst_node_id"], edges.iloc[i]["src_node_id"]), 0.0)
```

`score_dict` 的 key 是整数行号，查询 key 是 tuple，几乎必然查不到。结果是 `reverse_score` 默认 0.0，进而污染 `score_mean_if_mutual`。

### 1.2 `src/semantic_graph_research/graph_builder.py`

当前 `derive_mutual_edges` 逻辑是：

```python
edge_set = set(zip(directed_edges["src_node_id"], directed_edges["dst_node_id"]))
mutual_rows = []
for _, row in directed_edges.iterrows():
    u, v = row["src_node_id"], row["dst_node_id"]
    if (v, u) in edge_set:
        rev_row = directed_edges[
            (directed_edges["src_node_id"] == v) &
            (directed_edges["dst_node_id"] == u)
        ]
```

`edge_set` 本身是 O(E) 的好思路，但后面每一条互惠候选又回到 DataFrame 布尔过滤，整体性能接近 O(E²)。k=20 时还能忍，四 view × k=100 时不合适。

### 1.3 `cache/.../edge_layer_summary.json`

旧结果中：

```json
"mutual_edge_count": 550200,
"mutual_ratio": 1.0
```

这是 bug 结果，不应作为任何后续金融结论。修复后若仍接近 1.0，必须输出反向边样例和验证报告，不能静默通过。

### 1.4 `cache/.../size_liquidity_summary.json`

旧结果中：

```json
"total_nodes": 5502,
"nodes_with_market_data": 0,
"cap_stats": {},
"size_quintile_dist": {"1":1101, "2":1100, ...}
```

这说明 summary 的 market data 字段统计口径错了。因为如果 `nodes_with_market_data=0`，不应同时生成看似合理的五分位分布。本地脚本应修复字段名并强制 matched 节点数。

---

## 2. 必须建立的本地不变量

修复前，先把这些不变量写进测试和 sanity check。

### 2.1 节点不变量

```text
node_id 必须是 0..n-1
nodes.set_index("node_id").index 必须等于 np.arange(n)
stock_code 不允许为空
stock_code 不允许重复
record_id 不允许重复
```

### 2.2 边不变量

```text
src_node_id != dst_node_id
src_stock_code != dst_stock_code
src_record_id != dst_record_id
edge count = n * k
rank in [1, k]
每个 src_node_id 正好 k 条边
```

### 2.3 mutual 不变量

```text
is_mutual(u,v) = True 当且仅当 (v,u) 存在
reverse_rank(u,v) = rank(v,u)
reverse_score(u,v) = score(v,u)
score_mean_if_mutual = (score_uv + score_vu) / 2
n_mutual_pairs_unique <= n_mutual_edges_directed_rows
若无重复边，n_mutual_edges_directed_rows = 2 * n_mutual_pairs_unique
```

### 2.4 rank 命名不变量

```text
rank_001_005 = ranks 1..5
rank_006_010 = ranks 6..10
rank_011_020 = ranks 11..20
rank_021_050 = ranks 21..50
rank_051_100 = ranks 51..100

top_001_005 = rank <= 5
top_001_010 = rank <= 10
top_001_020 = rank <= 20
top_001_050 = rank <= 50
top_001_100 = rank <= 100
```

### 2.5 市场数据不变量

```text
matched_market_nodes >= 5400
matched_market_nodes != 0
median_total_mv 字段存在
median_circ_mv 字段存在
median_turnover_rate 字段存在
median_amount 字段存在
size_bucket_10、liquidity_bucket_10、amount_bucket_10 不应在 matched=0 时生成
```

---

## 3. 修改一：替换 `derive_mutual_edges`

### 3.1 推荐修改位置

文件：

```text
src/semantic_graph_research/graph_builder.py
```

保留旧函数名 `derive_mutual_edges` 也可以，但内部应改成 fast self-merge。为了兼容旧调用，建议实现两个函数：

- `derive_mutual_edges_fast`
- `derive_mutual_edges = derive_mutual_edges_fast` 或让旧函数调用新函数

### 3.2 推荐代码

```python
import numpy as np
import pandas as pd

def derive_mutual_edges_fast(
    directed_edges: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"src_node_id", "dst_node_id", "rank", "score"}
    missing = required - set(directed_edges.columns)
    if missing:
        raise ValueError(f"directed_edges missing columns: {missing}")

    edges = directed_edges.copy()
    edges["src_node_id"] = edges["src_node_id"].astype(np.int32)
    edges["dst_node_id"] = edges["dst_node_id"].astype(np.int32)
    edges["rank"] = edges["rank"].astype(np.int32)
    edges["score"] = edges["score"].astype(np.float32)

    duplicated = edges.duplicated(["src_node_id", "dst_node_id"])
    if duplicated.any():
        bad = edges.loc[duplicated, ["src_node_id", "dst_node_id"]].head(10).to_dict("records")
        raise ValueError(f"duplicated directed edges found, examples={bad}")

    self_edges = edges["src_node_id"].to_numpy() == edges["dst_node_id"].to_numpy()
    if self_edges.any():
        bad = edges.loc[self_edges, ["src_node_id", "dst_node_id", "rank", "score"]].head(10).to_dict("records")
        raise ValueError(f"self edges found in directed_edges, examples={bad}")

    reverse = edges[["src_node_id", "dst_node_id", "rank", "score"]].rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score",
    })

    merged = edges.merge(
        reverse,
        on=["src_node_id", "dst_node_id"],
        how="left",
        validate="one_to_one",
    )

    mutual_directed = merged[merged["reverse_rank"].notna()].copy()
    mutual_directed["reverse_rank"] = mutual_directed["reverse_rank"].astype(np.int32)
    mutual_directed["reverse_score"] = mutual_directed["reverse_score"].astype(np.float32)
    mutual_directed["score_mean"] = (
        mutual_directed["score"].astype(np.float32) +
        mutual_directed["reverse_score"].astype(np.float32)
    ) / 2.0

    mutual_directed["u_node_id"] = np.minimum(
        mutual_directed["src_node_id"].to_numpy(),
        mutual_directed["dst_node_id"].to_numpy(),
    )
    mutual_directed["v_node_id"] = np.maximum(
        mutual_directed["src_node_id"].to_numpy(),
        mutual_directed["dst_node_id"].to_numpy(),
    )

    mutual_pairs = (
        mutual_directed
        .sort_values(["u_node_id", "v_node_id", "src_node_id"])
        .drop_duplicates(["u_node_id", "v_node_id"])
        .copy()
    )

    n_directed = len(edges)
    n_mutual_directed = len(mutual_directed)
    n_mutual_pairs = len(mutual_pairs)
    reciprocity_ratio = n_mutual_directed / n_directed if n_directed else 0.0

    if n_mutual_directed != 2 * n_mutual_pairs:
        raise ValueError(
            f"mutual directed rows should equal 2 * unique pairs; "
            f"got {n_mutual_directed=} {n_mutual_pairs=}"
        )

    if not (0.0 <= reciprocity_ratio <= 1.0):
        raise ValueError(f"invalid reciprocity_ratio={reciprocity_ratio}")

    return mutual_directed, mutual_pairs


def derive_mutual_edges(directed_edges: pd.DataFrame) -> pd.DataFrame:
    mutual_directed, _ = derive_mutual_edges_fast(directed_edges)
    return mutual_directed
```

### 3.3 为什么这段代码正确

对原始边 `(u, v)`，`reverse` 表中来自反向原始边 `(v, u)` 的行会被重命名为 `(u, v, reverse_rank, reverse_score)`。因此 `edges.merge(reverse, on=["src_node_id", "dst_node_id"])` 正好把 `(u,v)` 与 `(v,u)` 连接起来。

`validate="one_to_one"` 用来确保 `(src_node_id, dst_node_id)` 没有重复。如果重复，它会直接报错，而不是静默扩大行数。

---

## 4. 修改二：重写 `build_edge_candidates`

### 4.1 推荐修改位置

文件：

```text
src/semantic_graph_research/phase2_graph_layers.py
```

新增函数：

- `prepare_nodes_index`
- `assign_rank_band_exclusive`
- `add_cumulative_topk_flags`
- `build_edge_candidates_fixed`

旧的 `build_edge_candidates` 可以保留为 wrapper，但建议让它调用 `build_edge_candidates_fixed`，避免脚本大面积改动。

### 4.2 推荐代码

```python
import numpy as np
import pandas as pd


def prepare_nodes_index(nodes: pd.DataFrame, n: int) -> pd.DataFrame:
    if "node_id" not in nodes.columns:
        raise ValueError("nodes must contain node_id")

    required_cols = {"node_id", "stock_code"}
    missing = required_cols - set(nodes.columns)
    if missing:
        raise ValueError(f"nodes missing required columns: {missing}")

    nodes_idx = nodes.set_index("node_id", drop=False).sort_index()

    expected = np.arange(n)
    actual = nodes_idx.index.to_numpy()

    if not np.array_equal(actual, expected):
        raise ValueError(
            "nodes index is not exactly node_id 0..n-1; "
            f"actual head={actual[:10].tolist()}, expected head={expected[:10].tolist()}"
        )

    if nodes_idx["stock_code"].isna().any():
        bad = nodes_idx.loc[nodes_idx["stock_code"].isna()].head(10).index.tolist()
        raise ValueError(f"nodes contains missing stock_code, examples node_id={bad}")

    if nodes_idx["stock_code"].duplicated().any():
        dup = nodes_idx.loc[nodes_idx["stock_code"].duplicated(), "stock_code"].head(10).tolist()
        raise ValueError(f"duplicated stock_code in nodes, examples={dup}")

    return nodes_idx


def assign_rank_band_exclusive(rank_array: np.ndarray) -> np.ndarray:
    rank = rank_array.astype(np.int32)
    out = np.full(rank.shape, "rank_out_of_range", dtype=object)

    out[(rank >= 1) & (rank <= 5)] = "rank_001_005"
    out[(rank >= 6) & (rank <= 10)] = "rank_006_010"
    out[(rank >= 11) & (rank <= 20)] = "rank_011_020"
    out[(rank >= 21) & (rank <= 50)] = "rank_021_050"
    out[(rank >= 51) & (rank <= 100)] = "rank_051_100"

    if (out == "rank_out_of_range").any():
        bad = rank[out == "rank_out_of_range"][:10].tolist()
        raise ValueError(f"rank out of configured bands, examples={bad}")

    return out


def add_cumulative_topk_flags(edges: pd.DataFrame) -> None:
    edges["top_001_005"] = edges["rank"] <= 5
    edges["top_001_010"] = edges["rank"] <= 10
    edges["top_001_020"] = edges["rank"] <= 20
    edges["top_001_050"] = edges["rank"] <= 50
    edges["top_001_100"] = edges["rank"] <= 100
```

### 4.3 `build_edge_candidates_fixed`

```python
def build_edge_candidates_fixed(
    neighbors_k100: np.ndarray,
    scores_k100: np.ndarray,
    nodes: pd.DataFrame,
    near_duplicate_score_threshold: float = 0.999999,
) -> pd.DataFrame:
    if neighbors_k100.shape != scores_k100.shape:
        raise ValueError(
            f"neighbors and scores shape mismatch: "
            f"{neighbors_k100.shape} vs {scores_k100.shape}"
        )

    n, k = neighbors_k100.shape
    if k != 100:
        raise ValueError(f"Phase 2.1 expects k=100, got k={k}")

    nodes_idx = prepare_nodes_index(nodes, n)

    src_node_ids = np.repeat(np.arange(n, dtype=np.int32), k)
    dst_node_ids = neighbors_k100.reshape(-1).astype(np.int32)
    rank_array = np.tile(np.arange(1, k + 1, dtype=np.int32), n)
    score_flat = scores_k100.reshape(-1).astype(np.float32)

    if dst_node_ids.min() < 0 or dst_node_ids.max() >= n:
        raise ValueError(
            f"dst_node_id out of range: min={dst_node_ids.min()}, max={dst_node_ids.max()}, n={n}"
        )

    self_mask = src_node_ids == dst_node_ids
    if self_mask.any():
        bad_idx = np.where(self_mask)[0][:10]
        bad = [
            {
                "row_idx": int(i),
                "src_node_id": int(src_node_ids[i]),
                "dst_node_id": int(dst_node_ids[i]),
                "rank": int(rank_array[i]),
                "score": float(score_flat[i]),
            }
            for i in bad_idx
        ]
        raise ValueError(f"self edges found in kNN candidates, examples={bad}")

    edges = pd.DataFrame({
        "src_node_id": src_node_ids,
        "dst_node_id": dst_node_ids,
        "rank": rank_array,
        "score": score_flat,
    })

    if edges.duplicated(["src_node_id", "dst_node_id"]).any():
        bad = edges.loc[
            edges.duplicated(["src_node_id", "dst_node_id"]),
            ["src_node_id", "dst_node_id", "rank", "score"],
        ].head(10).to_dict("records")
        raise ValueError(f"duplicated edge pairs found, examples={bad}")

    edges["src_stock_code"] = nodes_idx.loc[src_node_ids, "stock_code"].to_numpy()
    edges["dst_stock_code"] = nodes_idx.loc[dst_node_ids, "stock_code"].to_numpy()

    if "record_id" in nodes_idx.columns:
        edges["src_record_id"] = nodes_idx.loc[src_node_ids, "record_id"].to_numpy()
        edges["dst_record_id"] = nodes_idx.loc[dst_node_ids, "record_id"].to_numpy()
    else:
        edges["src_record_id"] = edges["src_node_id"]
        edges["dst_record_id"] = edges["dst_node_id"]

    same_stock = edges["src_stock_code"].to_numpy() == edges["dst_stock_code"].to_numpy()
    if same_stock.any():
        bad = edges.loc[same_stock, ["src_node_id", "dst_node_id", "src_stock_code", "dst_stock_code"]].head(10)
        raise ValueError(f"self stock_code edges found: {bad.to_dict('records')}")

    same_record = edges["src_record_id"].to_numpy() == edges["dst_record_id"].to_numpy()
    if same_record.any():
        bad = edges.loc[same_record, ["src_node_id", "dst_node_id", "src_record_id", "dst_record_id"]].head(10)
        raise ValueError(f"self record_id edges found: {bad.to_dict('records')}")

    reverse = edges[["src_node_id", "dst_node_id", "rank", "score"]].rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score",
    })

    edges = edges.merge(
        reverse,
        on=["src_node_id", "dst_node_id"],
        how="left",
        validate="one_to_one",
    )

    edges["is_mutual"] = edges["reverse_rank"].notna()
    edges["reverse_rank"] = edges["reverse_rank"].fillna(-1).astype(np.int32)
    edges["reverse_score"] = edges["reverse_score"].astype(np.float32)

    edges["score_mean_if_mutual"] = np.where(
        edges["is_mutual"].to_numpy(),
        (edges["score"].to_numpy(dtype=np.float32) + edges["reverse_score"].to_numpy(dtype=np.float32)) / 2.0,
        np.nan,
    ).astype(np.float32)

    top1_scores = np.repeat(scores_k100[:, 0].astype(np.float32), k)
    edges["src_top1_score"] = top1_scores
    edges["src_score_gap_from_top1"] = edges["src_top1_score"] - edges["score"]
    edges["src_score_rank_pct"] = edges["rank"] / k

    edges["rank_band_exclusive"] = assign_rank_band_exclusive(edges["rank"].to_numpy())
    add_cumulative_topk_flags(edges)

    edges["near_duplicate_score_flag"] = edges["score"] >= near_duplicate_score_threshold

    mutual_ratio = float(edges["is_mutual"].mean())
    if not (0.0 < mutual_ratio < 1.0):
        sample = edges.head(20).to_dict("records")
        raise ValueError(
            f"invalid mutual_ratio={mutual_ratio}; expected 0<ratio<1 for current k=100 sanity. "
            f"sample={sample[:2]}"
        )

    reverse_score_nonnull = edges.loc[edges["is_mutual"], "reverse_score"].notna().mean()
    if reverse_score_nonnull < 0.999:
        raise ValueError(f"reverse_score missing for mutual edges: nonnull_ratio={reverse_score_nonnull}")

    if (edges.loc[edges["is_mutual"], "reverse_score"].fillna(0.0) == 0.0).mean() > 0.5:
        raise ValueError("too many mutual edges have reverse_score=0.0; likely reverse lookup bug remains")

    return edges
```

### 4.4 兼容旧函数名

为了减少脚本改动，可加：

```python
def build_edge_candidates(
    neighbors_k100: np.ndarray,
    scores_k100: np.ndarray,
    nodes: pd.DataFrame,
    rank_bands: dict | None = None,
) -> pd.DataFrame:
    return build_edge_candidates_fixed(
        neighbors_k100=neighbors_k100,
        scores_k100=scores_k100,
        nodes=nodes,
    )
```

---

## 5. 修改三：T2.1.3 脚本应如何写

### 5.1 推荐新脚本

新增：

```text
scripts/19_build_fixed_edge_candidates.py
```

不要直接覆盖旧 `07_build_extended_edge_candidates.py`，先保留旧结果，然后新脚本写入 Phase 2.1 新目录。

### 5.2 输出路径

```text
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_candidates_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_layer_summary.json
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_score_by_rank.csv
cache/semantic_graph/views/{view}/{view_key}/edge_layers/mutual_ratio_by_rank.csv
cache/semantic_graph/views/{view}/{view_key}/edge_layers/near_duplicate_pairs.csv
outputs/reports/phase2_1/{view}/edge_candidate_repair_report.md
logs/phase2_1/{view}/19_build_fixed_edge_candidates.log
```

### 5.3 summary 必须包含

```json
{
  "view_name": "",
  "view_key": "",
  "n_nodes": 5502,
  "k": 100,
  "n_edges": 550200,
  "mutual_directed_rows": 0,
  "mutual_pairs_unique": 0,
  "reciprocity_ratio": 0.0,
  "reverse_score_nonnull_ratio": 0.0,
  "near_duplicate_edges_count": 0,
  "rank_band_counts": {},
  "score_by_rank_path": "",
  "status": "success"
}
```

### 5.4 失败条件

- edge count 不等于 5502×100；
- mutual_ratio 等于 1；
- reverse_score 对 mutual 边大量为空；
- reverse_score 大量为 0；
- rank band 出现旧命名 core/strong/stable；
- near duplicate 不输出；
- self stock_code edge 存在；
- self record_id edge 存在。

---

## 6. 修改四：near duplicate 审计

### 6.1 为什么必须做

多个 rank band 的 max score 显示为 1.0000，不能直接视为正常。它可能只是四位显示，也可能是：

- 向量重复；
- 文本模板重复；
- 公司描述高度同质；
- self-neighbor 未清理；
- record_id/stock_code 映射错误。

### 6.2 输出

对每个 view 输出：

```text
audit/near_duplicate_pairs.csv
edge_layers/near_duplicate_edges.csv
outputs/plots/phase2_1/{view}/near_duplicate_score_histogram_{view}.png
```

字段：

- src_node_id；
- dst_node_id；
- src_stock_code；
- dst_stock_code；
- src_record_id；
- dst_record_id；
- rank；
- score；
- is_mutual；
- reverse_score；
- same_l1；
- same_l3；
- duplicate_reason_candidate。

### 6.3 规则

```python
near_dup = edges[edges["score"] >= 0.999999].copy()
```

如果数量为 0，仍输出空 csv 和 summary。  
如果数量很多，不直接删除，但在 view report 中标记。

---

## 7. 修改五：size/liquidity 修复

### 7.1 推荐新脚本

新增或重写：

```text
scripts/21_repair_size_liquidity_profile.py
```

不建议在旧 `10_size_liquidity_domain.py` 上继续补丁式修改，因为旧脚本是 Phase 2 单 view 逻辑。

### 7.2 DuckDB 读取模板

```python
def read_market_profile_with_duckdb(
    stock_daily_basic_path: str,
    stock_daily_path: str,
    stock_codes: list[str],
    start_date: str = "20180101",
    end_date: str = "20260423",
) -> pd.DataFrame:
    import duckdb
    import pandas as pd

    con = duckdb.connect()
    codes_df = pd.DataFrame({"ts_code": stock_codes})
    con.register("codes", codes_df)

    basic = con.execute(f'''
        SELECT
            b.ts_code,
            median(b.total_mv) AS median_total_mv,
            median(b.circ_mv) AS median_circ_mv,
            median(b.turnover_rate) AS median_turnover_rate
        FROM read_parquet('{stock_daily_basic_path}') b
        INNER JOIN codes c ON b.ts_code = c.ts_code
        WHERE b.trade_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY b.ts_code
    ''').df()

    daily = con.execute(f'''
        SELECT
            d.ts_code,
            median(d.amount) AS median_amount
        FROM read_parquet('{stock_daily_path}') d
        INNER JOIN codes c ON d.ts_code = c.ts_code
        WHERE d.trade_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY d.ts_code
    ''').df()

    return basic.merge(daily, on="ts_code", how="outer", validate="one_to_one")
```

### 7.3 强校验

```python
matched = profile["median_total_mv"].notna().sum()
if matched < 5400:
    raise ValueError(f"market matched nodes too low: {matched}, expected >= 5400")
```

### 7.4 输出

```text
cache/semantic_graph/multi_view/baselines/node_size_liquidity_profile.parquet
cache/semantic_graph/multi_view/baselines/size_liquidity_summary.json
outputs/reports/phase2_1/size_liquidity_repair_report.md
```

summary：

```json
{
  "total_nodes": 5502,
  "matched_market_nodes": 0,
  "unmatched_nodes": 0,
  "min_required_matched_nodes": 5400,
  "fields": [
    "median_total_mv",
    "median_circ_mv",
    "median_turnover_rate",
    "median_amount"
  ],
  "status": "success"
}
```

---

## 8. 修改六：industry_comparison 不能再为空

### 8.1 必须实现的 baseline

对每个 view，每个 rank band，至少输出：

- `global_random`
- `same_l3_random`
- `same_l3_same_size_random`
- `same_l3_same_liquidity_random`
- `cross_l1_random`
- `cross_l1_same_size_liquidity_random`

### 8.2 baseline 抽样原则

随机边必须匹配：

- src_node_id 分布；
- edge count；
- rank band 或 edge layer；
- domain 约束。

例如 cross L1 random：

```text
对每个 src，在所有 dst 中抽取 l1(dst) != l1(src) 的股票，数量等于该 src 的 semantic cross L1 edge 数。
```

same L3 + size random：

```text
对每个 src，在 l3(dst)==l3(src) 且 size_bucket(dst)==size_bucket(src) 的股票中随机抽取。
```

### 8.3 输出 schema

```json
{
  "view_name": "chain_text",
  "rank_001_005": {
    "semantic": {
      "edge_count": 0,
      "same_l3_ratio": 0.0,
      "cross_l1_ratio": 0.0,
      "monthly_resid_corr_mean": null
    },
    "global_random": {},
    "same_l3_random": {},
    "same_l3_same_size_random": {},
    "same_l3_same_liquidity_random": {},
    "cross_l1_random": {},
    "cross_l1_same_size_liquidity_random": {}
  }
}
```

`industry_comparison` 不允许是 `{}`。若某 baseline 因候选不足无法抽样，必须写：

```json
{
  "status": "insufficient_candidates",
  "reason": "...",
  "semantic_edge_count": 0,
  "candidate_count": 0
}
```

而不是空对象。

---

## 9. 修改七：H5 报告口径

### 9.1 旧 H5 必须改写

旧 Phase 2 的 H5 不能写 support。当前状态必须是：

```text
H5 = REJECTED_STATIC_PROXY / NOT_RETESTED_MONTHLY
```

### 9.2 H5 状态枚举

```python
VALID_H5_STATUS = {
    "REJECTED_STATIC_PROXY",
    "NOT_TESTED",
    "INSUFFICIENT_DATA",
    "SUPPORTED_MONTHLY_RESIDUAL",
    "SUPPORTED_MONTHLY_LEAD_LAG",
    "SUPPORTED_SHOCK_COOCCURRENCE",
    "MIXED",
    "INVALIDATED_BY_BUG",
}
```

### 9.3 报告规则

如果月度矩阵还没生成，H5 只能写：

```text
NOT_TESTED
```

如果只有旧静态 proxy，写：

```text
REJECTED_STATIC_PROXY
```

如果不同 view 结论不一致，写：

```text
MIXED
```

不能同一张表里出现 support 与 rejected。

### 9.4 禁止语句

报告中禁止：

- “语义图产生 alpha”
- “图因子有效”
- “可交易信号”
- “回测支持”
- “语义边预测收益”

允许：

- “描述性支持”
- “月度残差相关高于 matched random”
- “cross L1 semantic 高于 cross L1 random”
- “lead-lag association”
- “旧静态 proxy 不支持 H5”

---

## 10. 新增测试文件

### 10.1 `tests/test_phase2_1_mutual_logic.py`

```python
import numpy as np
import pandas as pd

from semantic_graph_research.graph_builder import derive_mutual_edges_fast
from semantic_graph_research.phase2_graph_layers import build_edge_candidates_fixed


def test_derive_mutual_edges_fast_small_case():
    edges = pd.DataFrame({
        "src_node_id": [0, 1, 0, 2],
        "dst_node_id": [1, 0, 2, 3],
        "rank": [1, 2, 2, 1],
        "score": [0.9, 0.8, 0.7, 0.6],
    })

    mutual_directed, mutual_pairs = derive_mutual_edges_fast(edges)

    assert len(mutual_directed) == 2
    assert len(mutual_pairs) == 1

    row = mutual_directed[
        (mutual_directed["src_node_id"] == 0) &
        (mutual_directed["dst_node_id"] == 1)
    ].iloc[0]

    assert row["reverse_rank"] == 2
    assert abs(row["reverse_score"] - 0.8) < 1e-6
    assert abs(row["score_mean"] - 0.85) < 1e-6


def test_build_edge_candidates_reverse_score():
    nodes = pd.DataFrame({
        "node_id": [0, 1, 2],
        "record_id": ["r0", "r1", "r2"],
        "stock_code": ["000001.SZ", "000002.SZ", "000003.SZ"],
    })

    neighbors = np.array([
        [1, 2, 1, 2, 1] * 20,
        [0, 2, 0, 2, 0] * 20,
        [1, 0, 1, 0, 1] * 20,
    ], dtype=np.int32)

    scores = np.linspace(0.99, 0.50, 300, dtype=np.float32).reshape(3, 100)

    # Make sure no duplicate (src,dst) in this synthetic case is hard with k=100 and 3 nodes,
    # so this particular test should use a smaller helper or expect duplicate failure.
```

对于 k=100 小样本，节点数太少会出现重复邻居，因此实际测试应使用独立 helper 或 n=101 的 synthetic neighbors。推荐写 n=101。

### 10.2 `tests/test_phase2_1_rank_band_naming.py`

```python
import numpy as np
from semantic_graph_research.phase2_graph_layers import assign_rank_band_exclusive

def test_rank_band_exclusive_names():
    ranks = np.array([1, 5, 6, 10, 11, 20, 21, 50, 51, 100])
    bands = assign_rank_band_exclusive(ranks).tolist()
    assert bands == [
        "rank_001_005",
        "rank_001_005",
        "rank_006_010",
        "rank_006_010",
        "rank_011_020",
        "rank_011_020",
        "rank_021_050",
        "rank_021_050",
        "rank_051_100",
        "rank_051_100",
    ]
```

### 10.3 `tests/test_phase2_1_market_profile_alignment.py`

断言：

- matched_market_nodes 不能是 0；
- median_total_mv 存在；
- 不再使用 total_market_cap；
- matched_market_nodes >= 5400。

### 10.4 `tests/test_phase2_1_report_schema.py`

断言：

- summary 无裸 `N/A`；
- h5_status 属于枚举集合；
- industry_comparison 不为空。

---

## 11. 本地执行顺序

建议按以下命令顺序：

```bash
# 1. 先跑新互惠逻辑测试
pytest -q tests/test_phase2_1_mutual_logic.py

# 2. 跑 rank 命名测试
pytest -q tests/test_phase2_1_rank_band_naming.py

# 3. 旧结果冻结
python scripts/16_phase2_old_results_audit.py

# 4. 四 view audit
python scripts/17_audit_multi_view_semantic_data.py

# 5. 四 view k100 graph
python scripts/18_build_multi_view_knn.py

# 6. 修复版 edge candidates
python scripts/19_build_fixed_edge_candidates.py

# 7. 检查 edge summary
python scripts/20_multi_view_industry_baselines.py
```

在第 6 步之后，必须人工检查：

```text
mutual_ratio 是否不再是 1.0
reverse_score 是否非空
rank_band 是否是 rank_001_005 等新命名
edge count 是否是 550200
near_duplicate_pairs 是否输出
```

---

## 12. 验收标准

修复完成后，必须满足：

| 检查项 | 标准 |
|---|---|
| edge count | 5502 × 100 |
| mutual ratio | 0 < ratio < 1 |
| reverse_score | mutual 边非空 |
| reverse_score zero ratio | 不应异常高 |
| rank band | 使用 rank_001_005 等 |
| topK flags | 使用 top_001_010 等 |
| self node edge | 0 |
| self stock edge | 0 |
| self record edge | 0 |
| near duplicate | 有 csv 输出 |
| matched_market_nodes | >= 5400 |
| industry_comparison | 非空 |
| H5 | 不得写 support，除非月度重验完成 |

---

## 13. 最小报告模板

`edge_candidate_repair_report.md` 建议包含：

```markdown
# Edge Candidate Repair Report - {view}

## 1. Inputs
- neighbors_k100
- scores_k100
- nodes
- view_key

## 2. Core Checks
| check | value | status |
|---|---:|---|
| n_nodes | 5502 | PASS |
| k | 100 | PASS |
| n_edges | 550200 | PASS |
| self_node_edges | 0 | PASS |
| self_stock_edges | 0 | PASS |
| mutual_ratio | ... | PASS |
| reverse_score_nonnull_ratio | ... | PASS |

## 3. Rank Bands
...

## 4. Near Duplicates
...

## 5. Invalidated Old Results
- old mutual_ratio=1.0 invalidated
- old reverse_score invalidated

## 6. Safe to Continue
yes/no
```

---

## 14. 最重要的实现原则

这次本地修复不是为了让 Phase 2.1 “能跑通”，而是为了让最关键的边关系表可信。只要 `edge_candidates_k100.parquet` 中 `is_mutual`、`reverse_rank`、`reverse_score`、`rank_band_exclusive`、`src/dst stock_code` 任一项不可信，后面的行业基准、hub、bridge、月度 lead-lag 都会建立在错误地基上。

因此，T2.1.3 的完成标准不是“文件生成了”，而是：

> 边表里的每一条关系都能被解释为：哪个 view、哪个 src、哪个 dst、几号邻居、分数多少、是否互惠、反向 rank/score 是什么、属于哪个 rank band、是否近重复风险。  

只有这个边表正确，Phase 2.1 才能继续进入金融解释。
