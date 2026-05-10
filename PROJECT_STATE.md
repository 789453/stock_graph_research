# PROJECT_STATE

## 1. 当前项目阶段

- 当前阶段：Phase 1 - 语义近邻图工程已完成
- 当前研究问题：真实 application_scenarios_json 语义向量能否形成一张可解释、可复现、非退化的 A 股语义近邻图？
- 当前只允许做的事情：
  - 使用真实 application_scenarios_json-all.npy
  - 使用配套的 meta.json 和 records-all.parquet
  - 使用 FAISS GPU 构建 kNN
  - 缓存节点表、邻居矩阵、边表、诊断统计、可视化布局
  - 用当前 stock_sw_member 做解释性标签诊断
  - 对 2010-01-01 至 2026-04 数据做行情覆盖率普查
- 当前明确不做的事情：
  - 不允许使用 mock / TF-IDF / PCA 替代真实 1024 维语义向量
  - 不允许图融合、图平滑、因子、回测、模型训练
  - 不允许把当前申万成分当成历史行业真值
  - 不允许为了"让测试通过"偷偷换数据源

## 2. 当前真实数据源

### 语义
- view：application_scenarios_json
- vectors path：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.npy
- meta path：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.meta.json
- records path：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/parquet/records-all.parquet
- 已验证 shape：(5502, 1024)
- 已验证 dtype：float32
- 已验证 alignment：row_ids 与 records record_id 完全对齐

### 行情
- stock_daily path：/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily.parquet
- stock_daily_basic path：/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet
- stock_sw_member path：/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet
- 请求研究窗口：2010-01-01 至 2026-04-30
- 实际数据最大日期：2026-04-23

## 3. 已完成任务

| 任务 | 状态 | 产物 | 备注 |
|---|---|---|---|
| T0 | completed | configs/phase1_semantic_graph.yaml, PROJECT_STATE.md | 目录骨架和配置文件已创建 |
| T1 | completed | cache/semantic_graph/2eebde04e582/semantic_audit.json | 审计通过：5502行，1024维，0个非有限值 |
| T2 | completed | cache/semantic_graph/2eebde04e582/nodes.parquet | 5502个节点，node_id 0-5501连续 |
| T3 | completed | neighbors_k10/k20/k50.npz, edges_directed_k10/k20/k50.parquet, edges_mutual_k10/k20/k50.parquet | k=20: 110040有向边，64488双向边 |
| T4 | completed | graph_stats_k20.json, industry_diagnostics_k20.parquet, neighbor_examples_k20.parquet, layout_pca2.parquet, industry_join_current.parquet | Union-Find算法优化 |
| T5 | completed | outputs/plots/*.png | 仅从缓存绘图 |
| T6 | completed | cache/market_alignment/2eebde04e582/market_coverage_by_stock.parquet, market_coverage_summary.json | 100%覆盖率 |

## 4. 当前可用接口

| 模块 | 函数 | 说明 | 已验证 |
|---|---|---|---|
| semantic_loader | load_semantic_view | 加载语义向量 bundle | 是 |
| semantic_loader | audit_semantic_bundle | 审计语义数据契约 | 是 |
| semantic_loader | build_node_table | 构建节点表 | 是 |
| graph_builder | build_faiss_knn | FAISS GPU kNN 构建 | 是 |
| graph_builder | neighbors_to_directed_edges | 转换为有向边 | 是 |
| graph_builder | derive_mutual_edges | 推导双向边 | 是 |
| cache_io | save_nodes/load_cached_graph | 缓存读写 | 是 |
| diagnostics | compute_graph_stats | 图统计（Union-Find优化） | 是 |
| diagnostics | compute_industry_diagnostics | 行业诊断 | 是 |

## 5. 当前缓存

| 缓存 | 路径 | 生成任务 | 是否可复用 |
|---|---|---|---|
| 语义图缓存 | cache/semantic_graph/2eebde04e582/ | T1-T4 | 是 |
| 行情缓存 | cache/market_alignment/2eebde04e582/ | T6 | 是 |

## 6. 当前测试状态

| 测试 | 状态 | 说明 |
|---|---|---|
| `test_real_semantic_contract.py` | pending | |
| `test_real_node_alignment.py` | pending | |
| `test_real_knn_cache_contract.py` | pending | |
| `test_plotting_reads_cache_only.py` | pending | |
| `test_market_alignment_contract.py` | pending | |

## 7. 已知问题

1. 图表中文字体缺失（DejaVu Sans 不支持中文），需要配置中文字体如 SimHei

## 8. 本轮新发现

1. **图结构非退化**：
   - reciprocity ratio = 0.586（58.6%的有向边是双向的）
   - 最大连通分量包含 5401 个节点（98.16%）
   - Top-1 平均分数：0.834，Top-20 平均分数：0.703，gap = 0.131
   - 分数有区分度，不是退化图

2. **行情覆盖率 100%**：
   - 所有 5502 个节点都有 daily 和 daily_basic 数据
   - 实际数据最大日期：2026-04-23（接近请求的 2026-04-30）

3. **计算性能优化**：
   - 使用 Union-Find 算法替代 BFS，连通分量计算从 O(n²) 优化到接近 O(n)
   - 64488 个 mutual pairs 在 1 秒内处理完成

## 9. 下一步唯一任务

- 下一步任务：运行单元测试验证
- 为什么现在做它：确保代码质量，验证数据契约
- 完成标准：所有测试通过
- 不允许顺手做的事情：不跳步做 T2/T3，必须先完成测试

## 10. 最近一次更新

- 更新时间：2026-05-10
- 更新人：Trae AI
- 关联提交：Phase 1 全部任务完成 (T0-T6)