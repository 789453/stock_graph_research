# PHASE2.1 多语义 View 修复、稳健基准与月度时序研究完整规格文档

## 0. 文档定位

这份文档是一份连续完整的 Phase 2.1 主文档，用来替代前面被拆开的多段分析内容。它可以直接放入项目 `docs/` 目录，作为 Trae 或其他交互式 IDE AI 的主入口文档。

Phase 2 已经完成了第一轮语义图解释力研究，但 Phase 2 的结果并不能直接作为最终金融结论。它的价值在于证明了一套研究流程已经跑通，也暴露出几个必须修复的核心问题：mutual 逻辑错误、reverse_score 错误、size/liquidity 字段错配、rank band 命名混淆、H5 结论冲突、industry_comparison 为空、静态市场行为 proxy 被误读为市场共振检验。

Phase 2.1 的目标不是做新系统，也不是进入 GNN、回测、图因子或生产化。Phase 2.1 的目标是：

1. 修复 Phase 2 的关键算法和字段口径问题；
2. 将研究对象从单一 `application_scenarios_json` 切换为四个核心语义 view；
3. 对四个 view 分别建图、分别缓存、分别做行业/市值/流动性/市场行为基准；
4. 将市场行为研究升级到 2018 年以来的月度时间序列、残差相关和 lead-lag；
5. 保留大量可复查中间结果，以 md/json/csv/yaml/parquet/png 的形式沉淀研究资产；
6. 用严格证伪标准判断语义图是否具有金融解释价值，而不是过早宣称 alpha。

Phase 2.1 明确禁止：

- GNN；
- 回测；
- 图因子；
- Ollama 自动标注；
- 新 embedding；
- 生产化 API；
- 把 lead-lag 写成 alpha；
- 把静态语义边分数直接解释为市场行为共振；
- 让失败任务继续生成“成功”报告；
- 将不同语义 view 的缓存混在同一个目录中。

---

## 1. 当前仓库状态与 Phase 2.1 起点

最新主分支已经有 Phase 2 的脚本链、报告、缓存和状态文件，也已经把多个语义 view 的 `.meta.json` 放入 `a_share_semantic_dataset/npy` 目录。接下来要使用四个 view：

- `main_business_detail`
- `theme_text`
- `chain_text`
- `full_text`

这四个 view 的格式与旧的 `application_scenarios_json` 一致，仍然是 `*-all.npy` 与 `*-all.meta.json` 的配套结构，记录数和维度应继续遵守语义数据契约：5502 个节点、1024 维、float32、row_ids 与 records 对齐。

`docs` 目录下仍应参考：

- `docs/a_share_semantic_dataset_数据格式说明.md`
- `docs/tushare-data-README.md`

这两份文档不是新的工程依赖，但它们是理解语义数据结构、records 对齐、行情/日频指标字段的关键资料。Phase 2.1 的 Trae 执行顺序必须把它们纳入上下文。

---

## 2. Phase 2 旧结果的处理原则

Phase 2 的结果不能简单删除。它是研究过程资产，但必须被重新分类：

| 旧结果 | 状态 | 说明 |
|---|---|---|
| Phase 1 semantic audit | 保留 | 只代表 `application_scenarios_json` 历史 view |
| k20 graph stats | 部分保留 | 可作为早期结构参考 |
| k100 edge candidates | 部分失效 | 基础边数量可参考，但 mutual/reverse_score 失效 |
| mutual_ratio=1.0 | INVALIDATED_BY_BUG | 当前结果不可信 |
| reverse_score | INVALIDATED_BY_BUG | 字典 key 错误导致反向分数错误 |
| size_liquidity_summary | INVALIDATED_BY_BUG | `nodes_with_market_data=0` 与分桶并存，字段口径错误 |
| industry baseline | PARTIALLY_VALID | 单 view 行业 lift 可参考，但需四 view 重算 |
| domain baseline | REQUIRES_RECOMPUTE | 依赖 size/liquidity 修复 |
| hub/bridge | REQUIRES_RECOMPUTE | 依赖 mutual 修复和新 view |
| semantic_market_association | STATIC_PROXY_ONLY | 不是时序共振，不是 H5 完整检验 |
| PHASE2_RESEARCH_SUMMARY | REQUIRES_REWRITE | H5 支持/否定冲突，N/A 字段需消除 |

Phase 2.1 的第一个任务必须生成旧结果审计：

```text
outputs/reports/phase2_1/PHASE2_OLD_RESULTS_AUDIT.md
cache/semantic_graph/multi_view/manifests/phase2_old_result_audit.json
```

审计报告要明确：

- 哪些旧结果能作为历史参考；
- 哪些旧结果必须 invalidated；
- 哪些旧结果只作为 static proxy；
- 哪些旧结果必须重算；
- 哪些旧结论不能再写进最终总结。

---

## 3. 当前必须修复的核心问题

### 3.1 mutual 逻辑错误

当前 `phase2_graph_layers.py` 中 `build_edge_candidates` 的 mutual 逻辑存在方向性错误。旧逻辑先把 key 存成 `(dst, src)`，再用 `(dst, src)` 查询，导致每条边几乎都命中自己登记过的 key，最终 `mutual_ratio = 1.0`。

正确逻辑是：对每条原始边 `(u, v)`，检查反向边 `(v, u)` 是否存在。不能把查询 key 与存储 key 写成同方向。

修复后应输出：

- `is_mutual`
- `reverse_rank`
- `reverse_score`
- `score_mean_if_mutual`
- `n_mutual_edges_directed_rows`
- `n_mutual_pairs_unique`
- `reciprocity_ratio`

并强制 sanity check：

```python
if not (0.0 < mutual_ratio < 1.0):
    raise ValueError(f"invalid mutual_ratio={mutual_ratio}")
```

注意：这个断言不是理论定理，而是针对当前数据规模和 k=100 的现实 sanity check。若未来出现真正 mutual_ratio 接近 1 的 view，必须提供反向边验证表和样例，而不能静默通过。

### 3.2 reverse_score 字典 key 错误

当前 `score_dict = {i: edges.iloc[i]["score"] for i in range(len(edges))}`，key 是整数行号；后续却用 `(dst, src)` tuple 查询。这会导致 `reverse_score` 几乎全是 0，进而污染 `score_mean_if_mutual`。

修复原则：不要用整数 key 字典，应使用 self-merge 或 `(src, dst) -> (rank, score)` 字典。

### 3.3 `derive_mutual_edges` 性能隐患

旧 `derive_mutual_edges` 在每行 iterrows 中再做 DataFrame 布尔过滤，复杂度接近 O(E²)。四个 view、k=100 时每个 view 550,200 条边，总边数超过 220 万，这种写法不适合。

应改为 self-merge：

```python
def derive_mutual_edges_fast(directed_edges: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"src_node_id", "dst_node_id", "rank", "score"}
    missing = required - set(directed_edges.columns)
    if missing:
        raise ValueError(f"directed_edges missing columns: {missing}")

    edges = directed_edges.copy()
    edges["src_node_id"] = edges["src_node_id"].astype(np.int32)
    edges["dst_node_id"] = edges["dst_node_id"].astype(np.int32)
    edges["rank"] = edges["rank"].astype(np.int32)
    edges["score"] = edges["score"].astype(np.float32)

    reverse = edges[["src_node_id", "dst_node_id", "rank", "score"]].rename(columns={
        "src_node_id": "dst_node_id",
        "dst_node_id": "src_node_id",
        "rank": "reverse_rank",
        "score": "reverse_score",
    })

    merged = edges.merge(reverse, on=["src_node_id", "dst_node_id"], how="left", validate="one_to_one")
    mutual_directed = merged[merged["reverse_rank"].notna()].copy()
    mutual_directed["reverse_rank"] = mutual_directed["reverse_rank"].astype(np.int32)
    mutual_directed["reverse_score"] = mutual_directed["reverse_score"].astype(np.float32)
    mutual_directed["score_mean"] = (mutual_directed["score"] + mutual_directed["reverse_score"]) / 2.0

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

必须新增小样本测试，确认 0->1 与 1->0 互惠，0->2 不互惠，reverse_score 正确。

### 3.4 nodes index 隐式假设

旧逻辑使用：

```python
nodes.loc[src_node_ids, "stock_code"]
```

这要求 DataFrame index 恰好等于 node_id。稳健写法：

```python
def prepare_nodes_index(nodes: pd.DataFrame, n: int) -> pd.DataFrame:
    if "node_id" not in nodes.columns:
        raise ValueError("nodes must contain node_id")

    nodes_idx = nodes.set_index("node_id", drop=False).sort_index()
    expected = np.arange(n)
    actual = nodes_idx.index.to_numpy()

    if not np.array_equal(actual, expected):
        raise ValueError("nodes index is not exactly node_id 0..n-1")

    if nodes_idx["stock_code"].isna().any():
        raise ValueError("nodes contains missing stock_code")

    if nodes_idx["stock_code"].duplicated().any():
        dup = nodes_idx.loc[nodes_idx["stock_code"].duplicated(), "stock_code"].head(10).tolist()
        raise ValueError(f"duplicated stock_code in nodes, examples={dup}")

    return nodes_idx
```

### 3.5 rank band 命名混乱

Phase 2.1 必须区分两种概念：

**Exclusive rank band：**

- `rank_001_005`
- `rank_006_010`
- `rank_011_020`
- `rank_021_050`
- `rank_051_100`

**Cumulative topK：**

- `top_001_005`
- `top_001_010`
- `top_001_020`
- `top_001_050`
- `top_001_100`

`rank_006_010` 是第 6 到第 10 名，不是 top10。  
`top_001_010` 是第 1 到第 10 名累计。  
最终报告不允许写模糊的 `top10_mean`。

### 3.6 多个 band 的 max score=1.0000

多个 band 的 max 显示为 1.0000，可能是：

1. 四舍五入显示；
2. 真实近重复向量；
3. 文本模板重复；
4. self-neighbor 没剔除干净；
5. record_id 或 stock_code 重复；
6. 不同股票确实语义极近。

Phase 2.1 必须新增：

- exact duplicate vector check；
- near duplicate pair check，阈值 `score >= 0.999999`；
- `src_stock_code != dst_stock_code`；
- `src_record_id != dst_record_id`；
- 每个 view 输出 `near_duplicate_pairs.csv`；
- 每个 view 输出 `near_duplicate_score_histogram.png`。

如果 near duplicate 来自真实文本高度相似，不直接删除，但要在报告中标记。

### 3.7 `nodes_with_market_data=0`

当前 size/liquidity summary 中 `nodes_with_market_data=0` 与分桶并存。这说明不是市场数据真的没有匹配，而是字段统计口径有误。旧脚本 merge 后是 `total_mv`，summary 却使用 `total_market_cap`。

修复要求：

- 字段统一为 `median_total_mv`、`median_circ_mv`、`median_turnover_rate`、`median_amount`；
- 输出 `matched_market_nodes`；
- 输出 `unmatched_stock_codes_sample.csv`；
- 若 `matched_market_nodes < 5400`，任务失败；
- 若 matched 为 0，直接 raise；
- 不允许继续生成看似完整的分桶报告。

### 3.8 `industry_comparison:{}` 为空

Phase 2.1 必须补足：

- semantic vs global random；
- same L3 semantic vs same L3 random；
- same L3 + size bucket semantic vs matched random；
- same L3 + liquidity bucket semantic vs matched random；
- cross L1 semantic vs cross L1 random；
- cross L1 + size/liquidity matched random。

否则不能说语义边在行业、市值、流动性之外保留增量。

### 3.9 H5 口径冲突

H5 的正确当前状态：

> 在当前静态、非中性化、非时序 lead-lag 的定义下，语义边分数不能直接解释市场行为共振。

旧 Phase 2 的 H5 只能标记为：

- `REJECTED_STATIC_PROXY`
- 或 `NOT_RETESTED_MONTHLY`

不能再写 support。

---

## 4. 四个 view 的金融含义

### 4.1 `main_business_detail`

主营业务详细描述，最接近业务 peer network。它应主要用于：

- 同业可比公司；
- 申万三级行业内部细分；
- 业务模式相似；
- 盈利模式相似；
- 行业内残差结构。

预期：

- same L3 lift 较高；
- core 边同业纯度较高；
- 跨行业边比例较低；
- 月度收益相关若存在，可能更多来自行业和基本面共振；
- lead-lag 不一定强。

### 4.2 `theme_text`

主题文本，接近题材、叙事、概念暴露。它应主要用于：

- 题材扩散；
- 成交额冲击共现；
- 极端上涨共现；
- 市场关注点扩散；
- 跨行业概念连接。

预期：

- same L3 lift 不一定最高；
- cross L1 边可能更多；
- rank_021_050、rank_051_100 可能比 core 更有题材扩散含义；
- 收益残差相关不一定强，但成交冲击和 extreme up 可能更强。

### 4.3 `chain_text`

产业链文本，接近上下游、产业链位置、供需链条、技术路线。它应主要用于：

- 跨行业桥；
- 产业链风险传导；
- 上下游 lead-lag；
- 波动共振；
- 下跌共振；
- 事件冲击扩散。

预期：

- same L3 lift 可以不高；
- cross L1 semantic vs cross L1 random 是核心；
- lead-lag 比同期相关更重要；
- 去 hub 稳健性很关键。

### 4.4 `full_text`

综合文本，信息最丰富，也最混杂。它应主要用于：

- 综合语义基准；
- 多 view ensemble；
- 检查其他 view 的遗漏；
- 观察 hub 和 near duplicate 风险。

预期：

- score 可能整体更高；
- hub 可能更多；
- near duplicate 风险更高；
- 去 hub 后是否仍稳健是关键。

---

## 5. 新缓存结构

四个 view 必须隔离缓存：

```text
cache/semantic_graph/views/
  main_business_detail/{view_key}/
    audit/
    graph/
    edge_layers/
    baselines/
    hub_bridge/
    market_behavior/
    reports/
  theme_text/{view_key}/
  chain_text/{view_key}/
  full_text/{view_key}/
```

multi-view 汇总：

```text
cache/semantic_graph/multi_view/
  manifests/
  comparisons/
  baselines/
  market_behavior/
  reports/
```

输出目录：

```text
outputs/reports/phase2_1/{view}/
outputs/plots/phase2_1/{view}/
outputs/reports/phase2_1/multi_view/
outputs/plots/phase2_1/multi_view/
logs/phase2_1/{view}/
```

`view_key` 应由以下信息生成：

- view name；
- npy path；
- meta path；
- row_ids hash；
- vector shape；
- vector checksum；
- config version。

旧 `2eebde04e582` 只能作为 `application_scenarios_json` 历史结果，不再代表四 view。

---

## 6. Phase 2.1 任务清单

### T2.1.0 旧结果冻结

输出：

```text
outputs/reports/phase2_1/PHASE2_OLD_RESULTS_AUDIT.md
cache/semantic_graph/multi_view/manifests/phase2_old_result_audit.json
```

必须标记：

- mutual invalidated；
- reverse_score invalidated；
- size/liquidity invalidated；
- H5 conflict invalidated；
- static market association proxy only；
- application_scenarios_json historical only。

### T2.1.1 四 view 数据审计

每个 view 检查：

- shape；
- dtype；
- finite；
- zero norm；
- L2 norm；
- row_ids；
- records record_id 唯一；
- stock_code 唯一；
- row_ids 与 records 集合一致；
- row_ids 与向量行顺序绑定；
- near duplicate；
- as-of/fina 字段是否存在。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/audit/semantic_audit.json
cache/semantic_graph/views/{view}/{view_key}/audit/alignment_diagnostics.json
cache/semantic_graph/views/{view}/{view_key}/audit/near_duplicate_pairs.csv
outputs/reports/phase2_1/{view}/view_audit_report.md
```

### T2.1.2 四 view k100 构图

每个 view 使用 FAISS GPU、IndexFlatIP、L2 normalized vectors、k=100。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/graph/neighbors_k100.npz
cache/semantic_graph/views/{view}/{view_key}/graph/edges_directed_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/graph/edges_mutual_directed_rows_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/graph/mutual_pairs_unique_k100.parquet
```

### T2.1.3 修复版 edge candidates

输出字段：

- src_node_id；
- dst_node_id；
- src_stock_code；
- dst_stock_code；
- src_record_id；
- dst_record_id；
- rank；
- score；
- is_mutual；
- reverse_rank；
- reverse_score；
- score_mean_if_mutual；
- rank_band_exclusive；
- cumulative topK flags；
- src_top1_score；
- src_score_gap_from_top1；
- score percentile；
- duplicate risk flag。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_candidates_k100.parquet
cache/semantic_graph/views/{view}/{view_key}/edge_layers/edge_layer_summary.json
```

### T2.1.4 行业结构对比

每个 view 输出：

- same_l1_ratio_by_rank；
- same_l2_ratio_by_rank；
- same_l3_ratio_by_rank；
- same_l3_lift_by_rank；
- cross_l1_ratio_by_rank；
- cumulative topK 行业纯度；
- exclusive rank band 行业纯度。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/baselines/industry_by_rank.csv
cache/semantic_graph/multi_view/comparisons/industry_view_comparison.csv
```

### T2.1.5 市值/流动性 profile 修复

使用 DuckDB 或 Polars lazy scan 读取 2018—2026 必要列：

- `total_mv`
- `circ_mv`
- `turnover_rate`
- `amount`

计算：

- median_total_mv；
- median_circ_mv；
- median_turnover_rate；
- median_amount；
- log_total_mv；
- log_amount；
- size_bucket_10；
- liquidity_bucket_10；
- amount_bucket_10。

输出：

```text
cache/semantic_graph/multi_view/baselines/node_size_liquidity_profile.parquet
cache/semantic_graph/multi_view/baselines/size_liquidity_summary.json
outputs/reports/phase2_1/size_liquidity_repair_report.md
```

### T2.1.6 组合基准

每个 view、每个 rank band 输出：

- semantic vs global random；
- same L3 semantic vs same L3 random；
- same L3 + same size semantic vs matched random；
- same L3 + same liquidity semantic vs matched random；
- cross L1 semantic vs cross L1 random；
- cross L1 + size/liquidity matched random。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/baselines/domain_baseline_comparison.parquet
cache/semantic_graph/views/{view}/{view_key}/baselines/industry_comparison.json
```

### T2.1.7 score 对规模/流动性横截面回归

被解释变量：

- score；
- rank-adjusted score；
- local score percentile；
- mutual flag，可用 logistic 或线性概率模型做描述性分析。

解释变量：

- same_l1；
- same_l3；
- abs log market cap diff；
- abs log amount diff；
- same_size_bucket；
- same_liquidity_bucket；
- src/dst turnover；
- src/dst amount。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/baselines/score_size_liquidity_regression.csv
outputs/reports/phase2_1/{view}/score_exposure_regression_report.md
```

### T2.1.8 hub 与 bridge 多 view 研究

每个 view 输出：

- in_degree_k100；
- mutual_in_degree；
- cross_l1_in_degree；
- cross_l3_in_degree；
- neighbor_l3_entropy；
- score concentration；
- hub type candidate；
- bridge node score；
- top hubs；
- cross-industry bridge edges。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/hub_bridge/node_hub_scores.parquet
cache/semantic_graph/views/{view}/{view_key}/hub_bridge/top_hubs.csv
cache/semantic_graph/views/{view}/{view_key}/hub_bridge/cross_industry_bridge_edges.parquet
cache/semantic_graph/multi_view/comparisons/hub_overlap_by_view.csv
```

### T2.1.9 月度市场面板

从 2018 年开始构造月度面板：

- monthly_return；
- monthly_volatility；
- monthly_amount_change；
- monthly_turnover_change；
- market monthly return；
- L1 monthly return；
- L3 monthly return；
- market residual return；
- L1 residual return；
- L3 residual return；
- amount shock；
- turnover shock；
- extreme up/down flags。

输出矩阵：

```text
monthly_ret_matrix.npy
monthly_ret_resid_market.npy
monthly_ret_resid_l1.npy
monthly_ret_resid_l3.npy
monthly_amount_z_matrix.npy
monthly_vol_matrix.npy
```

### T2.1.10 月度 pair correlation 与 lead-lag

每个 view、每个边层、每个基准样本计算：

- same-month return correlation；
- market residual correlation；
- L1 residual correlation；
- L3 residual correlation；
- amount shock correlation；
- volatility correlation；
- src_leads_dst_1m/2m/3m；
- dst_leads_src_1m/2m/3m；
- lead_lag_asymmetry。

输出：

```text
cache/semantic_graph/views/{view}/{view_key}/market_behavior/monthly_pair_corr_by_layer.parquet
cache/semantic_graph/views/{view}/{view_key}/market_behavior/monthly_lead_lag_by_layer.parquet
cache/semantic_graph/views/{view}/{view_key}/market_behavior/monthly_baseline_comparison.json
```

### T2.1.11 多 view 总结

输出：

```text
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.md
outputs/reports/phase2_1/multi_view/MULTI_VIEW_RESEARCH_SUMMARY.json
outputs/plots/phase2_1/multi_view/view_comparison_dashboard.png
```

---

## 7. 月度矩阵算法设计

### 7.1 为什么用月度

日频对语义图可能太噪。语义关系更可能反映业务、产业链、主题和资金关注扩散，这些关系通常在周/月尺度上更稳定。月度矩阵还能显著降低 IO 和计算压力。

### 7.2 月度矩阵

设：

- N = 5502；
- T = 2018-01 至 2026-04，约 100 个月；
- E = 每个 view 550,200 条边。

构造 `R` 为 T×N 月收益矩阵。标准化：

```python
Rz = (R - np.nanmean(R, axis=0, keepdims=True)) / np.nanstd(R, axis=0, keepdims=True)
```

pair correlation：

```python
def pair_corr_between(A: np.ndarray, B: np.ndarray, src: np.ndarray, dst: np.ndarray, chunk: int = 200000):
    out = np.empty(len(src), dtype=np.float32)
    for s in range(0, len(src), chunk):
        e = min(s + chunk, len(src))
        a = A[:, src[s:e]]
        b = B[:, dst[s:e]]
        valid = np.isfinite(a) & np.isfinite(b)
        prod = np.where(valid, a * b, np.nan)
        out[s:e] = np.nanmean(prod, axis=0).astype(np.float32)
    return out
```

同期相关：

```python
same_month_corr = pair_corr_between(Rz, Rz, src, dst)
```

lead-lag：

```python
src_leads_dst_1m = pair_corr_between(Rz[:-1], Rz[1:], src, dst)
dst_leads_src_1m = pair_corr_between(Rz[:-1], Rz[1:], dst, src)
```

命名必须明确：`src_leads_dst_1m` 只是描述性方向关联，不是预测信号，不是 alpha。

---

## 8. 行业、市值、流动性基准

### 8.1 行业基准

必须计算：

- same_l1；
- same_l2；
- same_l3；
- cross_l1；
- same_l3 lift；
- cross_l1 semantic vs random。

随机基准不能只用 global random。因为行业本身是强结构，global random 会夸大语义图增量。

### 8.2 市值/流动性基准

输出：

- same_size_bucket_ratio_by_rank；
- same_liquidity_bucket_ratio_by_rank；
- same_amount_bucket_ratio_by_rank；
- score 对 log market cap、turnover、amount 的回归；
- 行业中性化后的桶内比较。

如果语义边倾向连接同规模、同流动性股票，那么 market behavior 的基准必须匹配这些结构。

### 8.3 随机基准构造

每个 semantic layer 都要构造相同 src 分布、相同边数量的 random edges。推荐：

- global_random；
- same_l3_random；
- same_l3_same_size_random；
- same_l3_same_liquidity_random；
- cross_l1_random；
- cross_l1_same_size_liquidity_random。

每个随机基准保存 manifest：

```json
{
  "baseline_name": "cross_l1_same_size_liquidity_random",
  "random_seed": 20260510,
  "n_repeats": 200,
  "edge_count": 0,
  "src_distribution_matched": true,
  "constraints": []
}
```

---

## 9. 结果解释模板

### 9.1 如果 `main_business_detail` 强

说明语义图作为 peer network 有价值，适合未来研究可比公司、行业内相对关系、估值相似和风险同源。它更像经济结构图，而不一定是价格行为图。

如果同 L3 lift 高但月度残差相关弱，应解释为：该 view 主要提供经济结构，不直接提供市场共振。

### 9.2 如果 `theme_text` 强

说明市场主题文本更贴近交易叙事，适合未来事件观察、题材扩散和成交冲击预警。如果成交冲击共现强于收益残差相关，说明它更偏市场关注度而不是收益方向。

### 9.3 如果 `chain_text` 强

说明产业链语义能捕捉跨行业传导，适合未来研究上下游风险、订单链、供应链冲击和政策冲击扩散。若 cross L1 lead-lag 高于 random，说明它可能捕捉到产业链方向性关联。

### 9.4 如果 `full_text` 强

说明综合文本有信息，但必须判断它是否被 hub 和 near duplicate 污染。full_text 强不等于最好，只有去 hub 后仍稳健才说明它具有可靠信息增益。

### 9.5 如果所有 view 在市场行为上都弱

这不是失败。说明语义图更适合经济结构解释，而不适合直接进入交易辅助。下一步应转向人工边类型标注、事件窗口研究或语义数据质量审计。

---

## 10. 多 view 组合解释

### 10.1 multi-view consensus edges

如果某条边在多个 view 中都强，称为 consensus edge。它可能更稳定，但需要解释是哪类共识：

- main + full：业务相似；
- theme + full：主题叙事相似；
- chain + full：产业链关系；
- main + theme + chain：核心产业主题；
- 只有 full：需要检查是否信息混杂或泛化 hub。

输出：

```text
multi_view_edge_overlap.parquet
multi_view_consensus_edges.csv
edge_overlap_upset.png
```

### 10.2 view disagreement edges

如果某条边只在一个 view 中强，也很有研究价值：

- main only：传统同行；
- theme only：题材关系；
- chain only：产业链关系；
- full only：综合文本关系，需谨慎。

输出：

```text
main_only_edges.csv
theme_only_edges.csv
chain_only_edges.csv
full_only_edges.csv
cross_view_disagreement_edges.csv
```

---

## 11. H5 结论模板

H5-Monthly 定义：

> 在行业、市值、流动性中性化与匹配随机基准之后，至少一个语义 view 的某类边在月度收益残差、波动、成交冲击或 lead-lag 上显著高于对应基准。

H5 状态只能是：

- `REJECTED_STATIC_PROXY`
- `NOT_TESTED`
- `INSUFFICIENT_DATA`
- `SUPPORTED_MONTHLY_RESIDUAL`
- `SUPPORTED_MONTHLY_LEAD_LAG`
- `SUPPORTED_SHOCK_COOCCURRENCE`
- `MIXED`
- `INVALIDATED_BY_BUG`

错误写法：

```text
语义图可以解释市场行为。
```

正确写法：

```text
在 chain_text 的 cross L1 semantic edges 中，rank_021_050 边的 src_leads_dst_1m 高于 cross L1 random 和 cross L1 + size/liquidity matched random，且去除 top hub 后仍存在。因此，H5 在 chain_text 的跨行业 lead-lag 子问题上得到描述性支持。
```

---

## 12. 跨行业边如何证明有价值

“跨行业边很多”不是价值证明。必须满足至少一条：

1. cross L1 semantic 的月度残差相关高于 cross L1 random；
2. chain_text 的 cross L1 lead-lag 高于 cross L1 random；
3. theme_text 的 cross L1 成交冲击共现高于 random；
4. 去 hub 后仍然成立；
5. size/liquidity matched 后仍成立；
6. 不是单一行业或单一 hub 驱动。

如果跨行业边只是在数量上多，但不高于随机跨行业边，结论应是：

> 跨行业语义边只是语义空间扩展，不是已验证金融结构。

---

## 13. hub 稳健性

hub 不是单纯噪声，也不是天然有效。它可能是产业中心、题材中心、平台公司、综合集团，也可能是文本泛化。

### 13.1 hub removal

对每个 view 输出三套结果：

- all_edges；
- remove_top_1pct_hub_edges；
- remove_top_5pct_hub_edges。

hub 排序指标：

- in_degree_k100；
- cross_l1_in_degree；
- neighbor_l3_entropy；
- score_concentration；
- pagerank，可选。

### 13.2 hub 稳健性解释

如果去 hub 后结果仍存在：

> 语义边层效果不是少数中心节点驱动，具有更强稳健性。

如果去 hub 后结果消失：

> 当前结果高度依赖 hub，不能解释为普遍边层效应，需要回到 hub 样例判断其经济含义。

输出：

```text
hub_removed_industry_lift.csv
hub_removed_monthly_corr.csv
hub_removed_lead_lag.csv
hub_removed_baseline_delta.csv
```

---

## 14. score 对规模/流动性回归

回归不是为了预测，而是为了判断语义相似是否被规模、流动性、行业机械解释。

推荐模型：

```text
score_uv = a
         + b1 * same_l1_uv
         + b2 * same_l3_uv
         + b3 * abs(log_mv_u - log_mv_v)
         + b4 * abs(log_amount_u - log_amount_v)
         + b5 * same_size_bucket_uv
         + b6 * same_liquidity_bucket_uv
         + e_uv
```

解释：

- same_l3 系数强：语义分数吸收行业结构；
- abs log market cap diff 为负：语义边偏向同规模公司；
- liquidity 变量显著：交易活跃度或披露充分度可能影响语义距离；
- size/liquidity 控制后 score 仍有增量：语义图不是简单规模/流动性近邻。

---

## 15. 报告结构

每个 view 报告：

```text
# {view} Phase 2.1 Research Report

## 1. View 定义与金融假设
## 2. 数据审计
## 3. k100 图结构
## 4. mutual 与 rank band
## 5. 行业 L1/L2/L3 解释
## 6. 市值/流动性暴露
## 7. 随机基准与 matched baseline
## 8. hub 与 bridge
## 9. 月度市场行为
## 10. lead-lag
## 11. 去 hub 稳健性
## 12. 证伪情况
## 13. view 的适用场景
## 14. 不应使用的场景
## 15. 下一步建议
```

multi-view 报告：

```text
# Multi-view Semantic Graph Research Summary

## 1. 总结论
## 2. 四 view 数据质量对比
## 3. 四 view 图结构对比
## 4. 行业解释力对比
## 5. 市值/流动性暴露对比
## 6. 跨行业桥对比
## 7. hub 污染对比
## 8. 月度残差相关对比
## 9. lead-lag 对比
## 10. view-specific 结论
## 11. H5 最终状态
## 12. 旧 Phase 2 结果修正
## 13. Phase 3 是否允许
```

---

## 16. JSON summary schema

每个 view 的 summary 必须使用固定 schema，不允许关键字段 N/A。

```json
{
  "view_name": "chain_text",
  "view_key": "...",
  "status": "success",
  "n_nodes": 5502,
  "n_edges_k100": 550200,
  "mutual_ratio": 0.0,
  "near_duplicate_pairs_count": 0,
  "industry": {
    "same_l1_ratio_rank_001_005": 0.0,
    "same_l2_ratio_rank_001_005": 0.0,
    "same_l3_ratio_rank_001_005": 0.0,
    "same_l3_lift_rank_001_005": 0.0
  },
  "size_liquidity": {
    "matched_market_nodes": 0,
    "same_size_bucket_ratio_rank_001_005": 0.0,
    "same_liquidity_bucket_ratio_rank_001_005": 0.0,
    "same_amount_bucket_ratio_rank_001_005": 0.0
  },
  "baselines": {
    "industry_comparison_status": "computed",
    "cross_l1_semantic_vs_random_delta": 0.0,
    "same_l3_semantic_vs_matched_random_delta": 0.0
  },
  "hub_bridge": {
    "hub_count": 0,
    "bridge_node_count": 0,
    "hub_removed_stability": "not_computed"
  },
  "market_behavior": {
    "monthly_resid_corr_semantic_vs_random_delta": 0.0,
    "best_lead_lag_metric": "src_leads_dst_1m",
    "best_lead_lag_delta": 0.0,
    "amount_shock_delta": 0.0
  },
  "h5_status": "NOT_TESTED",
  "warnings": []
}
```

缺字段应写结构化状态：

```json
{
  "status": "not_computed",
  "reason": "monthly panel not available"
}
```

不允许裸写 `N/A`。

---

## 17. CSV 输出清单

每个 view：

```text
audit/near_duplicate_pairs.csv
edge_layers/edge_score_by_rank.csv
edge_layers/mutual_ratio_by_rank.csv
baselines/industry_by_rank.csv
baselines/domain_baseline_comparison.csv
baselines/score_size_liquidity_regression.csv
hub_bridge/top_hubs.csv
hub_bridge/cross_industry_bridge_edges_sample.csv
market_behavior/monthly_pair_corr_by_layer.csv
market_behavior/monthly_lead_lag_by_layer.csv
reports/view_key_metrics.csv
```

multi-view：

```text
multi_view/comparisons/industry_view_comparison.csv
multi_view/comparisons/hub_overlap_by_view.csv
multi_view/comparisons/monthly_behavior_view_comparison.csv
multi_view/comparisons/lead_lag_view_comparison.csv
multi_view/comparisons/view_final_decision_matrix.csv
```

---

## 18. 可视化清单

每个 view 至少输出：

```text
score_by_rank_{view}.png
score_distribution_by_rank_band_{view}.png
mutual_ratio_by_rank_{view}.png
same_l3_lift_by_rank_{view}.png
same_size_bucket_ratio_by_rank_{view}.png
same_liquidity_bucket_ratio_by_rank_{view}.png
cross_l1_ratio_by_rank_{view}.png
hub_indegree_distribution_{view}.png
hub_entropy_vs_indegree_{view}.png
cross_industry_bridge_heatmap_{view}.png
monthly_residual_corr_by_layer_{view}.png
monthly_lead_lag_heatmap_{view}.png
semantic_vs_random_baseline_{view}.png
score_exposure_regression_coefficients_{view}.png
near_duplicate_score_histogram_{view}.png
```

multi-view：

```text
same_l3_lift_by_view.png
cross_l1_ratio_by_view.png
mutual_ratio_by_view.png
hub_overlap_heatmap.png
monthly_residual_corr_by_view.png
lead_lag_by_view.png
view_final_decision_matrix.png
view_comparison_dashboard.png
```

图表原则：

- 图表只读缓存；
- 不重跑 FAISS；
- 不重读全量 parquet；
- 图名和图内标签用英文；
- 每张图只表达一个问题；
- 图名必须包含 view。

---

## 19. 单元测试清单

新增测试：

```text
tests/test_phase2_1_mutual_logic.py
tests/test_phase2_1_rank_band_naming.py
tests/test_phase2_1_market_profile_alignment.py
tests/test_phase2_1_view_cache_isolation.py
tests/test_phase2_1_monthly_pair_corr.py
tests/test_phase2_1_report_schema.py
```

核心断言：

- mutual 不应全 True；
- reverse_score 对小样本正确；
- rank_006_010 不等于 top_001_010；
- nodes_with_market_data 不为 0；
- matched_market_nodes >= 5400；
- 四 view cache 路径互不覆盖；
- monthly pair corr 对小矩阵正确；
- summary 无裸 N/A；
- H5 状态属于枚举集合。

---

## 20. Phase 3 进入条件

Phase 2.1 完成后不能自动进入 Phase 3。只有满足以下条件之一，才允许讨论下一阶段：

- 至少一个 view 在 matched random 后月度残差相关显著；
- cross L1 semantic 高于 cross L1 random；
- chain_text 或 theme_text 的 lead-lag 高于随机基准；
- 去 hub 后仍成立；
- size/liquidity matched 后仍成立；
- 结果不是单一行业或单一 hub 驱动。

如果出现以下情况，不允许进入 Phase 3：

- H5 仍是 REJECTED_STATIC_PROXY；
- 所有 view 在 matched random 后无增量；
- 结果完全由 hub 驱动；
- size/liquidity 匹配后消失；
- 行业残差后消失；
- lead-lag 只在少数极端样本中出现；
- near duplicate 严重污染 full_text。

即使进入 Phase 3，也只能先做：

- 观察型图邻居统计；
- 事件窗口研究；
- 简单邻居描述指标；
- 人工样例复核；
- 交易辅助面板。

仍不做：

- GNN；
- 大规模回测；
- 多因子挖掘；
- 组合净值；
- 自动调参寻找收益。

---

## 21. Trae 执行规程

每次打开新会话，先读：

```text
PROJECT_STATE.md
docs/a_share_semantic_dataset_数据格式说明.md
docs/tushare-data-README.md
docs/PHASE2_1_COMPLETE_CONTINUOUS_SPEC.md
configs/phase2_1_multi_view_research.yaml
```

然后一次只做一个任务：

1. 旧结果冻结；
2. 四 view audit；
3. 四 view k100 graph；
4. 修复版 edge candidates；
5. 行业结构；
6. size/liquidity 修复；
7. matched baseline；
8. score regression；
9. hub/bridge；
10. monthly panel；
11. monthly pair corr and lead-lag；
12. multi-view summary。

每个任务必须输出：

- manifest；
- summary json；
- summary md；
- log；
- csv/parquet；
- 如有图则输出 png。

失败时写 failed manifest，不准继续生成 success summary。

---

## 22. 最终验收标准

Phase 2.1 完成后，必须能回答：

1. 四个 view 的行业解释力谁最强？
2. 四个 view 的跨行业桥谁最有结构？
3. theme_text 是否更适合题材/成交冲击？
4. chain_text 是否更适合跨行业 lead-lag？
5. main_business_detail 是否更适合同行业内 peer？
6. full_text 是否有信息增益，还是 hub/重复风险更高？
7. size/liquidity 中性化后，语义边还有没有增量？
8. cross industry semantic edges 是否高于 cross industry random？
9. H5 在月度残差相关和 lead-lag 下是支持、拒绝，还是证据不足？
10. 哪些旧 Phase 2 结果被修复后保留，哪些废弃？
11. 是否允许进入 Phase 3？
12. 如果不允许，下一步应回到哪类研究？

如果这些问题没有答完，不进入 Phase 3。

---

## 23. 最重要的总纲

Phase 2.1 的核心不是把报告写得更漂亮，而是修正研究证据。

旧 Phase 2 证明了：语义图很可能是强经济结构图。  
Phase 2.1 要检验的是：四个不同语义 view 中，是否有某些边层在行业、市值、流动性之外，对月度市场行为、风险传导、成交冲击或 lead-lag 有描述性增量。

最终如果支持，也只能写“描述性支持”；如果不支持，也不是失败，而是说明语义图更适合经济结构解释，不适合进入交易信号研究。
