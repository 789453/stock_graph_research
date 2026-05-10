# PHASE2_SEMANTIC_GRAPH_RESEARCH_IMPLEMENTATION_SPEC

## 0. 文档定位

这份文档定义 Phase 2 的研究实施方案。它不是生产系统设计，不是 GNN 方案，不是回测方案，也不是图因子库方案。Phase 2 的目标，是在 Phase 1 已经证明“真实 1024 维语义向量可以构造非退化 A 股语义近邻图”的基础上，进一步回答一个更接近金融研究本质的问题：

> 这张语义图到底表达了什么金融关系？  
> 它是否在申万三级行业、市值、流动性等常见分组之外，保留了可解释、可统计验证的市场行为关联？

Phase 2 的研究对象仍然是 `application_scenarios_json` 这一版 1024 维 float32 语义快照；不做新的 embedding，不做多 view 融合，不做历史语义图，不做 GNN，不做回测，不做图因子，不做自动大规模人工标注。所有研究都必须围绕“语义边是否有金融含义”展开，并保留阶段性结果到 `md/json/log/yaml/parquet/png` 等文件中。

Phase 2 的重点不是把模型做大，而是把证据链做厚。Phase 1 已经给出了一张 kNN 图，但 kNN 图只说明“向量空间里的近邻关系存在”。Phase 2 要做的是：把这张候选语义图拆成多种可解释关系层，分别与行业、规模、市值、流动性、收益共动、波动共振、题材/风险传染进行对照。只有当这些描述性结果成立，后续才有必要考虑 Phase 3 的图信号、图平滑、图模型或者更复杂的交易辅助研究。

本文件遵循你的研究哲学：研究优先、真实数据优先、阶段性缓存优先、证伪标准优先。所有任务都要有明确输入、明确输出、明确失败条件、明确缓存。任何脚本都不应为了“跑得完整”而偷偷降级、补造、换数据源或者把研究结果写死为工程测试。

---

## 1. 对 Phase 1 当前状态的承接判断

当前仓库已经形成了 Phase 1 的研究闭环：`configs/phase1_semantic_graph.yaml` 固定了真实语义路径、预期 5502 行、1024 维、float32、禁止 fallback、FAISS GPU、k=10/20/50、2010—2026.04 行情窗口；`src/semantic_graph_research` 下已有 `semantic_loader.py`、`graph_builder.py`、`diagnostics.py`、`plotting.py`、`cache_io.py`、`config.py`；`scripts` 下已有 `00` 到 `05` 的阶段脚本；`tests` 下已有五个真实数据契约测试；缓存中已有 `semantic_audit.json`、`graph_stats_k20.json`、`market_coverage_summary.json`；图表目录中已有四张 Phase 1 图。

Phase 1 最重要的结果是：

- 语义数据：5502 行、1024 维、float32、无非有限值、无零向量，L2 norm 基本等于 1。
- 图结构：k=20 时有向边 110040 条，即 5502 × 20；互惠有向边行数 64488；reciprocity ratio 约 0.586；最大 mutual component 5401 个节点，占比约 98.16%；入度均值 20、标准差约 13.44；top1 平均分约 0.834，top20 平均分约 0.703。
- 行情接入：daily 与 daily_basic 覆盖率均为 100%，实际最大日期为 2026-04-23。
- 缓存哲学：核心结果已经落盘，可以被后续研究引用。
- 当前缺陷：`score_distribution_k20.png` 实际不是分布图；`PROJECT_STATE.md` 测试状态仍是 pending；互惠边命名需要澄清；self-neighbor 断言虽然测试文件里已有逐行检查，但构图脚本中的断言仍然较弱；行业诊断还没有随机/分域基准；hub 和跨行业桥尚未系统研究。

Phase 2 不需要推翻 Phase 1，而是把 Phase 1 当成稳定地基：继续使用现有 cache key `2eebde04e582` 下的节点、边和审计结果；在不重新构造 embedding 的前提下，扩展边关系分析、行业/市值基准、hub 分析、市场行为关联分析。Phase 2 可以新增 k=100 或使用已有 k=50 做候选池，但不应该把“更多边”误解成“更好图”。更多边只是为了研究不同强度关系：核心邻居、稳定邻居、中等邻居、弱主题邻居、边界邻居。最终任何边能否进入解释，必须经过行业/市值/流动性/市场行为基准验证。

---

## 2. Phase 2 的核心研究问题

Phase 2 建议总标题为：

> Phase 2：语义图解释力与市场行为关联验证

核心问题可以分成六组：

### Q1：语义图是否只是复刻申万行业？

如果语义近邻高度集中在同一申万三级行业，这并不是坏事，但它意味着语义图可能主要捕捉的是行业分类。真正重要的是：在控制三级行业、市值、流动性后，语义近邻还是否有增量结构？如果没有，语义图的第一用途可能是“行业分类的连续化表达”；如果有，语义图可能捕捉了传统行业分类之外的业务场景、产业链、主题链、风险链。

### Q2：不同 rank 的边是否代表不同金融含义？

top1/top5/top10 可能代表非常强的业务相似；top20 可能代表稳定语义邻域；top50 可能包含中等主题或产业链关系；top100 则可能包含弱关联、题材扩散、风险传染候选关系。不能把所有边一视同仁。Phase 2 应该把边按 rank band 和 score band 分层，而不是只使用固定 k=20。推荐初始分层：

- core：rank 1—5
- strong：rank 1—10
- stable：rank 1—20
- context：rank 21—50
- extended：rank 51—100，如果新增 k=100
- middle：按 score 或 rank 的中位区间，例如 rank 21—50
- tail：在候选池内分数较低但仍进入 top100 的边，例如 rank 51—100

这些分层不是为了生产筛选，而是为了认识图的结构。尤其是你的实盘直觉中提到的“中等关联关系的股票，存在风险、题材炒作传染”，很可能不在 top5/top10，而在 top20—top100 的弱至中等语义边里。强边更像同业务，弱边更像同主题或场景扩散候选。

### Q3：不同股票的邻居数量是否应当不同？

固定 kNN 是第一阶段必要的候选生成方法，但不应直接等同于最终图。固定 k 会强迫每只股票都有 k 个邻居；对于语义孤立股票，第 20 或第 50 个邻居可能只是“相对最近”，不是“绝对相似”。因此 Phase 2 的核心图构建思想应从“固定 k 图”转向“候选边池 + 自适应边选择”。

推荐把图分成三层：

1. 候选图：用 FAISS 一次性取较大的 topK，例如 100。它不代表最终关系，只代表可研究候选。
2. 证据图：对候选边附加 rank、score、mutual、score_gap、行业关系、市值距离、流动性距离、收益共动、波动共振等证据。
3. 研究图：根据具体研究问题选择不同边集。例如强业务图、跨行业桥图、hub 诊断图、中等传染候选图、行业内残差图。

这样就可以允许每只股票拥有不同数量的研究邻居。实际规则可以是：

- `score >= node_top1_score - local_gap_threshold`：保留与本节点最强邻居相差不大的边。
- `score >= global_score_quantile(q)`：保留全局分数高于某分位的边。
- `rank <= rank_cap`：保留排名约束，避免 hub 或异常边过多。
- `mutual == true`：保留互惠边作为高可信边。
- `same_l3`、`same_mv_bucket`、`cross_l1` 等域条件：按研究问题选择域内或跨域边。
- `min_neighbors <= degree_i <= max_neighbors`：防止节点过孤立或 hub 过强。

最终你可以得到不同类型的变长邻居：

- `adaptive_core_edges`：强相似、互惠优先、每节点 3—20 个。
- `adaptive_context_edges`：中等相似、每节点 10—50 个。
- `cross_industry_bridge_edges`：跨 L1/L2/L3 但 score 高或 mutual 的边。
- `within_l3_residual_edges`：同三级行业内，排除最相似的常规同行，寻找细分业务结构。
- `topic_contagion_candidate_edges`：rank 20—100、score 不低、跨行业或跨二级行业，后续看收益/波动/成交共振。

这比“k=20 或 k=50 哪个更好”更符合研究逻辑。

---

## 3. Phase 2 的证伪标准

Phase 2 必须允许失败。失败不是坏事，失败能帮助你决定不做 GNN、不做回测、不做因子是正确的。

### H1：语义图不只是行业分类的复刻

证据要求：

- topK 同 L3 比例显著高于随机股票，但不能完全被 L3 解释。
- 同 L3 内，语义邻居比同 L3 随机邻居有更高的收益共动或波动共振。
- 跨 L3 或跨 L1 的高语义边中，存在显著高于随机跨行业边的市场行为关联。
- 行业、市值、流动性分层后，语义边仍有部分增量。

证伪条件：

- 语义邻居的所有市场行为关联，在同 L3、同市值桶、同流动性桶基准下完全消失。
- 跨行业高语义边与随机跨行业边没有区别。
- hub 解释显示大部分边来自泛化文本或模板相似，而不是业务/产业关系。

### H2：rank band 有不同含义

证据要求：

- top1—5 的同 L3/同 L2 纯度明显高于 top21—50。
- top21—50 或 top51—100 的跨行业比例更高。
- 中等 rank 边在收益极端共振、波动共振、成交冲击同步上可能强于纯行业随机边。
- score 衰减曲线存在可解释的拐点，而不是平滑无差别下降。

证伪条件：

- 各 rank band 的行业结构、市场行为关联、hub 暴露几乎相同。
- top50/top100 只是加入噪声，无法提供任何解释性样本。

### H3：语义 hub 既可能有价值，也可能污染图

证据要求：

- top in-degree hub 可以被分为产业中心型、综合集团型、主题平台型、文本泛化型。
- hub 的邻居行业熵、边权均值、mutual ratio、市场行为共振存在结构差异。
- 去 hub 或降权 hub 后，行业纯度和市场行为关联更稳定。

证伪条件：

- 大部分 hub 的边权不高、行业熵极高、邻居样例不可解释。
- hub 的存在显著抬高图连通性，但削弱所有局部市场行为关联。

### H4：语义边能解释收益/波动/成交共振，但不做预测回测

证据要求：

- 语义边连接的股票对，在 2018—2026 上有高于随机基准的日/周/月收益相关。
- 去市场、去行业、按市值/流动性分层后，至少部分边集仍有残差相关。
- 语义边对波动、成交额、极端涨跌同步有解释力。
- 中等边可能对题材和风险传染有解释力。

证伪条件：

- 所有相关性都低于或等同随机基准。
- 相关性只在原始收益上存在，去行业后完全消失。
- 相关性只由少数 hub 或少数大行业驱动。

### H5：Phase 2 不产生交易结论

Phase 2 的成功标准不是“收益显著”，不是“因子 IC 高”，不是“回测曲线好看”。Phase 2 只回答：语义图是否有金融解释价值。即使发现了 lead-lag 或邻居收益关系，也只保存为“描述性统计与候选现象”，不能把它命名为因子或交易策略。

---

## 4. Phase 2 总体目录建议

保留 Phase 1 的目录，不重构；只新增 Phase 2 文档、配置、脚本、缓存目录和输出目录。

```text
project_root/
  docs/
    PHASE2_SEMANTIC_GRAPH_RESEARCH_IMPLEMENTATION_SPEC.md
    PHASE2_RESEARCH_HYPOTHESES_AND_FALSIFICATION.md
    PHASE2_CACHE_CONTRACTS.md
    PHASE2_TASKS_00_02_REPAIR_AND_EDGE_LAYERS.md
    PHASE2_TASKS_03_05_BASELINES_AND_DOMAINS.md
    PHASE2_TASKS_06_08_HUB_BRIDGE_MARKET_BEHAVIOR.md
    PHASE2_AI_WORKING_PROTOCOL_UPDATE.md
    PHASE2_PROJECT_STATE_UPDATE_TEMPLATE.md
  configs/
    phase2_semantic_graph_research.yaml
  src/
    semantic_graph_research/
      phase2_graph_layers.py
      phase2_baselines.py
      phase2_hub_bridge.py
      phase2_market_behavior.py
      phase2_report_tables.py
  scripts/
    06_phase1_repair_and_test_report.py
    07_build_extended_edge_candidates.py
    08_compute_edge_layer_stats.py
    09_industry_size_liquidity_baselines.py
    10_within_domain_neighbor_analysis.py
    11_hub_and_bridge_analysis.py
    12_market_panel_prepare_2018_2026.py
    13_pairwise_market_behavior_analysis.py
    14_phase2_summary_report.py
  cache/
    semantic_graph/
      2eebde04e582/
        phase2/
          manifests/
          edge_layers/
          baselines/
          hub_bridge/
          market_behavior/
          reports/
  outputs/
    plots/
      phase2/
    reports/
      phase2/
  logs/
    phase2/
```

注意：这不是工程化扩张，而是研究资产管理。模块可以很薄，脚本可以很直接，优先把每一步的输入、输出、缓存、日志保存下来。

---

## 5. Phase 2 配置设计

建议新增 `configs/phase2_semantic_graph_research.yaml`，不要直接修改 Phase 1 配置。Phase 2 配置引用 Phase 1 cache key，并明确禁止 GNN、回测、图因子。

```yaml
project:
  phase: "phase2"
  research_name: "semantic_graph_explanatory_finance"
  upstream_phase1_cache_key: "2eebde04e582"
  semantic_view: "application_scenarios_json"

boundaries:
  allow_gnn: false
  allow_backtest: false
  allow_graph_factor: false
  allow_ollama_labeling: false
  allow_new_embedding: false
  allow_mock_core_data: false
  allow_phase1_cache_reuse: true

paths:
  phase1_config: "configs/phase1_semantic_graph.yaml"
  semantic_graph_cache: "cache/semantic_graph/2eebde04e582"
  phase2_cache: "cache/semantic_graph/2eebde04e582/phase2"
  stock_daily_path: "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily.parquet"
  stock_daily_basic_path: "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet"
  stock_sw_member_path: "/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet"
  logs_dir: "logs/phase2"
  plots_dir: "outputs/plots/phase2"
  reports_dir: "outputs/reports/phase2"

graph_candidate:
  candidate_k_existing: [10, 20, 50]
  candidate_k_optional_new: 100
  build_k100_if_missing: true
  metric: "inner_product_cosine_on_l2_normalized_vectors"
  mutual_definition: "reciprocal_directed_edge_rows"
  unique_undirected_pair_definition: "min(u,v),max(u,v)"
  rank_bands:
    core: [1, 5]
    strong: [1, 10]
    stable: [1, 20]
    context: [21, 50]
    extended: [51, 100]
  score_quantiles: [0.50, 0.70, 0.80, 0.90, 0.95, 0.99]
  adaptive_rules:
    min_neighbors: 3
    max_neighbors: 50
    max_rank: 100
    keep_mutual_always: true
    local_score_gap_quantile: 0.75

industry_baselines:
  levels: ["l1_name", "l2_name", "l3_name"]
  treat_current_sw_as_normalized_member: true
  random_seed: 20260510
  n_random_repeats: 200
  buckets:
    market_cap_quantiles: 10
    liquidity_quantiles: 10
  baseline_types:
    - global_random
    - same_l1_random
    - same_l2_random
    - same_l3_random
    - same_market_cap_bucket_random
    - same_liquidity_bucket_random
    - same_l3_and_mv_bucket_random
    - cross_l1_random

market_behavior:
  start_date: "20180101"
  end_date: "20260423"
  horizons: [1, 5, 20]
  returns:
    use_pct_chg: true
    winsorize_quantiles: [0.001, 0.999]
  neutralization:
    market_return: true
    current_sw_l1: true
    current_sw_l3: true
    market_cap_bucket: true
  pair_sampling:
    max_pairs_per_layer_for_corr: 500000
    preserve_all_core_edges: true
  metrics:
    - return_corr_daily
    - return_corr_weekly
    - return_corr_monthly
    - residual_return_corr
    - volatility_corr
    - amount_shock_corr
    - extreme_down_cooccurrence
    - extreme_up_cooccurrence

io:
  engine_priority: ["duckdb", "polars"]
  use_predicate_pushdown: true
  use_projection_pushdown: true
  write_parquet_compression: "zstd"
  progress_bar: true
  progress_granularity: "task_level"
  log_level: "INFO"
```

---

## 6. Phase 2 任务总览

Phase 2 建议拆成 9 个任务，分三批执行。

### 批次 A：修复 Phase 1 遗留问题，建立 Phase 2 边候选层

- T2.0：Phase 1 修复与测试报告缓存
- T2.1：构建 k=100 候选边，或至少统一 k=10/20/50 边表为候选边池
- T2.2：边层分解与真实分数分布

### 批次 B：行业、市值、流动性基准和域内分析

- T2.3：申万 L1/L2/L3、当前成分常态化标签覆盖与基准表
- T2.4：市值/流动性桶构建，行业 × 市值 × 流动性分域
- T2.5：topK/rank band/score band 的域内与跨域邻居统计

### 批次 C：hub、跨行业桥、市场行为关联

- T2.6：语义 hub 和桥接边研究
- T2.7：2018—2026 市场行为面板准备
- T2.8：语义边与收益/波动/成交共振的描述性统计
- T2.9：Phase 2 总结报告与下一阶段决策

每个任务都必须写入：

- `manifest.json`
- `run.log`
- 主要统计 `summary.json`
- 人类可读 `summary.md`
- 必要中间结果 `parquet`
- 必要图表 `png`

---

## 7. T2.0：Phase 1 修复与测试报告缓存

### 目标

先处理 Phase 1 遗留问题，不带着不一致状态进入 Phase 2。这个任务不做新研究，只修正契约和状态。

### 输入

- `PROJECT_STATE.md`
- `tests/*.py`
- `src/semantic_graph_research/semantic_loader.py`
- `src/semantic_graph_research/graph_builder.py`
- `src/semantic_graph_research/plotting.py`
- Phase 1 cache key `2eebde04e582`

### 必做修复

#### 1. alignment 增强

在 `semantic_loader.py` 中新增更严格检查：

- `len(row_ids) == vectors.shape[0]`
- `len(set(row_ids)) == len(row_ids)`
- `records_df["record_id"].is_unique`
- `records_df["stock_code"].is_unique`
- `row_ids` 中每一个 `record_id` 都能在 records 中找到
- `build_node_table` 构建后，`nodes.loc[i, "record_id"] == row_ids[i]`
- 输出 `alignment_diagnostics.json`，记录：
  - `row_ids_count`
  - `records_count`
  - `row_ids_unique_count`
  - `records_record_id_unique_count`
  - `stock_code_unique_count`
  - `row_order_binding_ok`
  - `missing_in_records_count`
  - `extra_in_records_count`

注意：这里不再讨论原始 dtype，因为你已经明确向量化结果目前只有这一版 float32。文档里仍然记录“Phase 2 不处理 dtype 争议”。

#### 2. self-neighbor 断言增强

`build_faiss_knn` 内部应在生成 `final_indices` 后立即断言：

```python
row_ids = np.arange(n, dtype=np.int32)
has_self = (final_indices == row_ids[:, None]).any()
if has_self:
    bad_rows = np.where((final_indices == row_ids[:, None]).any(axis=1))[0][:10]
    raise ValueError(f"self-neighbor remains after removal, examples={bad_rows.tolist()}")
```

同时检查每行是否填满 k：

```python
if count != k:
    raise ValueError(f"row {i} only has {count} non-self neighbors, expected {k}")
```

当前测试文件里已经逐行检查 `i not in indices[i]`，但构图脚本中的断言较弱，需要把强检查内置进核心函数，避免只有测试发现问题。

#### 3. mutual edge 定义澄清

保留当前 `edges_mutual_k*.parquet` 的语义，但在文档、字段和统计中明确：

- `n_mutual_edges_directed_rows`：互惠有向边行数。
- `n_mutual_pairs_unique`：唯一无向互惠 pair 数，通常等于互惠有向边行数 / 2，前提是无重复。
- `reciprocity_ratio = n_mutual_edges_directed_rows / n_directed_edges`。
- mutual component 建图时可以使用唯一无向 pair，避免重复 union。

建议新增 `mutual_pair_id`：

```python
u_pair = np.minimum(src_node_id, dst_node_id)
v_pair = np.maximum(src_node_id, dst_node_id)
mutual_pair_id = f"{u_pair}_{v_pair}"
```

#### 4. score distribution 修复

当前 `plot_score_distribution_from_cache` 应改为读取 `edges_directed_k20.parquet` 的真实 `score` 字段，至少输出：

- 全部 directed edge score histogram
- top1/top5/top10/top20/top50 分 rank 平均/中位数
- score by rank line plot
- score quantile table

输出文件：

- `cache/semantic_graph/2eebde04e582/phase2/edge_layers/score_distribution_k20.json`
- `outputs/plots/phase2/score_distribution_k20_true.png`
- `outputs/plots/phase2/score_by_rank_k20.png`

#### 5. 测试报告缓存与 PROJECT_STATE 更新

运行：

```bash
pytest -q tests | tee logs/phase2/phase1_pytest_YYYYMMDD_HHMMSS.log
```

生成：

- `outputs/reports/phase2/phase1_pytest_summary.md`
- `cache/semantic_graph/2eebde04e582/phase2/manifests/phase1_repair_manifest.json`

如果全部通过，把 `PROJECT_STATE.md` 的测试状态改为 PASSED，并新增 Phase 2 状态区；如果失败，不准进入 T2.1。

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/manifests/phase1_repair_manifest.json
cache/semantic_graph/2eebde04e582/phase2/manifests/alignment_diagnostics.json
outputs/reports/phase2/phase1_pytest_summary.md
logs/phase2/phase1_pytest_*.log
outputs/plots/phase2/score_distribution_k20_true.png
outputs/plots/phase2/score_by_rank_k20.png
```

### 失败条件

- row_id 重复
- records record_id 重复
- `node_id` 与 `row_ids` 逐行绑定失败
- self-neighbor 存在
- score 图仍然只用均值画 histogram
- pytest 未通过但 `PROJECT_STATE.md` 被标记为 PASSED

---

## 8. T2.1：扩展候选边池，支持不同股票变长邻居

### 目标

把固定 k 图升级为“候选边池”。这一步不是为了确定最终图，而是为了给后续分层研究提供足够候选边。你已经观察到 `edges_directed_k50.parquet`、`edges_mutual_k50.parquet` 本地只有 1—2MB 量级，说明保存更多边关系的成本不高；因此 Phase 2 可以构造 k=100 候选边。如果 k=100 生成成本也很低，推荐做；如果暂时不做，则先用已有 k=50。

### 输入

- Phase 1 真实向量
- `nodes.parquet`
- `neighbors_k10/k20/k50.npz`
- `edges_directed_k10/k20/k50.parquet`
- `edges_mutual_k10/k20/k50.parquet`

### 处理逻辑

1. 如果不存在 `neighbors_k100.npz`，使用 FAISS `IndexFlatIP` 生成 top100。由于 N=5502、D=1024，FlatIP 在 GPU 上成本可控。
2. 保存 `edges_directed_k100.parquet` 和 `edges_mutual_k100.parquet`。如果考虑 GitHub 轻量化，完整 parquet 可保留本地，不上传；但导出摘要 JSON 和抽样 Markdown。
3. 构建统一候选边池 `edge_candidates_k100.parquet`，字段包括：
   - `src_node_id`
   - `dst_node_id`
   - `src_stock_code`
   - `dst_stock_code`
   - `rank`
   - `score`
   - `is_mutual`
   - `reverse_rank`
   - `reverse_score`
   - `score_mean_if_mutual`
   - `rank_band`
   - `score_quantile_global`
   - `src_top1_score`
   - `src_score_gap_from_top1`
   - `src_score_rank_pct`
4. 计算每个节点的局部分数曲线：
   - top1、top5、top10、top20、top50、top100 score
   - top1-top5 gap
   - top1-top20 gap
   - top20-top50 gap
   - top50-top100 gap
   - local elbow 候选点

### 自适应邻居规则

Phase 2 不应该再只有固定 k。建议生成多个自适应边集：

#### adaptive_core

规则：

- `rank <= 20`
- `is_mutual == true` 优先
- `score >= max(global_p80, src_top1_score - local_gap_threshold)`
- 每个节点最少 3 条，最多 20 条

含义：高可信业务近邻。

#### adaptive_context

规则：

- `rank <= 50`
- `score >= global_p60`
- 每个节点最多 50 条
- mutual 加权，不强制 mutual

含义：中等语义上下文关系，可用于题材和风险传染候选。

#### adaptive_cross_industry_bridge

规则：

- `rank <= 100`
- `same_l1 == false` 或 `same_l3 == false`
- `score >= global_p75`
- mutual 边优先
- 排除超高 hub 入度边或给 hub 降权

含义：跨行业语义桥，不用于交易，只用于解释跨行业主题/产业链关系。

#### adaptive_within_l3_residual

规则：

- `same_l3 == true`
- `rank <= 50`
- 在同 L3 内按 score 排名
- 与同 L3 随机邻居对比

含义：研究语义图是否能在三级行业内部提供更细颗粒度结构。

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/edge_layers/edge_candidates_k100.parquet
cache/semantic_graph/2eebde04e582/phase2/edge_layers/edge_candidates_summary.json
cache/semantic_graph/2eebde04e582/phase2/edge_layers/adaptive_core_edges.parquet
cache/semantic_graph/2eebde04e582/phase2/edge_layers/adaptive_context_edges.parquet
cache/semantic_graph/2eebde04e582/phase2/edge_layers/adaptive_cross_industry_bridge_edges.parquet
cache/semantic_graph/2eebde04e582/phase2/edge_layers/adaptive_within_l3_residual_edges.parquet
outputs/reports/phase2/edge_layer_summary.md
outputs/plots/phase2/score_by_rank_k100.png
outputs/plots/phase2/adaptive_degree_distribution.png
logs/phase2/07_build_extended_edge_candidates.log
```

### 失败条件

- 候选图出现 self-loop
- 每节点候选边数不是 100，除非有明确解释
- adaptive 规则导致大量节点 0 邻居
- adaptive 规则没有保存配置和统计，无法复现
- 为了让边更多而降低到明显噪声阈值

---

## 9. T2.2：边层统计与真实分数分布

### 目标

系统认识不同 rank band、score band、mutual/non-mutual 边的结构差异。这是后续所有金融解释的前置步骤。

### 必算统计

#### 全局边分布

- directed edge count by k
- mutual directed row count by k
- unique mutual pair count by k
- reciprocity ratio by k
- score mean/median/std/min/max by k
- score quantiles：p1/p5/p10/p25/p50/p75/p90/p95/p99
- score by rank：每个 rank 的 mean/median/p10/p90
- rank band 的 score 分布

#### 节点层分布

- 每个节点入度
- mutual 入度
- adaptive_core degree
- adaptive_context degree
- cross_industry_bridge degree
- within_l3_residual degree
- hub score concentration
- local score gap

#### 互惠边理解

互惠有向边占比 0.586 不是简单的“边越多越好”。它说明在固定 k=20 下，接近 58.6% 的出边是 reciprocal 的。这个指标可以理解为局部语义空间的对称性。对称性强的区域通常代表稠密、稳定、可解释的语义团；对称性弱的区域可能代表 hub、边界节点、孤立股票或方向性近邻关系。

需要将 mutual 边分成两类：

- symmetric strong：u→v rank 很高，v→u rank 也很高，score_uv 与 score_vu 都高。这类边最像“稳定业务近邻”。
- asymmetric mutual：双方互为 topK，但 rank 差距大，例如 u 认为 v 是第 3，v 认为 u 是第 48。这类边可能说明一个小公司靠近大 hub，或一个细分公司落在更大业务簇边缘。
- non-mutual high score：u→v 分数高但 v 不回指 u，可能是 hub 或密度差造成。
- non-mutual low score：固定 k 被迫保留的弱边，通常只适合作候选，不适合强解释。

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/edge_layers/edge_score_distribution_k20.json
cache/semantic_graph/2eebde04e582/phase2/edge_layers/edge_score_distribution_k50.json
cache/semantic_graph/2eebde04e582/phase2/edge_layers/edge_score_distribution_k100.json
cache/semantic_graph/2eebde04e582/phase2/edge_layers/reciprocity_by_rank_band.json
cache/semantic_graph/2eebde04e582/phase2/edge_layers/node_degree_layers.parquet
outputs/plots/phase2/score_hist_by_rank_band.png
outputs/plots/phase2/reciprocity_by_rank_band.png
outputs/plots/phase2/adaptive_degree_by_layer.png
outputs/reports/phase2/edge_layer_diagnostics.md
```

---

## 10. T2.3：行业基准，重点加入三级行业

### 目标

研究语义边与当前申万 L1/L2/L3 的关系，并用随机基准、分域基准判断语义图是否只是行业分类复刻。

你已经明确 `stock_sw_member` 是当前最新成分，成分变化少，可以默认为常态化成分。Phase 2 按这个前提处理，但所有文档仍然标注“当前常态化行业标签”，不要写成历史逐日行业标签。

### 输入

- `nodes.parquet`
- `industry_join_current.parquet`
- `stock_sw_member.parquet`
- `edge_candidates_k100.parquet`
- adaptive edge layers

### 统计对象

对每个 edge layer、每个 rank band、每个 topK，计算：

- same_l1_ratio
- same_l2_ratio
- same_l3_ratio
- cross_l1_ratio
- cross_l2_ratio
- cross_l3_ratio
- by source industry 的均值、中位数、分位数
- by destination industry 的流入结构
- industry entropy
- industry concentration HHI
- 每个 L3 内的语义邻居集中度
- 每个 L3 跨出去的主要目标行业

### 基准设计

#### global random baseline

对每个 src，在全市场随机抽同样数量的 dst，重复 200 次，计算 same_l1/l2/l3 比例。用于判断语义图是否明显强于无条件随机。

#### same market cap bucket baseline

先用 2018—2026 或最近可用窗口计算市值分位桶。对每个 src，在同市值桶内随机抽同样数量 dst。用于判断语义近邻是否只是大市值/小市值相似。

#### same liquidity bucket baseline

用成交额、换手率或 amount 构造流动性桶。对每个 src，在同流动性桶内随机抽同样数量 dst。用于判断语义近邻是否只是流动性结构。

#### same L3 random baseline

对每个 src，在同三级行业内随机抽同样数量 dst。用于判断语义边在行业内部是否比随机同行更细。

#### same L3 + market cap bucket baseline

最强的行业内基准：同三级行业、同市值桶。若语义边在这个基准上仍能解释收益/波动共动，则很有价值。

#### cross L1 random baseline

对跨 L1 语义边，在跨 L1 的随机候选中抽样。用于评估跨行业桥是否真的有结构，而不是所有跨行业都随机噪声。

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/baselines/industry_baseline_summary.json
cache/semantic_graph/2eebde04e582/phase2/baselines/industry_purity_by_layer.parquet
cache/semantic_graph/2eebde04e582/phase2/baselines/random_baseline_samples_manifest.json
cache/semantic_graph/2eebde04e582/phase2/baselines/same_l3_random_baseline.parquet
cache/semantic_graph/2eebde04e582/phase2/baselines/cross_l1_random_baseline.parquet
outputs/plots/phase2/same_l3_ratio_by_rank_band.png
outputs/plots/phase2/semantic_vs_random_industry_purity.png
outputs/plots/phase2/industry_entropy_by_layer.png
outputs/reports/phase2/industry_baseline_report.md
logs/phase2/09_industry_size_liquidity_baselines.log
```

### 证伪重点

如果语义边的 same_l3_ratio 只比 global random 高，但不比 same size 或 same L3 random 更有信息，那么它更多是行业/规模复刻。若 cross_l1 high-score mutual 边在市场行为上显著高于 cross_l1 random，则它是 Phase 2 最值得保留的增量证据。

---

## 11. T2.4：市值和流动性分域

### 目标

把你提出的“三级行业、市值中分别做基准、做抽样和域内关系”落地。市值和流动性是 A 股中非常强的共同结构，若不控制，语义图可能只是把大公司与大公司、小公司与小公司连在一起。

### 数据窗口

建议使用 2018-01-01 至 2026-04-23。原因：

- 你已说明数据问题经过处理，停复牌退市等问题由数据自身解决。
- Phase 2 不是历史无偏交易回测，而是未来交易辅助前的历史关联研究。
- 2018—2026 覆盖近几年市场结构、题材行情和产业链变化，更贴近未来辅助用途。

### 市值指标

从 `stock_daily_basic` 读取：

- `total_mv`
- `circ_mv`
- `turnover_rate`
- `trade_date`

按股票计算：

- `median_total_mv_2018_2026`
- `median_circ_mv_2018_2026`
- `median_turnover_rate_2018_2026`
- `median_amount_2018_2026`，可从 daily 读 amount
- `mv_bucket_10`
- `liquidity_bucket_10`

注意：为了减少 IO，不应 `pd.read_parquet` 全表后再筛。优先使用 DuckDB SQL 对 Parquet 做列选择和日期过滤，或者用 Polars lazy scan 做 projection/predicate pushdown。

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/baselines/node_size_liquidity_profile.parquet
cache/semantic_graph/2eebde04e582/phase2/baselines/node_size_liquidity_summary.json
outputs/plots/phase2/market_cap_bucket_distribution.png
outputs/plots/phase2/liquidity_bucket_distribution.png
outputs/reports/phase2/size_liquidity_profile_report.md
```

### 失败条件

- 读取全量 parquet 后才筛日期和列，导致 IO 爆炸。
- 没有记录读取字段、日期窗口、过滤条件。
- 市值桶有大量 NaN 但未解释。
- 市值桶分布极不均衡但仍用于基准而不报告。

---

## 12. T2.5：域内与跨域邻居分析

### 目标

系统回答：

- 同三级行业内，语义图是否比随机同行更细？
- 同市值桶内，语义图是否还有业务解释？
- 跨行业边是否集中在少数主题/产业链？
- top5/10/20/50/100、middle、bottom 的关系是否不同？

### 推荐分析维度

#### topK

- top1
- top5
- top10
- top20
- top50
- top100

#### rank band

- 1—5
- 6—10
- 11—20
- 21—50
- 51—100

#### score band

- top 1% score
- top 5% score
- top 10% score
- middle 40%—60%
- lower candidate 10% within top100

#### domain

- same_l3
- same_l2 but different_l3
- same_l1 but different_l2
- cross_l1
- same_mv_bucket
- different_mv_bucket
- same_liquidity_bucket
- cross_l1 + same_mv_bucket
- same_l3 + same_mv_bucket

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/baselines/domain_neighbor_stats.parquet
cache/semantic_graph/2eebde04e582/phase2/baselines/domain_neighbor_summary.json
outputs/plots/phase2/domain_same_l3_by_topk.png
outputs/plots/phase2/domain_cross_l1_by_rank_band.png
outputs/plots/phase2/domain_score_boxplot.png
outputs/reports/phase2/domain_neighbor_analysis.md
```

### 解释原则

top5 强业务边如果 same_l3 很高，是合理的；top50/top100 如果 cross_l1 比例上升，也不一定是坏事，因为它可能反映题材或风险传染候选。不要把跨行业边直接判为噪声，也不要把同行业边直接判为有效。关键在于：它们与市场行为是否有超越基准的关系。

---

## 13. T2.6：语义 hub 与跨行业桥研究

### 目标

Phase 1 的入度标准差约 13.44，说明存在明显 hub。hub 是语义图中最需要深度分析的结构之一，因为它同时可能代表产业中心，也可能代表文本泛化噪声，还可能在图传播中造成污染。Phase 2 不做 smoothing，但必须判断 smoothing 是否“不一定合适”的原因。

### hub 指标

对每个节点计算：

- in_degree_k20/k50/k100
- mutual_in_degree
- adaptive_core_degree
- adaptive_context_degree
- cross_l1_in_degree
- cross_l3_in_degree
- neighbor_l1_entropy
- neighbor_l3_entropy
- avg_in_score
- avg_mutual_score_mean
- hub_score_concentration
- pagerank，可选，只做图结构描述
- bridge_score：跨行业高分边数量 / 总边数
- hub_type_candidate

### hub 类型初判

无需 Ollama，先用规则生成候选分类，人工以后再看：

1. 产业中心 hub  
   特征：边权高、mutual ratio 高、邻居行业集中或围绕产业链上下游。
2. 综合平台 hub  
   特征：邻居跨行业较多，但仍有业务逻辑，例如平台型公司、综合集团。
3. 题材中心 hub  
   特征：跨行业多、rank 分布中等、可能在主题行情里共振。
4. 文本泛化 hub  
   特征：行业熵高、边权不高、很多非 mutual、邻居样例语义空泛。
5. 数据异常候选 hub  
   特征：score 过高或接近 1 的边过多，可能是文本重复或向量重复，需要单独审计。

### 跨行业桥

跨行业桥不应只看 `same_l1 == false`。建议输出：

- high_score_cross_l1_mutual_edges
- high_score_cross_l3_mutual_edges
- rank_21_100_cross_l1_edges
- cross_l1_edges_by_src_industry_dst_industry
- bridge nodes：连接多个 L1 但不是纯 hub 的节点

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/hub_bridge/node_hub_scores.parquet
cache/semantic_graph/2eebde04e582/phase2/hub_bridge/top_hubs_by_layer.parquet
cache/semantic_graph/2eebde04e582/phase2/hub_bridge/cross_industry_bridge_edges.parquet
cache/semantic_graph/2eebde04e582/phase2/hub_bridge/industry_bridge_matrix.parquet
cache/semantic_graph/2eebde04e582/phase2/hub_bridge/hub_bridge_summary.json
outputs/plots/phase2/hub_indegree_distribution.png
outputs/plots/phase2/hub_entropy_vs_indegree.png
outputs/plots/phase2/cross_industry_bridge_heatmap.png
outputs/reports/phase2/hub_bridge_report.md
```

### 关键研究判断

如果最大 mutual component 覆盖 98.16%，说明主题关系和大结构关系很强，但这并不自动支持 smoothing。相反，过大的连通主体意味着多跳传播可能很快扩散到全市场，造成过平滑。Phase 2 应该明确记录：图结构有大主体，但当前只研究一跳边和边层，不进行图 smoothing。若未来要做 smoothing，必须先基于 hub 降权、边阈值、传播半径限制和残差市场行为证据。

---

## 14. T2.7：2018—2026 市场行为面板准备

### 目标

准备一个轻量、可复用、按节点对齐的市场行为面板，用于描述性统计，不用于回测和因子。

### 输入字段

`stock_daily`：

- `ts_code`
- `trade_date`
- `pct_chg`
- `close`
- `vol`
- `amount`

`stock_daily_basic`：

- `ts_code`
- `trade_date`
- `turnover_rate`
- `total_mv`
- `circ_mv`
- `pe_ttm`
- `pb`

只读取 2018-01-01 至 2026-04-23，且只读取节点股票。使用 DuckDB 或 Polars lazy scan 做列选择和日期过滤。

### 派生字段

- `ret_1d`
- `ret_5d`
- `ret_20d`
- `abs_ret_1d`
- `rv_5d`
- `rv_20d`
- `amount_chg_1d`
- `amount_z_20d`
- `turnover_z_20d`
- `market_ret_1d`
- `l1_ret_1d`
- `l3_ret_1d`
- `ret_1d_resid_market`
- `ret_1d_resid_l1`
- `ret_1d_resid_l3`

注意：残差可以先用简单减法，不必上复杂回归。Phase 2 的目标是解释，不是建模。

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/market_behavior/node_market_panel_2018_2026.parquet
cache/semantic_graph/2eebde04e582/phase2/market_behavior/market_panel_summary.json
cache/semantic_graph/2eebde04e582/phase2/market_behavior/market_panel_manifest.json
outputs/reports/phase2/market_panel_prepare_report.md
logs/phase2/12_market_panel_prepare_2018_2026.log
```

### 效率原则

- 不在 Python 中读全表再过滤。
- 不把所有 pair 展开成巨大日频笛卡尔积。
- 先做节点级面板，再按边集合分批计算。
- 对 pair correlation 采用 chunk：按 edge layer 分组、按 src_node_id 分块。
- 先保存中间收益矩阵或窄表，避免重复读 parquet。
- 使用 `zstd` 压缩保存 parquet。
- 每个任务只有任务级进度条，不要每只股票打印日志。

---

## 15. T2.8：语义边与市场行为关联

### 目标

在不做回测、不做图因子的前提下，检验语义边是否连接了市场行为相似或风险传染相关的股票对。

### 分析对象

- `adaptive_core_edges`
- `adaptive_context_edges`
- `adaptive_cross_industry_bridge_edges`
- `adaptive_within_l3_residual_edges`
- top5/top10/top20/top50/top100
- rank 21—50 middle edges
- rank 51—100 extended edges
- mutual-only edges
- non-mutual edges
- high hub exposure edges
- hub-removed edges

### 指标

#### 收益共动

- pair daily return correlation
- pair weekly return correlation
- pair monthly return correlation
- market residual return correlation
- L1 residual return correlation
- L3 residual return correlation

#### 波动共振

- abs return correlation
- 5日 realized volatility correlation
- 20日 realized volatility correlation
- downside volatility co-movement

#### 成交与题材热度

- amount_z_20d correlation
- turnover_z_20d correlation
- extreme amount shock co-occurrence
- extreme up co-occurrence
- extreme down co-occurrence

#### 分层比较

每个语义边层都要和对应基准比较：

- semantic edges vs global random
- semantic same_l3 edges vs same_l3 random
- semantic same_l3+mv edges vs same_l3+mv random
- semantic cross_l1 edges vs cross_l1 random
- semantic middle edges vs random middle-sized sample

### 重要限制

不能做“邻居收益预测目标收益”的回测曲线。可以做描述性 lead-lag 相关，但命名必须谨慎，例如：

- `lead_lag_association_summary`
- 不叫 `factor`
- 不叫 `alpha`
- 不叫 `strategy`
- 不生成组合净值

### 输出

```text
cache/semantic_graph/2eebde04e582/phase2/market_behavior/pair_behavior_by_layer.parquet
cache/semantic_graph/2eebde04e582/phase2/market_behavior/pair_behavior_baseline_comparison.parquet
cache/semantic_graph/2eebde04e582/phase2/market_behavior/market_behavior_summary.json
outputs/plots/phase2/return_corr_semantic_vs_baseline.png
outputs/plots/phase2/residual_corr_by_layer.png
outputs/plots/phase2/volatility_corr_by_layer.png
outputs/plots/phase2/amount_shock_cooccurrence_by_layer.png
outputs/reports/phase2/market_behavior_association_report.md
```

### 成功标准

- 至少一种语义边层在对应严格基准上表现出稳定更高的共动或共振。
- 结果不是由少数 hub 完全驱动。
- 结果在 topK、rank band、same_l3/cross_l1 分层中有可解释模式。
- 所有结果保留完整统计和失败情况。

### 失败标准

- 所有语义边层都不优于对应基准。
- 只有全市场原始收益相关有效，残差后消失。
- 去 hub 后消失。
- 仅由个别行业驱动且无法泛化。

---

## 16. T2.9：Phase 2 总结报告与下一阶段决策

### 目标

将 Phase 2 的所有统计、图表、失败、偏差、下一步建议合并成一个研究报告。报告重点不是“做了哪些脚本”，而是“语义图是否有金融解释价值”。

### 报告结构

1. Phase 2 边界声明
2. Phase 1 修复结果
3. 候选边池与自适应边层
4. 真实 score 分布与 rank band 解释
5. 行业 L1/L2/L3 基准结果
6. 市值/流动性分域结果
7. top5/top10/top20/top50/top100 和 middle/bottom 结果
8. hub 类型与跨行业桥
9. 2018—2026 市场行为关联
10. 证伪情况
11. 哪些边层值得保留
12. 哪些边层应丢弃
13. 是否允许 Phase 3 进入简单图信号
14. 仍然禁止什么
15. 下一阶段最小研究单元建议

### 输出

```text
outputs/reports/phase2/PHASE2_RESEARCH_SUMMARY.md
outputs/reports/phase2/PHASE2_RESEARCH_SUMMARY.json
cache/semantic_graph/2eebde04e582/phase2/manifests/phase2_final_manifest.json
PROJECT_STATE.md 更新
```

### Phase 3 决策标准

只有当 Phase 2 满足以下条件，Phase 3 才考虑“简单图信号”：

- 语义边在严格基准下存在市场行为关联。
- 跨行业桥或行业内残差边至少有一类显示增量。
- hub 问题可控，去 hub 后结果不完全消失。
- 中等边对题材/风险传染有解释性证据。
- 没有使用 GNN、回测、图因子来偷换 Phase 2 目标。

如果不满足，则 Phase 3 不进入交易信号，而应回到语义向量、行业解释、边质量抽样，或等待 Ollama 标注工具完善后做边类型标注。

---

## 17. 代码实现原则

Phase 2 允许新增模块，但不追求抽象优雅。优先简单、可读、可缓存。

### 推荐模块职责

`phase2_graph_layers.py`

- 读取 edge candidates
- 计算 mutual flag、reverse rank、rank band、score band
- 生成 adaptive edge layers

`phase2_baselines.py`

- 行业基准
- 市值/流动性桶
- 随机抽样
- 统计对比

`phase2_hub_bridge.py`

- hub score
- industry entropy
- bridge matrix
- hub 样例导出

`phase2_market_behavior.py`

- DuckDB/Polars 读取市场数据
- 构建 2018—2026 面板
- 分块 pair correlation
- baseline comparison

`phase2_report_tables.py`

- 将 parquet/json 汇总为 markdown 表格
- 输出报告所需表格

### 日志原则

- 每个脚本开头打印配置摘要。
- 每个大步骤打印耗时。
- 进度条只放在较长循环，不要每个小操作都 tqdm。
- 日志写入 `logs/phase2/*.log`。
- JSON manifest 记录开始时间、结束时间、输入文件、输出文件、行数、参数、状态。

### 缓存原则

- 任何耗时超过 30 秒或读取大 parquet 的结果都必须缓存。
- 图表脚本只读缓存，不重算市场面板。
- summary markdown 只读缓存，不重跑统计。
- 允许删除图表重画，但不允许重算上游。
- 每个 parquet 都配一个 summary JSON 或 manifest JSON。

---

## 18. 对 smoothing 的明确态度

Phase 2 不做 smoothing。原因不是 smoothing 一定错误，而是当前图有一个非常大的 mutual component，局部主题关系强，但也意味着信号传播容易扩散。若没有先弄清 hub、边强度、跨行业桥、行业内残差和市场行为关联，直接 smoothing 会把很多不同类型边混在一起。

Phase 2 对 smoothing 只保留一个结论接口：

- 如果 adaptive_core 与 within_l3_residual 边在市场行为上有清晰解释，未来可以考虑一跳局部平滑。
- 如果 adaptive_context 或 cross_industry_bridge 对风险/题材共振有解释，未来可以考虑事件期邻居统计。
- 如果 hub 污染严重，未来 smoothing 必须先 hub 降权或边稀疏化。
- 如果所有边层不优于基准，禁止进入 smoothing。

---

## 19. 关于中等边、top100 和题材传染

你的直觉是重要的：实际交易中，风险、题材、情绪传染不一定发生在最强业务相似股票之间。最强 top5 可能是同业务、同细分赛道；中等 rank 的边可能连接应用场景相近、产业链间接、概念主题相关的公司。Phase 2 因此要保留 top100 候选，而不是过早剪掉。

但 top100 不能全部当成有效边。建议将 top100 分成：

- top1—5：核心业务近邻
- top6—10：强业务邻居
- top11—20：稳定语义邻域
- top21—50：中等主题/产业链候选
- top51—100：弱主题/风险传染候选

对于题材传染，重点看：

- 成交额冲击共现
- 极端上涨共现
- 极端下跌共现
- 波动共振
- 事件期的同步性
- 跨 L1/L2 但语义 score 不低的边

Phase 2 不需要判断“谁带动谁”，只需要判断“中等语义边是否比随机跨域边更容易共振”。如果成立，后续再研究 lead-lag；如果不成立，就不要把 top100 用到模型里。

---

## 20. 最后一条总纲

Phase 2 的目标不是证明语义图一定有用，而是把“有用”拆成多个可以被数据证实或证伪的问题。固定 k 图只是候选图，自适应边层才是研究图；行业、市值、流动性基准是防止自欺；hub 和跨行业桥是理解语义图金融含义的核心；2018—2026 市场行为关联是进入未来交易辅助前最重要的描述性证据。

只要 Phase 2 能清楚回答：

1. 哪些边是真正强业务边；
2. 哪些边只是行业复刻；
3. 哪些边可能是跨行业主题/产业链桥；
4. 哪些 hub 有价值，哪些 hub 会污染；
5. 语义边是否在严格基准下连接市场行为；
6. 哪些边层值得保留到 Phase 3；

那么 Phase 2 就成功了。即使答案是否定的，也是一项有价值的研究资产，因为它会阻止你把无效图继续工程化。
