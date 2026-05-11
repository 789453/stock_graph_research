下面我把它改成“真正能落地改代码”的版本。先说明一个重要前提：我这次重新核对 GitHub 公开 `main` 分支时，`scripts/` 页面当前只显示 `00_audit_semantic_data.py` 到 `15_phase2_summary_report.py`，而你上传的 `phase2.2问题解决专题.md` 明确讨论了 `21_phase2_2_code_consistency_audit.py` 到 `31_phase2_2_exhaustive_viz_engine.py` 等 Phase 2.2 脚本。也就是说，**你上传的文档对应的是一个比当前 GitHub 页面可见脚本更“新”的 Phase 2.2 方案或分支状态；当前公开 `main` 上我能看到的 scripts 清单仍是 Phase 1/Phase 2 主线脚本**。GitHub 当前 `scripts/` 目录列出的文件包括 `00_audit_semantic_data.py`、`01_build_nodes.py`、`02_build_semantic_knn.py`、`03_compute_graph_diagnostics.py`、`04_plot_from_cache.py`、`05_market_alignment_census.py`、`06_phase1_repair_and_test_report.py`、`07_build_extended_edge_candidates.py` 到 `15_phase2_summary_report.py`。([GitHub][1]) 你上传的文档我会作为 Phase 2.2 修改目标的依据。

---

# 一、总判断：现在最大问题不是“脚本不够”，而是“主路径不唯一、证据链不闭合、报告比代码乐观”

这个项目已经有一个清晰研究方向：用语义 embedding 构建股票近邻图，再验证语义边是否具有行业解释、结构解释和市场共振解释。但当前问题集中在四层：

第一，**脚本阶段混杂**。公开仓库可见的 `scripts/` 是 `00-15` 的 Phase 1/2 脚本；你上传文档中讨论的是 Phase 2.2 的 `21-31` 系列脚本。必须把“正式 pipeline”从探索脚本、补丁脚本、临时绘图脚本中拆出来，否则报告可能引用了不同版本数据。

第二，**节点顺序和矩阵行号对齐风险非常高**。这是我认为最高优先级的潜在灾难。只要边表的 `src_node_id/dst_node_id` 来自语义 nodes 顺序，而残差矩阵用 `sorted(stock_code)` 重新排序，边级市场指标就可能全部错配。这个错误不会报错，shape 也正常，但结果完全失真。

第三，**H5 市场共振检验容易出现伪显著**。边很多，月份很多，直接对几十万条边做普通 t-test 或用“边数量”当有效样本，会把高度相关的边当成独立样本，p-value 会虚假变小。必须使用 matched random edges、month/block bootstrap、node-cluster 或 permutation。

第四，**报告生成脚本缺少一致性闸门**。之前 Phase 2 报告里已经出现过 H5 同时“支持”和“否定”的冲突；Phase 2.2 文档里也指出“commit 说 plots not、报告说 145 张图”的状态矛盾。报告脚本不能只是拼 Markdown，必须强制读取 manifest、图表索引、统计检验结果和审计结果，一旦关键字段冲突就 fail。

---

# 二、公开 `scripts/` 下文件职责与应如何改

## 0. `00_audit_semantic_data.py`

**当前职责**：读取配置、加载语义 view、审计 NPY/metadata/records 对齐，检查行数、维度、dtype、非有限值、零范数、row_id 唯一性、alignment 状态，并保存 audit 和 manifest。代码中确实调用了 `load_semantic_view` 和 `audit_semantic_bundle`，然后写入 `manifest.json`。([GitHub][2])

**问题隐患**：

它现在更像一次性审计脚本，不够适合作为 Phase 2.2 多 view pipeline 的入口。Phase 2.2 需要支持多个 view，比如 `application_scenarios_json`、`business_model_json`、`products_services_json`、`industry_chain_position_json`，不能只靠固定 config 隐含决定。

**具体修改**：

增加 CLI 参数：

```python
parser.add_argument("--view", required=False, default=None)
parser.add_argument("--config", default="configs/phase1_semantic_graph.yaml")
parser.add_argument("--out-root", default="cache/semantic_graph/phase2_2")
parser.add_argument("--strict", action="store_true")
```

audit 输出必须包含：

```json
{
  "view": "...",
  "records_path": "...",
  "npy_path": "...",
  "meta_path": "...",
  "records_sha256": "...",
  "npy_sha256": "...",
  "meta_sha256": "...",
  "rows": 5502,
  "dim": 1024,
  "row_id_alignment_ok": true,
  "stock_code_unique_ok": true,
  "finite_ok": true,
  "zero_norm_count": 0,
  "created_at_utc": "...",
  "script": "00_audit_semantic_data.py",
  "git_commit": "..."
}
```

必须新增一个强断言：`meta["row_ids"]` 与 `records["record_id"]` 的顺序完全一致，而不是只检查集合一致。因为后续 node_id、向量行号、边表行号全部依赖这个顺序。

---

## 1. `01_build_nodes.py`

**当前职责**：构建 nodes 表，把语义记录转成图节点。公开脚本目录确实包含该文件。([GitHub][1])

**问题隐患**：

`nodes.parquet` 是全项目最关键的事实表。它必须定义唯一、稳定的 `node_id -> stock_code -> record_id -> vector_row` 映射。只要这个表在后续某个脚本里被重新排序，整个边表和矩阵都会错位。

**具体修改**：

`nodes.parquet` 应固定以下字段：

```text
node_id
vector_row
record_id
stock_code
stock_name
asof_date
view
sw_l1_name
sw_l2_name
sw_l3_name
```

并加入不可妥协断言：

```python
assert (nodes["node_id"].to_numpy() == np.arange(len(nodes))).all()
assert (nodes["node_id"] == nodes["vector_row"]).all()
assert nodes["stock_code"].is_unique
assert nodes["record_id"].is_unique
```

输出 `nodes_manifest.json`：

```json
{
  "node_count": 5502,
  "node_id_policy": "node_id equals vector_row from meta row_ids order",
  "sort_policy": "no resort after semantic row order",
  "stock_code_unique": true,
  "record_id_unique": true
}
```

**不要**在这里用 `sort_values("stock_code")` 重新排序。后续市场矩阵可以按 node_id 对齐 stock_code，但不能反过来让 stock_code 排序覆盖 node_id。

---

## 2. `02_build_semantic_knn.py`

**当前职责**：构建语义 kNN。`graph_builder.py` 显示底层是 FAISS：复制 vectors、`faiss.normalize_L2`、`IndexFlatIP`，搜索 `k+1` 个邻居以剔除 self-neighbor，因此本质是余弦相似度近邻图。([GitHub][3])

**问题隐患**：

`gpu_device=0` 默认会在无 GPU 环境失败；另外，如果向量中有零范数或 NaN，FAISS 结果可能不可解释。虽然 `00` 脚本审计了，但 `02` 不应完全信任上游。

**具体修改**：

把 GPU 改成自动 fallback：

```python
def build_faiss_knn(vectors, k, gpu_device=None):
    vectors = np.asarray(vectors, dtype=np.float32)
    assert np.isfinite(vectors).all()
    norms = np.linalg.norm(vectors, axis=1)
    assert (norms > 0).all()

    vectors_copy = vectors.copy()
    faiss.normalize_L2(vectors_copy)

    index = faiss.IndexFlatIP(vectors_copy.shape[1])
    if gpu_device is not None and gpu_device >= 0:
        try:
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, gpu_device, index)
        except Exception as e:
            print(f"[WARN] GPU unavailable, fallback to CPU: {e}")

    index.add(vectors_copy)
    scores, indices = index.search(vectors_copy, k + 1)
    ...
```

输出必须包含 `knn_manifest.json`：

```json
{
  "k": 100,
  "metric": "cosine_via_l2_normalized_inner_product",
  "self_neighbor_removed": true,
  "indices_shape": [5502, 100],
  "scores_shape": [5502, 100],
  "score_min": ...,
  "score_mean": ...,
  "score_max": ...,
  "gpu_used": false
}
```

---

## 3. `03_compute_graph_diagnostics.py`

**当前职责**：计算图诊断指标。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

诊断不能只看 degree、reciprocity、component。Phase 2.2 的风险在于重复文本、hub 污染、行业复制、node_id 错位、分数饱和。因此诊断脚本要扩展为“结构 + 数据质量 + 金融口径”三类。

**具体修改**：

增加这些输出：

```text
score_by_rank.csv
same_l1_by_rank.csv
same_l2_by_rank.csv
same_l3_by_rank.csv
mutual_ratio_by_rank.csv
in_degree_distribution.csv
hub_top_nodes.csv
score_gt_098_pairs.csv
duplicate_text_or_embedding_suspects.csv
```

新增检查：

```python
assert edges["src_node_id"].between(0, len(nodes)-1).all()
assert edges["dst_node_id"].between(0, len(nodes)-1).all()
assert not (edges["src_node_id"] == edges["dst_node_id"]).any()
assert edges.groupby("src_node_id").size().nunique() == 1
```

特别要输出 `score >= 0.98` 的边，用于人工判断是否存在模板文本、重复业务描述、同集团复制、embedding 饱和。

---

## 4. `04_plot_from_cache.py`

**当前职责**：从 cache 读取数据画图。公开脚本目录包含该文件。([GitHub][1])

**问题隐患**：

之前的图表存在标题模板复用问题，比如 PCA 提示出现在非 PCA 图中。Phase 2.2 里如果要生成很多图，必须避免“图是生成了，但标题、口径、数据源错了”。

**具体修改**：

每张图必须对应一个 metadata：

```json
{
  "plot_file": "score_by_rank.png",
  "source_data": "cache/.../score_by_rank.csv",
  "source_sha256": "...",
  "title": "...",
  "x": "rank",
  "y": "cosine_score",
  "created_at": "...",
  "script": "04_plot_from_cache.py"
}
```

同时新增图表审计：

```python
assert plot_path.exists()
assert plot_path.stat().st_size > 10_000
assert metadata["source_sha256"] == sha256(source_data)
```

对于 Phase 2.2，不建议继续让 `04_plot_from_cache.py` 承担所有图；应把它改成基础绘图工具，正式图表由 `31_xxx` 系列调用统一函数。

---

## 5. `05_market_alignment_census.py`

**当前职责**：市场数据覆盖审计。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

不能只输出“覆盖率 99.8%”。必须区分：

```text
静态 profile 覆盖率
日频行情覆盖率
月度面板有效覆盖率
指定研究窗口覆盖率
剔除停牌/退市/缺失后的覆盖率
```

否则报告中“覆盖率”会互相冲突。

**具体修改**：

输出：

```text
market_alignment_static.csv
market_alignment_daily.csv
market_alignment_monthly.csv
missing_stock_codes.csv
low_trading_days_stock_months.csv
```

关键字段：

```text
stock_code
in_nodes
has_daily
first_trade_date
last_trade_date
n_trading_days_2018_2026
n_valid_months
missing_reason
```

最低断言：

```python
assert node_count == len(nodes)
assert aligned_stock_count / node_count >= 0.95
```

如果缺失不是 0，报告必须列出前 50 个缺失股票和原因。

---

## 6. `06_phase1_repair_and_test_report.py`

**当前职责**：Phase 1 修复和测试报告。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

这个脚本不应该继续参与 Phase 2.2 主路径。它可以保留为历史报告，但不要让 Phase 2.2 最终报告直接读取它的结论，避免旧口径污染新口径。

**具体修改**：

改名或标记为 legacy：

```text
scripts/legacy/06_phase1_repair_and_test_report.py
```

在文件顶部写：

```python
"""
LEGACY ONLY.
Do not use this script for Phase 2.2 production reports.
"""
```

---

## 7. `07_build_extended_edge_candidates.py`

**当前职责**：构建 k=100 扩展候选边。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

之前最大问题是 rank band 语义混乱：文档里 `strong=top10`，代码里可能是 `rank 6-10`。这会导致表、图、报告解释全乱。

**具体修改**：

必须同时生成两套字段：

```python
# 互斥物理分箱
rank_band_exclusive:
  rank_001_005
  rank_006_010
  rank_011_020
  rank_021_050
  rank_051_100

# 累计 topK flag
is_top005
is_top010
is_top020
is_top050
is_top100
```

不要再用含糊标签：

```text
core
strong
stable
context
extended
```

除非报告明确说明它们是互斥还是累计。

建议实现：

```python
def assign_rank_band_exclusive(rank: int) -> str:
    if 1 <= rank <= 5:
        return "rank_001_005"
    if 6 <= rank <= 10:
        return "rank_006_010"
    if 11 <= rank <= 20:
        return "rank_011_020"
    if 21 <= rank <= 50:
        return "rank_021_050"
    if 51 <= rank <= 100:
        return "rank_051_100"
    raise ValueError(f"rank out of range: {rank}")

edges["is_top005"] = edges["rank"] <= 5
edges["is_top010"] = edges["rank"] <= 10
edges["is_top020"] = edges["rank"] <= 20
edges["is_top050"] = edges["rank"] <= 50
edges["is_top100"] = edges["rank"] <= 100
```

---

## 8. `08_edge_layer_statistics.py`

**当前职责**：统计不同边层的分数、数量、行业比例等。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

如果统计脚本只 groupby `rank_band`，它会继续继承 rank band 混乱。另一个风险是只输出均值，没有随机基准和置信区间。

**具体修改**：

输出两类表：

```text
edge_stats_by_exclusive_rank_band.csv
edge_stats_by_cumulative_topk.csv
```

每个表必须包含：

```text
n_edges
score_mean
score_median
score_p25
score_p75
mutual_ratio
same_l1_ratio
same_l2_ratio
same_l3_ratio
cross_l1_ratio
random_same_l1_ratio
random_same_l2_ratio
random_same_l3_ratio
same_l3_lift
```

这样报告里就不会再出现 “Core L3 lift=58x/71x” 两套口径互相打架。

---

## 9. `09_industry_baseline.py`

**当前职责**：行业基准。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

当前行业对齐大概率使用“当前申万行业”。这可以用于静态解释，但不能装作历史行业真值。2018-2026 的研究中，行业分类、主营变化、退市、重组都会导致当前标签回填历史的问题。

**具体修改**：

报告字段必须写清楚：

```json
{
  "industry_label_type": "current_sw_industry",
  "historical_industry_available": false,
  "interpretation_limit": "static semantic structure only, not historical industry membership"
}
```

新增 matched random：

```python
# 对每条语义边，随机抽取一个同 src 行业/市值桶/流动性桶约束下的 dst
# 形成同分布随机边
```

最低要求：

```text
semantic same_l3 ratio
random same_l3 ratio
lift
permutation p-value
```

---

## 10. `10_size_liquidity_domain.py`

**当前职责**：市值/流动性域分析。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

“同规模比例 6-8%”本身不能说明低或高，必须知道桶数量和随机基准。比如十等分桶随机同桶约 10%，五等分桶随机同桶约 20%。

**具体修改**：

输出：

```text
size_bucket_count
liquidity_bucket_count
same_size_ratio
random_same_size_ratio
same_liquidity_ratio
random_same_liquidity_ratio
lift
```

市值、成交额、换手率建议 winsorize：

```python
def winsorize_s(s, lower=0.01, upper=0.99):
    lo, hi = s.quantile([lower, upper])
    return s.clip(lo, hi)
```

并明确使用静态 profile 还是月度动态 profile。

---

## 11. `11_domain_neighbor_analysis.py`

**当前职责**：域内/域间邻居分析。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

如果只是按行业、市值、流动性分组看均值，它很容易和 `09/10` 重复。Phase 2.2 里它应承担“解释语义边类型”的任务，而不是又输出一张均值表。

**具体修改**：

它应该输出边类型标签：

```text
same_l3_peer
same_l1_cross_l3
cross_l1_high_score
cross_l1_bridge
size_liquidity_similar
size_liquidity_different
potential_template_duplicate
```

为后续 `12_hub_bridge_research.py` 和 H5 检验提供分组。

---

## 12. `12_hub_bridge_research.py`

**当前职责**：hub 和跨行业桥分析。公开目录包含该脚本。([GitHub][1])

**问题隐患**：

hub 很容易混入文本模板污染。高入度节点可能是产业中心，也可能只是公司描述非常泛化，比如“广泛应用于工业、消费、医疗、能源”等。桥节点也可能只是行业标签粗糙导致的假桥。

**具体修改**：

hub 输出不能只有 in-degree。应包含：

```text
node_id
stock_code
stock_name
in_degree
out_degree
mutual_in_degree
mean_in_score
mean_out_score
neighbor_l1_entropy
neighbor_l3_entropy
duplicate_score_gt_098_count
hub_type_candidate
```

`hub_type_candidate` 可以先规则化：

```python
if neighbor_l1_entropy < low and same_l1_ratio > high:
    hub_type = "industry_center"
elif neighbor_l1_entropy > high and mean_in_score > threshold:
    hub_type = "cross_industry_platform"
elif duplicate_score_gt_098_count > threshold:
    hub_type = "template_duplicate_suspect"
else:
    hub_type = "mixed_or_uncertain"
```

桥边输出：

```text
src
dst
score
rank
src_l1
dst_l1
src_l3
dst_l3
is_mutual
score_percentile
market_resid_corr
random_baseline_corr
```

---

## 13. `13_market_behavior_panel.py`

**当前职责**：构建 2018-2026 市场行为面板。公开代码显示它读取 `nodes.parquet`，再读取本地 `/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily.parquet`，过滤节点股票和研究窗口，按年度计算收益、波动率、成交量、成交额、最大回撤和交易天数。([GitHub][4])

**问题隐患**：

这个脚本是 Phase 2 的年度市场行为，不足以支撑 Phase 2.2 的 H5。H5 需要月度甚至周度残差共振，年度收益差异太粗，会错过主题扩散、风险共振、极端事件共现。

另外，当前代码用 `close[-1]/close[0]-1` 算年度收益，这有复权口径风险；用 `np.diff(np.log(prices))` 算波动率，如果 close 未复权，也会受分红送转影响。

**具体修改**：

保留 `13_market_behavior_panel.py` 为 legacy annual panel，新建或替换为：

```text
23_phase2_2_build_market_monthly_panel.py
```

核心输出：

```text
node_monthly_panel.parquet
```

字段：

```text
node_id
stock_code
month
monthly_return
monthly_log_return
valid_trading_days
monthly_amount
monthly_turnover
daily_volatility_in_month
max_drawdown_in_month
return_z_cs
amount_z_cs
turnover_z_cs
extreme_up_cs_top5
extreme_down_cs_bottom5
```

必须按 `nodes` 对齐：

```python
nodes = pd.read_parquet(nodes_path)[["node_id", "stock_code"]]
panel = panel.merge(nodes, on="stock_code", how="inner")
assert panel["node_id"].notna().all()
```

不要在面板里重新生成 node_id。

---

## 14. `14_semantic_market_association.py`

**当前职责**：分析语义边与市场行为关联。公开代码显示它读取 `phase2/edge_layers/edge_candidates_k100.parquet`，再读取市场行为结果做关联。([GitHub][5])

**问题隐患**：

这是最需要重写的脚本。它不能只做：

```text
score 与收益差异相关
score 与波动差异相关
不同 rank band 的 return_diff_mean
```

这些只能说明非常粗的静态差异，不能回答“共振”。

**具体修改**：

拆成三个脚本：

```text
24_phase2_2_build_residual_matrices.py
25_phase2_2_build_matched_random_edges.py
26_phase2_2_compute_edge_market_metrics.py
```

### 14.1 残差矩阵脚本应做什么

输入 `node_monthly_panel.parquet`，输出：

```text
matrix_monthly_return.npy
matrix_ret_resid_market.npy
matrix_ret_resid_l1.npy
matrix_ret_resid_l3.npy
matrix_ret_resid_size_liquidity.npy
matrix_ret_resid_full.npy
matrix_amount_z.npy
matrix_turnover_z.npy
matrix_extreme_up.npy
matrix_extreme_down.npy
matrix_valid_mask.npy
matrix_manifest.json
```

最关键修改：**矩阵行顺序必须按 `node_id`，不是 sorted stock_code**。

正确写法：

```python
nodes = pd.read_parquet(nodes_path).sort_values("node_id")
stock_codes = nodes["stock_code"].tolist()

panel = panel.merge(nodes[["node_id", "stock_code"]], on="stock_code", how="inner")

matrix = np.full((len(nodes), len(months)), np.nan, dtype=np.float32)

row = panel["node_id"].to_numpy()
col = panel["month_id"].to_numpy()
matrix[row, col] = panel["ret_resid_full"].to_numpy()
```

强断言：

```python
assert nodes["node_id"].tolist() == list(range(len(nodes)))
assert matrix.shape[0] == len(nodes)
assert stock_codes[0] == nodes.loc[nodes.node_id == 0, "stock_code"].iloc[0]
```

### 14.2 matched random edges 应做什么

不能用完全随机边，因为完全随机边会改变行业、市值、流动性、出度结构。应按语义边匹配随机边：

```text
same src node
same dst L1 或同 L1 分布
same size bucket
same liquidity bucket
exclude semantic neighbor
exclude self-loop
same month coverage requirement
```

输出：

```text
matched_random_edges.parquet
```

字段：

```text
semantic_edge_id
src_node_id
random_dst_node_id
match_level
same_l1_matched
same_size_bucket_matched
same_liquidity_bucket_matched
seed
```

### 14.3 边级市场指标应做什么

对每条语义边和随机边计算：

```text
corr_return_raw
corr_resid_market
corr_resid_l1
corr_resid_l3
corr_resid_full
corr_amount_z
corr_turnover_z
extreme_up_cooccurrence
extreme_down_cooccurrence
n_valid_months
```

代码必须跳过有效月份太少的边：

```python
valid = np.isfinite(x) & np.isfinite(y)
if valid.sum() < 24:
    return np.nan
```

H5 的主指标建议用：

```text
corr_resid_full
extreme_down_cooccurrence_lift
amount_shock_cooccurrence_lift
```

而不是原始收益差异。

---

## 15. `15_phase2_summary_report.py`

**当前职责**：生成 Phase 2 总结报告。公开代码显示它读取多个 JSON：`edge_candidates_summary.json`、`industry_baseline_results.json` 等，然后拼报告。([GitHub][6])

**问题隐患**：

报告生成脚本不能只是拼接，它必须成为最后一道审计闸门。之前 H5 结论冲突、图表状态冲突、N/A 字段未填，就是报告脚本没有 fail-fast。

**具体修改**：

把它升级成：

```text
30_phase2_2_final_report.py
```

或保留旧版，新增 Phase 2.2 报告脚本。

必须读取这些 manifest：

```text
T2_2_0_CODE_CONSISTENCY_AUDIT.json
nodes_manifest.json
knn_manifest.json
edge_candidates_manifest.json
market_monthly_panel_manifest.json
residual_matrix_manifest.json
matched_random_edges_manifest.json
edge_market_metrics_manifest.json
h5_stat_tests.json
visualization_index.json
```

加一致性规则：

```python
assert audit["status"] == "SUCCESS"
assert market_panel["node_order_policy"] == "node_id"
assert residual_matrix["row_order"] == "node_id"
assert metrics["min_valid_months"] >= 24
assert h5["decision"] in {
    "SUPPORTED_WITH_CONTROLS",
    "PARTIALLY_SUPPORTED",
    "REJECTED_AFTER_MONTHLY_TEST",
    "INCONCLUSIVE",
}
assert not report_contains_forbidden_phrases(["alpha confirmed", "can make money"])
```

H5 决策规则不要靠人工写：

```python
if effect > threshold and p_adj < 0.05 and robustness_pass:
    decision = "SUPPORTED_WITH_CONTROLS"
elif effect > 0 and p_adj < 0.10 and some_robustness_pass:
    decision = "PARTIALLY_SUPPORTED"
elif abs(effect) < small_threshold or p_adj >= 0.10:
    decision = "REJECTED_AFTER_MONTHLY_TEST"
else:
    decision = "INCONCLUSIVE"
```

---

# 三、你上传文档中 Phase 2.2 新脚本应如何定义

你上传文档讨论了 `21-31` 系列。我建议把这些脚本正式化如下。

## `21_phase2_2_code_consistency_audit.py`

**职责**：检查报告、源码、测试、脚本是否一致。

**必须检查**：

```text
derive_mutual_edges_fast 是否真实存在
assign_rank_band_exclusive 是否真实存在
build_edge_candidates_fixed 是否真实存在
prepare_nodes_index 是否真实存在
是否仍有 legacy assign_rank_band
是否仍有旧 derive_mutual_edges 被主路径调用
是否有 hard-coded cache key
是否有 sorted(stock_code) 生成矩阵行号
是否有伪 p-value
```

审计不能只 grep 字符串。必须 import：

```python
import inspect
from semantic_graph_research.phase2_graph_layers import assign_rank_band_exclusive
```

并输出函数路径、行号、源码 hash。

---

## `22_phase2_2_freeze_fixed_edge_candidates.py`

**职责**：冻结多 view、多 rank 的正式边表。

**必须输出**：

```text
views/{view}/edge_candidates_k100.parquet
views/{view}/edge_candidates_manifest.json
```

**关键字段**：

```text
view
src_node_id
dst_node_id
src_stock_code
dst_stock_code
rank
score
rank_band_exclusive
is_top005
is_top010
is_top020
is_top050
is_top100
is_mutual
reverse_rank
reverse_score
score_mean_if_mutual
```

**必须检查**：

```python
assert edges.groupby("src_node_id").size().eq(100).all()
assert not (edges.src_node_id == edges.dst_node_id).any()
assert edges["score"].between(-1, 1).all()
```

---

## `23_phase2_2_build_market_monthly_panel.py`

**职责**：构建月度市场面板。

**必须解决**：

```text
收益复权口径
交易天数过滤
停牌月份处理
月度横截面 z-score
极端事件定义
node_id 对齐
```

**建议过滤**：

```python
panel = panel[panel["valid_trading_days"] >= 10]
```

但报告要写清楚过滤前后行数。

---

## `24_phase2_2_build_residual_matrices.py`

**职责**：构建按 node_id 排列的残差矩阵。

**最高优先级修复**：

不要：

```python
stock_codes = sorted(panel["stock_code"].unique())
```

要：

```python
nodes = pd.read_parquet(nodes_path).sort_values("node_id")
stock_codes = nodes["stock_code"].tolist()
```

并写入：

```json
{
  "row_order": "node_id",
  "row_0_stock_code": "...",
  "n_nodes": 5502,
  "n_months": ...,
  "months": [...]
}
```

---

## `25_phase2_2_build_matched_random_edges.py`

**职责**：生成匹配随机边。

**不要做完全随机**。匹配维度至少包括：

```text
src node 固定
dst 行业 bucket
dst 市值 bucket
dst 流动性 bucket
排除已有语义邻居
排除 self-loop
```

如果匹配失败，要降级并记录：

```text
match_l3_size_liq
match_l1_size_liq
match_l1_only
match_any
```

---

## `26_phase2_2_compute_edge_market_metrics.py`

**职责**：计算边级市场共振指标。

**关键风险**：如果这里直接：

```python
src_ids = edges["src_node_id"].values
dst_ids = edges["dst_node_id"].values
x = matrix[src_ids]
y = matrix[dst_ids]
```

那么矩阵必须 100% 按 node_id 排列。否则全部错。

**应加防错**：

```python
matrix_manifest = json.load(open(...))
assert matrix_manifest["row_order"] == "node_id"
assert matrix.shape[0] == len(nodes)
```

输出：

```text
edge_market_metrics.parquet
edge_market_metrics_summary.json
```

---

## `27_phase2_2_statistical_tests.py`

**职责**：统计检验。

**必须避免伪 p-value**。

不要把几十万条边当独立样本直接 t-test。要做：

```text
permutation test
matched pair test
month block bootstrap
node cluster bootstrap
FDR correction
effect size
confidence interval
```

输出：

```json
{
  "metric": "corr_resid_full",
  "semantic_mean": ...,
  "random_mean": ...,
  "delta": ...,
  "bootstrap_ci_95": [..., ...],
  "permutation_p": ...,
  "fdr_q": ...,
  "n_edges": ...,
  "n_effective_blocks": ...,
  "decision": ...
}
```

---

## `28_phase2_2_robustness_sensitivity.py`

**职责**：稳健性。

必须做这些切片：

```text
remove top 1% hubs
remove score >= 0.98 duplicate suspects
same_l1 only
cross_l1 only
rank_001_005
rank_006_010
rank_011_020
rank_021_050
rank_051_100
bull/bear/sideways market regimes
pre/post 2020
pre/post 2022
```

H5 只有在这些切片下方向大体一致，才允许写 `PARTIALLY_SUPPORTED`。

---

## `28_5_data_completion.py`

**职责**：补齐缺失数据。

**建议**：不要放在正式主路径中。它应该改成：

```text
scripts/dev/28_5_data_completion.py
```

或改名：

```text
28_phase2_2_data_availability_audit.py
```

它不应偷偷填补数据然后让报告继续跑。金融数据缺失不应随意插值，尤其是收益矩阵。可以补 metadata，不能补收益事实。

---

## `29_phase2_2_comprehensive_viz.py`

**职责**：综合可视化。

**问题**：如果 `31` 已经是 exhaustive viz engine，`29` 和 `31` 容易重复。

**建议**：`29` 只保留核心 10 张图：

```text
score_by_rank
same_l3_by_rank
mutual_ratio_by_rank
monthly_coverage_heatmap
corr_resid_full_semantic_vs_random
h5_effect_by_view
h5_effect_by_rank_band
hub_sensitivity
duplicate_sensitivity
decision_table
```

---

## `29_phase2_2_visualization_dashboard.py`

**职责**：仪表盘。

**建议**：不要作为研究结论依赖。Dashboard 可以读最终 parquet/json，但不能生成新统计口径。否则报告和 dashboard 会出现两套数据。

---

## `30_phase2_2_comprehensive_report.py` 与 `30_phase2_2_final_report.py`

**问题**：两个 `30` 报告脚本会制造冲突。

**建议**：

保留一个正式脚本：

```text
30_phase2_2_final_report.py
```

另一个移到：

```text
scripts/dev/
```

正式报告必须从 manifest 和 summary JSON 生成，不能手写结论。

---

## `31_phase2_2_exhaustive_viz_engine.py`

**职责**：批量生成图。

**问题**：如果它生成了 145 张图，但 commit message 写 plots not，那么它必须有图表完成度审计。

**具体修改**：

输出：

```text
PHASE2_2_VISUALIZATION_INDEX.md
visualization_index.json
```

每张图必须记录：

```json
{
  "plot_id": "...",
  "path": "...",
  "exists": true,
  "size_bytes": 123456,
  "source_data": "...",
  "source_sha256": "...",
  "status": "ok"
}
```

最终报告只允许引用 `status=ok` 的图。

---

## `31_1_viz_audit_scores.py` 到 `31_4_viz_regime_overlap.py`

这些可以保留，但应纳入统一入口。不要让用户手工记运行顺序。

建议增加：

```text
scripts/run_phase2_2_pipeline.py
```

顺序：

```text
21 audit
22 freeze edges
23 monthly panel
24 residual matrices
25 matched random
26 edge metrics
27 stat tests
28 robustness
29 core viz
31 exhaustive viz
30 final report
```

---

## `temp_plot1.py`

**必须删除或移入 `scripts/dev/`**。

任何 `temp_*.py` 不应留在正式研究仓库主脚本目录。否则审计者无法判断它是否参与报告。

---

# 四、必须新增或修改的 `src/` 核心函数

公开 `src/semantic_graph_research` 目录包含 `graph_builder.py`、`phase2_graph_layers.py` 等模块。([GitHub][7]) 其中 `graph_builder.py` 当前仍能看到 FAISS kNN 逻辑。([GitHub][3]) Phase 2.2 应把关键逻辑从 scripts 迁移到 `src/`，脚本只做 orchestration。

## 1. 新增 `derive_mutual_edges_fast`

不要用逐行 DataFrame 过滤找反向边。用 merge：

```python
def derive_mutual_edges_fast(edges: pd.DataFrame) -> pd.DataFrame:
    required = {"src_node_id", "dst_node_id", "score", "rank"}
    missing = required - set(edges.columns)
    if missing:
        raise ValueError(f"missing columns: {missing}")

    fwd = edges.copy()
    rev = edges[["src_node_id", "dst_node_id", "score", "rank"]].rename(
        columns={
            "src_node_id": "dst_node_id",
            "dst_node_id": "src_node_id",
            "score": "reverse_score",
            "rank": "reverse_rank",
        }
    )

    out = fwd.merge(
        rev,
        on=["src_node_id", "dst_node_id"],
        how="left",
        validate="many_to_one",
    )
    out["is_mutual"] = out["reverse_score"].notna()
    out["score_mean_if_mutual"] = np.where(
        out["is_mutual"],
        (out["score"] + out["reverse_score"]) / 2,
        np.nan,
    )
    return out
```

## 2. 新增 `prepare_nodes_index`

```python
def prepare_nodes_index(nodes: pd.DataFrame) -> pd.DataFrame:
    nodes = nodes.copy().sort_values("node_id").reset_index(drop=True)
    if not (nodes["node_id"].to_numpy() == np.arange(len(nodes))).all():
        raise ValueError("node_id must be contiguous and sorted")
    if not nodes["stock_code"].is_unique:
        raise ValueError("stock_code must be unique")
    if "record_id" in nodes and not nodes["record_id"].is_unique:
        raise ValueError("record_id must be unique")
    return nodes
```

## 3. 新增矩阵行序检查

```python
def assert_matrix_node_order(matrix: np.ndarray, nodes: pd.DataFrame, manifest: dict):
    if manifest.get("row_order") != "node_id":
        raise ValueError("matrix row_order must be node_id")
    if matrix.shape[0] != len(nodes):
        raise ValueError("matrix rows != nodes")
    nodes_sorted = nodes.sort_values("node_id")
    if not (nodes_sorted["node_id"].to_numpy() == np.arange(len(nodes))).all():
        raise ValueError("invalid node_id sequence")
```

---

# 五、最重要的潜在错误隐患清单

按严重程度排序：

1. **矩阵行号与 node_id 错配**：最高风险；会让所有边级市场指标失真，但不一定报错。
2. **rank band 互斥/累计混用**：导致报告口径冲突，比如 `strong` 到底是 top10 还是 rank 6-10。
3. **mutual edge 逻辑旧实现仍被调用**：报告说修复，但实际主路径可能没用新函数。
4. **伪 p-value**：大量边共享节点和月份，不能当独立样本。
5. **当前行业标签回填历史**：可以用于静态解释，不能用于严格历史归因。
6. **收益未复权**：年度/月度收益如果用 close，可能受分红送转影响。
7. **停牌与低交易日月份处理不明确**：会污染月度相关。
8. **duplicate/template 文本污染**：score 接近 1 的边必须人工或规则审计。
9. **hub 污染**：高入度节点可能是业务中心，也可能是泛化文本中心。
10. **报告脚本没有 fail-fast**：会继续生成看似完整但内部矛盾的总结。
11. **临时脚本留在正式目录**：`temp_plot1.py`、`28_5` 这类应移出主路径。
12. **hard-coded cache key**：公开代码中 Phase 2 脚本存在固定 cache 目录风格，例如 `cache/semantic_graph/2eebde04e582`，这对复现和多 view 非常危险；`13_market_behavior_panel.py` 就硬编码了 cache 路径和本地数据路径。([GitHub][4])

---

# 六、建议的最终目录结构

```text
scripts/
  run_phase2_2_pipeline.py

  phase1/
    00_audit_semantic_data.py
    01_build_nodes.py
    02_build_semantic_knn.py
    03_compute_graph_diagnostics.py
    04_plot_from_cache.py
    05_market_alignment_census.py

  phase2/
    07_build_extended_edge_candidates.py
    08_edge_layer_statistics.py
    09_industry_baseline.py
    10_size_liquidity_domain.py
    11_domain_neighbor_analysis.py
    12_hub_bridge_research.py
    13_market_behavior_panel.py
    14_semantic_market_association.py
    15_phase2_summary_report.py

  phase2_2/
    21_code_consistency_audit.py
    22_freeze_fixed_edge_candidates.py
    23_build_market_monthly_panel.py
    24_build_residual_matrices.py
    25_build_matched_random_edges.py
    26_compute_edge_market_metrics.py
    27_statistical_tests.py
    28_robustness_sensitivity.py
    29_core_visualizations.py
    30_final_report.py
    31_exhaustive_viz_engine.py

  dev/
    temp_plot1.py
    28_5_data_completion.py
```

---

# 七、Phase 2.2 的正确结论写法

目前不建议写：

> H5 已支持，语义边能预测市场共振。

更稳健的写法应是：

> 在月度残差收益、成交/换手冲击、极端涨跌共现等指标下，语义边相对 matched random edges 是否存在稳定增量，需要以 node-order-safe residual matrices、matched random baseline、block bootstrap/permutation test 和 hub/duplicate sensitivity 为前提。若仅基于原始收益差异或普通相关性，不能证明 H5。当前最多可写为 `PARTIALLY_SUPPORTED` 或 `INCONCLUSIVE`，除非稳健性检验全部通过。

---

# 八、最小修改路线：先修这 8 件事

按优先级：

1. 在 `24_phase2_2_build_residual_matrices.py` 修复矩阵行顺序，强制 `row_order=node_id`。
2. 在 `26_phase2_2_compute_edge_market_metrics.py` 读取 matrix manifest 并断言 `row_order=node_id`。
3. 在 `22_phase2_2_freeze_fixed_edge_candidates.py` 同时输出 `rank_band_exclusive` 和 `is_topK`。
4. 在 `src/semantic_graph_research/phase2_graph_layers.py` 加 `derive_mutual_edges_fast`，并确保主路径调用它。
5. 在 `27_phase2_2_statistical_tests.py` 删除伪 p-value，改 permutation/bootstrap。
6. 在 `25_phase2_2_build_matched_random_edges.py` 做行业/市值/流动性匹配随机边。
7. 在 `30_phase2_2_final_report.py` 加一致性 fail-fast。
8. 删除或移动 `temp_plot1.py`、`28_5_data_completion.py` 这类非正式脚本。

做到这 8 件事后，Phase 2.2 才能从“看起来完成”变成“研究闭环可信”。

