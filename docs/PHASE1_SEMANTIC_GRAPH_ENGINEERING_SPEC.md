# Phase 1 Semantic Graph Engineering Spec

## 0. 文档目的

这份文档只定义第一轮研究工程。  
目标不是搭一个完整量化系统，而是先把“真实语义近邻图是否值得继续研究”做成一个可复现的阶段性结果。

## 1. 第一轮研究问题

### 主问题

> 真实 `application_scenarios_json` 语义向量，能否形成一张可解释、可复现、非退化的 A 股语义近邻图？

### 子问题

1. 真实 1024 维向量是否完整、可对齐、可复现读取？
2. 用 cosine / inner product 近邻构出的图，是否存在稳定的局部结构？
3. 当前申万行业标签能否为这张图提供某种解释，但又不完全等同于语义图？
4. 图节点能否稳定接到 2010—2026.04 的行情世界，为后续研究做准备？

## 2. 第一轮明确不做什么

- 不做图融合
- 不做图平滑
- 不做聚类结论
- 不做因子构造
- 不做收益预测
- 不做回测
- 不做生产化接口
- 不做历史行业回填
- 不做多 view 融合
- 不做新的 embedding
- 不做任何 mock / fallback 替代

第一轮只研究**一张真实语义图**。

## 3. 项目建议目录

```text
project_root/
  docs/
    README_FOR_TRAE.md
    RESEARCH_CONSTITUTION.md
    DATA_CONTRACTS.md
    PHASE1_SEMANTIC_GRAPH_ENGINEERING_SPEC.md
    AI_WORKING_PROTOCOL.md
  configs/
    phase1_semantic_graph.yaml
  src/
    semantic_graph_research/
      __init__.py
      config.py
      data_contracts.py
      semantic_loader.py
      graph_builder.py
      cache_io.py
      diagnostics.py
      market_alignment.py
      plotting.py
  scripts/
    00_audit_semantic_data.py
    01_build_nodes.py
    02_build_semantic_knn.py
    03_compute_graph_diagnostics.py
    04_plot_from_cache.py
    05_market_alignment_census.py
  tests/
    test_real_semantic_contract.py
    test_real_node_alignment.py
    test_real_knn_cache_contract.py
    test_plotting_reads_cache_only.py
    test_market_alignment_contract.py
  cache/
    semantic_graph/
    market_alignment/
  outputs/
    plots/
    reports/
  PROJECT_STATE.md
```

## 4. 配置文件建议

`configs/phase1_semantic_graph.yaml`

```yaml
project:
  phase: "phase1"
  research_name: "semantic_knn_graph"
  graph_version: "v1"

semantic:
  view: "application_scenarios_json"
  dataset_root: "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset"
  vectors_path: "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.npy"
  meta_path: "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.meta.json"
  records_path: "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/parquet/records-all.parquet"
  expected_rows: 5502
  expected_dim: 1024
  expected_dtype: "float32"
  allow_fallback: false

graph:
  metric: "inner_product"
  normalized_vectors_expected: true
  canonical_k: 20
  sensitivity_k: [10, 20, 50]
  build_directed: true
  build_mutual: true
  remove_self_neighbor: true
  use_faiss_gpu: true
  gpu_device: 0

market:
  requested_start_date: "20100101"
  requested_end_date: "20260430"
  stock_daily_path: "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily.parquet"
  stock_daily_basic_path: "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet"
  stock_sw_member_path: "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet"

cache:
  root: "cache"
  reuse_if_valid: true
  write_manifest: true
  force_rebuild: false

plots:
  output_dir: "outputs/plots"
  max_ego_examples: 12
```

## 5. 核心接口定义

### 5.1 `semantic_loader.py`

```python
load_semantic_view(config) -> SemanticBundle
audit_semantic_bundle(bundle, config) -> SemanticAudit
build_node_table(bundle, records_path) -> DataFrame
```

#### `SemanticBundle` 至少包含

- `vectors`
- `row_ids`
- `view`
- `meta`
- `input_fingerprints`

#### `SemanticAudit` 至少包含

- `rows`
- `dim`
- `dtype`
- `non_finite_count`
- `zero_norm_count`
- `l2_min`
- `l2_mean`
- `l2_max`
- `row_id_unique_count`
- `alignment_ok`

### 5.2 `graph_builder.py`

```python
build_faiss_knn(vectors, k, gpu_device=0) -> NeighborMatrix
neighbors_to_directed_edges(neighbors, node_table) -> DataFrame
derive_mutual_edges(directed_edges) -> DataFrame
```

#### `NeighborMatrix`

- `indices`: `int32`, shape `[N, k]`
- `scores`: `float32`, shape `[N, k]`
- 已移除 self-neighbor

### 5.3 `cache_io.py`

```python
make_cache_key(input_fingerprints, config) -> str
write_cache_manifest(...)
read_cache_manifest(...)
save_nodes(...)
save_neighbors(...)
save_edges(...)
load_cached_graph(...)
```

### 5.4 `diagnostics.py`

```python
compute_graph_stats(nodes, directed_edges, mutual_edges) -> dict
compute_industry_diagnostics(nodes, directed_edges, sw_member_current) -> DataFrame
make_neighbor_examples(nodes, directed_edges, n_examples=...) -> DataFrame
```

### 5.5 `plotting.py`

```python
plot_score_distribution_from_cache(cache_dir, out_dir)
plot_degree_distribution_from_cache(cache_dir, out_dir)
plot_pca2_scatter_from_cache(cache_dir, out_dir)
plot_industry_purity_from_cache(cache_dir, out_dir)
plot_ego_neighbors_from_cache(cache_dir, out_dir, stock_codes=None)
```

注意：  
绘图函数只允许读取缓存，不允许重新加载原始 NPY，不允许重新跑 FAISS。

## 6. 缓存设计

## 6.1 为什么必须缓存

第一轮缓存不是为了生产优化，而是为了：

- 阻断上下文污染
- 固化每一步的研究身份
- 让图表可以脱离上游计算重复生成
- 让后续第二轮只接入已经验证过的节点与边

## 6.2 缓存键

`cache_key = sha256(input_fingerprints + canonical_config_json)[:12]`

其中 `input_fingerprints` 至少包含：

- `vectors_path`
- `vectors_sha256`
- `meta_path`
- `meta_sha256`
- `records_path`
- `records_sha256`
- 文件大小
- 文件修改时间

## 6.3 建议缓存目录

```text
cache/
  semantic_graph/
    <cache_key>/
      manifest.json
      semantic_audit.json
      nodes.parquet
      neighbors_k10.npz
      neighbors_k20.npz
      neighbors_k50.npz
      edges_directed_k10.parquet
      edges_directed_k20.parquet
      edges_directed_k50.parquet
      edges_mutual_k10.parquet
      edges_mutual_k20.parquet
      edges_mutual_k50.parquet
      graph_stats_k10.json
      graph_stats_k20.json
      graph_stats_k50.json
      layout_pca2.parquet
      industry_join_current.parquet
      industry_diagnostics_k20.parquet
      neighbor_examples_k20.parquet
    LATEST.json
  market_alignment/
    <cache_key>/
      manifest.json
      market_coverage_by_stock.parquet
      market_coverage_summary.json
```

## 6.4 关键缓存文件契约

### `nodes.parquet`

| 字段 | 类型 | 说明 |
|---|---|---|
| `node_id` | int32 | 与向量行号一致 |
| `record_id` | string | 语义主键 |
| `stock_code` | string | 股票代码 |
| `stock_name` | string | 股票名称 |
| `asof_date` | string | 语义快照日期 |
| `semantic_view` | string | 固定为 `application_scenarios_json` |

### `neighbors_k20.npz`

| 数组 | dtype | shape |
|---|---|---|
| `indices` | int32 | `[5502, 20]` |
| `scores` | float32 | `[5502, 20]` |

### `edges_directed_k20.parquet`

| 字段 | 说明 |
|---|---|
| `src_node_id` | 源节点 |
| `dst_node_id` | 近邻节点 |
| `src_stock_code` | 源股票 |
| `dst_stock_code` | 近邻股票 |
| `rank` | 近邻名次，从 1 开始 |
| `score` | inner product / cosine 相似度 |

### `edges_mutual_k20.parquet`

| 字段 | 说明 |
|---|---|
| `u_node_id` | 节点 u |
| `v_node_id` | 节点 v |
| `score_uv` | u -> v |
| `score_vu` | v -> u |
| `score_mean` | 双向均值 |

### `layout_pca2.parquet`

| 字段 | 说明 |
|---|---|
| `node_id` | 节点 |
| `x` | 仅用于绘图的二维投影 |
| `y` | 仅用于绘图的二维投影 |
| `layout_method` | 固定 `pca2_for_visualization_only` |

说明：  
PCA 在第一轮只允许用于可视化投影，不允许替代真实 1024 维向量参与构图。

## 7. 任务拆分

# T0 — 文档与配置落地

### 目标
把研究边界写死，让后续 AI 不再每轮重新发明项目。

### 输入
- 本文档
- `DATA_CONTRACTS.md`
- `RESEARCH_CONSTITUTION.md`

### 输出
- `configs/phase1_semantic_graph.yaml`
- `PROJECT_STATE.md`
- 目录骨架

### 验收
- 文件存在
- 路径已按本机环境填写
- `allow_fallback: false`
- `canonical_k: 20`
- `PROJECT_STATE.md` 能说清当前只做第一轮

---

# T1 — 真实语义数据审计

### 目标
确认第一轮研究输入是真实、完整、对齐的。

### 输入
- `application_scenarios_json-all.npy`
- `application_scenarios_json-all.meta.json`
- `records-all.parquet`

### 必做检查
- NPY 文件存在
- meta 文件存在
- records parquet 存在
- shape = `(5502, 1024)`
- dtype = `float32`
- 非有限值数量 = 0
- `row_ids` 唯一
- `row_ids` 与 `records-all.parquet.record_id` 完整对齐
- view 名称为 `application_scenarios_json`
- 不允许 fallback

### 输出
- `semantic_audit.json`
- `run_manifest.json`

### 失败条件
任一契约不满足，直接退出。

### 测试
- `test_real_semantic_contract.py`

---

# T2 — 节点表构建

### 目标
把“向量行号”变成稳定、可解释、可连接的图节点。

### 输入
- T1 审计通过的真实语义数据
- `records-all.parquet`

### 输出
- `nodes.parquet`

### 必须字段
- `node_id`
- `record_id`
- `stock_code`
- `stock_name`
- `asof_date`
- `semantic_view`

### 验收
- 行数 = 5502
- `node_id` 连续从 0 到 5501
- `record_id` 唯一
- `stock_code` 唯一
- `node_id -> record_id -> stock_code` 可逆追踪

### 测试
- `test_real_node_alignment.py`

---

# T3 — 真实向量上的 FAISS kNN 构图

### 目标
用真实 1024 维语义向量构造近邻图。

### 输入
- T1 真实向量
- T2 节点表

### 配置
- GPU: `gpu0`
- metric: inner product
- `k = 10, 20, 50`
- canonical graph: `k = 20`
- 必须移除 self-neighbor

### 输出
- `neighbors_k10.npz`
- `neighbors_k20.npz`
- `neighbors_k50.npz`
- `edges_directed_k10.parquet`
- `edges_directed_k20.parquet`
- `edges_directed_k50.parquet`
- `edges_mutual_k10.parquet`
- `edges_mutual_k20.parquet`
- `edges_mutual_k50.parquet`

### 验收
- directed edge count = `N * k`
- 没有 self loop
- 每行 rank 从 1 到 k
- 分数为有限值
- 重跑后结果在同配置下可复现
- 任何代码路径都没有调用 mock / TF-IDF / PCA fallback

### 测试
- `test_real_knn_cache_contract.py`

---

# T4 — 图诊断计算

### 目标
先描述图，再决定要不要做更复杂的图方法。

### 输入
- `nodes.parquet`
- `edges_directed_k*.parquet`
- `edges_mutual_k*.parquet`
- 当前 `stock_sw_member.parquet`

### 输出
- `graph_stats_k10.json`
- `graph_stats_k20.json`
- `graph_stats_k50.json`
- `industry_join_current.parquet`
- `industry_diagnostics_k20.parquet`
- `neighbor_examples_k20.parquet`

### 必算指标

#### 图结构
- 节点数
- directed edge 数
- mutual edge 数
- reciprocity ratio
- mutual graph connected components
- 最大连通分量比例
- 入度分布
- 出度分布
- score 分布
- top1 与 top20 score gap

#### 行业诊断
- 当前申万标签覆盖率
- top-k 近邻的同 L1 行业比例
- 随机基线同 L1 比例
- 按 L1 行业分组的平均近邻一致性
- 明确标注：该诊断只使用当前成分，不是历史行业真值

#### 可解释样例
- 选取若干股票输出其 top-k 近邻表
- 样例最好覆盖不同 L1 行业
- 输出时保留 `stock_code`, `stock_name`, `score`, `industry_label`

### 重要说明
行业一致性高低是研究结果，不是工程测试的硬阈值。  
不要为了让指标“好看”修改图。

---

# T5 — 仅从缓存绘图

### 目标
证明中间结果已被正确固化，图表生成不依赖重新计算上游。

### 输入
只允许读取缓存：

- `nodes.parquet`
- `edges_*.parquet`
- `graph_stats_*.json`
- `industry_diagnostics_k20.parquet`
- `neighbor_examples_k20.parquet`
- `layout_pca2.parquet`

### 输出图表
- `score_distribution_k20.png`
- `degree_distribution_k20.png`
- `mutual_component_sizes_k20.png`
- `industry_purity_vs_random_k20.png`
- `pca2_scatter_by_current_sw_l1.png`
- `ego_neighbors_examples_k20.png`

### 验收
- 删除或临时屏蔽原始 NPY 后，绘图脚本仍能在已有缓存上运行
- 绘图脚本没有重新调用 FAISS
- 绘图脚本没有重新读取原始语义向量
- 图表标题必须明确写出：
  - view
  - k
  - 当前行业标签的限制
  - PCA 仅用于可视化

### 测试
- `test_plotting_reads_cache_only.py`

---

# T6 — 2010—2026.04 行情对齐普查

### 目标
不做因子，只确认图节点能否接入后续行情研究。

### 输入
- `nodes.parquet`
- `stock_daily.parquet`
- `stock_daily_basic.parquet`

### 推荐实现
优先直接用 DuckDB 查询 Parquet，不必先把大型 warehouse 搬到 Linux。

### 允许查询的最低字段
`stock_daily`
- `ts_code`
- `trade_date`
- `close`
- `pct_chg`
- `vol`
- `amount`

`stock_daily_basic`
- `ts_code`
- `trade_date`
- `turnover_rate`
- `pe_ttm`
- `pb`
- `total_mv`
- `circ_mv`

### 输出
- `market_coverage_by_stock.parquet`
- `market_coverage_summary.json`

### 必算指标
- 每只股票在请求期内：
  - `daily_row_count`
  - `daily_basic_row_count`
  - `first_trade_date`
  - `last_trade_date`
- 全局：
  - 节点中有行情覆盖的比例
  - 节点中有 daily_basic 覆盖的比例
  - 实际数据最大日期
  - 大面积缺失的股票列表
- 写清：
  - 请求截止日
  - 实际截止日
  - 未对缺失数据进行任何补造

### 验收
- 所有结果均由真实 parquet 产生
- 不做任何因子计算
- 不把覆盖率结果误解释成研究结论

### 测试
- `test_market_alignment_contract.py`

## 8. 图表解释原则

第一轮图表只回答描述性问题：

- 图是不是退化？
- 哪些节点像谁？
- 当前行业标签能不能解释一部分结构？
- 哪些股票比较孤立或桥接？
- 是否值得进入聚类或融合研究？

第一轮图表不回答：

- 这张图能不能赚钱
- 哪个行业未来更强
- 图平滑能不能提升收益预测
- 聚类能不能直接拿来下单

## 9. 测试策略

## 9.1 必须有的真实数据测试

### `test_real_semantic_contract.py`
验证真实输入路径、shape、dtype、finite、row_ids。

### `test_real_node_alignment.py`
验证 `record_id` 对齐、`node_id` 连续、`stock_code` 唯一。

### `test_real_knn_cache_contract.py`
验证缓存存在、shape 正确、无 self loop、edge 数正确。

### `test_plotting_reads_cache_only.py`
用 monkeypatch 禁止原始 NPY 加载与 FAISS 调用，确认绘图只读缓存。

### `test_market_alignment_contract.py`
验证真实行情 parquet 可读、时间窗与输出字段正确。

## 9.2 不应该写的测试

- 不测试行业一致性必须高于某阈值
- 不测试某只股票必须连到某只股票
- 不测试聚类数
- 不测试收益结论
- 不测试“图必须好看”

这些属于研究观察，不属于工程契约。

## 10. 第一轮验收清单

### 数据
- [ ] 真实 `application_scenarios_json-all.npy` 已读取
- [ ] shape = `(5502, 1024)`
- [ ] 0 个非有限值
- [ ] `record_id` 全量对齐
- [ ] 无 fallback

### 图
- [ ] 已生成 k=10,20,50 的邻居矩阵
- [ ] k=20 作为 canonical graph
- [ ] directed 与 mutual 边表已缓存
- [ ] 无 self-loop

### 诊断
- [ ] 图结构统计已缓存
- [ ] 当前申万行业诊断已缓存
- [ ] 邻居样例表已缓存

### 图表
- [ ] 所有图均从缓存生成
- [ ] 图表不重新读原始向量
- [ ] 图表注释清楚说明当前行业标签限制

### 行情接入
- [ ] 已完成 2010—2026.04 覆盖率普查
- [ ] 已记录真实最大日期
- [ ] 未进行任何补造或因子计算

### 文档
- [ ] `PROJECT_STATE.md` 已更新
- [ ] 当前轮得到的发现、偏差、下一步已写清

## 11. 第一轮完成后如何决定下一轮

### 若图结构退化
例如：
- 近邻分数几乎无区分
- 大量近邻只是模板化文本重复
- 行业/业务解释样例非常差
- mutual 图过于碎裂或过于塌缩

下一轮优先考虑：
- 换 view 做对比
- 做多 view 的相似度研究
- 检查文本生成质量
- 先不要急着聚类

### 若图结构有解释力
下一轮可以进入：

1. semantic graph clustering  
2. semantic graph + 当前行业标签的关系研究  
3. graph smoothing 的最小研究单元  
4. 与行情特征做最小耦合实验

但仍然要一次只推进一个问题。

## 12. 一句总纲

> 第一轮不是把图研究做完，  
> 而是把“这张图到底值不值得继续做”这件事做对。
