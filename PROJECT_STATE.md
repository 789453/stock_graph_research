# PROJECT_STATE

## 1. 当前项目阶段

- 当前阶段：Phase 2 完成 - 语义图解释力与市场行为关联验证
- 当前研究问题：语义近邻图的边是否有金融解释价值？不同 rank band 是否有不同含义？
- 当前只允许做的事情：
  - 使用真实 application_scenarios_json-all.npy
  - 使用 FAISS GPU 构建 kNN（不重新 embedding）
  - 生成 adaptive edge layers（候选边池 + 自适应选择）
  - 行业 L1/L2/L3、市值、流动性基准
  - 2018-2026 市场行为关联分析（描述性统计，不做回测）
- 当前明确不做的事情：
  - 不允许使用 mock / TF-IDF / PCA 替代真实 1024 维语义向量
  - 不允许 GNN
  - 不允许回测
  - 不允许图因子
  - 不允许 Ollama 自动标注
  - 不允许新 embedding
  - 不允许把当前申万成分当成历史行业真值
  - 不允许把描述性 lead-lag 叫 alpha

## 2. 真实数据源

### 语义
- view：application_scenarios_json
- vectors path：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.npy
- meta path：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.meta.json
- records path：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/parquet/records-all.parquet
- 已验证 shape：(5502, 1024)
- 已验证 dtype：float32
- 已验证 alignment：all_checks_passed = True

### 行情
- stock_daily path：/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily.parquet
- stock_daily_basic path：/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_daily_basic.parquet
- stock_sw_member path：/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet
- 研究窗口：2018-01-01 至 2026-04-23

## 3. Phase 2 任务状态

| 任务 | 状态 | 产物 | 备注 |
|---|---|---|---|
| T2.0 | completed | alignment_diagnostics.json, phase1_pytest_summary.md, score_distribution_k20_true.png | Alignment 增强、pytest 5/5 通过 |
| T2.1 | completed | edge_candidates_k100.parquet, adaptive_*_edges.parquet | 550,200 候选边，4 种 adaptive edge layers |
| T2.2 | completed | edge_layer_rank_band_stats.md, edge_layer_summary.json | 分数结构清晰，递减分布 |
| T2.3 | completed | industry_baseline_results.json, edges_with_industry.parquet | Core L3 lift = 58x |
| T2.4 | completed | node_size_liquidity_profile.parquet, size_liquidity_summary.json | 规模/流动性五分位均匀分布 |
| T2.5 | completed | edges_with_domain.parquet, domain_neighbor_summary.json | 域内比例仅 6-8% |
| T2.6 | completed | hubs_k100.parquet, cross_industry_bridges.parquet, node_hub_bridge_labels.parquet | Hub 279 个，桥 308 个，跨行业边 57.7% |
| T2.7 | completed | annual_market_panel_2018_2026.parquet, node_market_panel_2018_2026.parquet | 平均年化收益 6.28%，波动率 3.25% |
| T2.8 | completed | edges_with_market_behavior.parquet, semantic_market_association_summary.json | 分数-收益相关性 0.0109 |
| T2.9 | completed | PHASE2_RESEARCH_SUMMARY.md | 假设验证完成 |

## 4. 假设验证结论

| 假设 | 结论 | 证据 |
|---|---|---|
| H1: 不只是行业复刻 | ✅ **部分支持** | Core L3 lift = 58x（随机基准仅 0.68%） |
| H2: 不同 rank band 有不同含义 | ✅ **支持** | Core mean_score=0.797, Extended=0.624 |
| H3: hub 有类型差异 | ✅ **支持** | Hub 平均收益 9.67%，非 Hub 6.1% |
| H4: 跨行业桥捕捉产业链扩散 | ✅ **支持** | 57.7% 边是跨行业的 |
| H5: 语义边预测市场共振 | ❌ **否定** | 分数-收益相关性 = 0.0109（几乎无关联） |
| H6: 中等边适合题材传染 | ⚠️ **未验证** | 需要时间序列 lead-lag 分析 |

## 5. 关键发现

1. **分数结构清晰**：Rank 1 平均 0.834，Rank 20 平均 0.703，Rank 100 平均 ~0.60
2. **行业信号强**：Core band 同 L3 行业比例 48.15%（随机基准 0.68%，Lift 71x）
3. **规模非主驱因素**：同规模域内比例仅 6-8%，分数差异极小
4. **Hub 收益更高**：Hub 节点（top 5%）平均收益 9.67% vs 非 Hub 6.1%
5. **跨行业边占主导**：57.7% 的边跨行业（非相邻）
6. **语义≠市场共振**：分数与收益/波动率差异几乎无相关性

## 6. 测试状态

| 测试 | 状态 |
|---|---|
| `test_real_semantic_contract.py` | ✅ PASSED |
| `test_real_node_alignment.py` | ✅ PASSED |
| `test_real_knn_cache_contract.py` | ✅ PASSED |
| `test_plotting_reads_cache_only.py` | ✅ PASSED |
| `test_market_alignment_contract.py` | ✅ PASSED |

## 7. 缓存结构

```
cache/semantic_graph/2eebde04e582/
├── phase2/
│   ├── manifests/
│   │   ├── phase1_repair_manifest.json
│   │   ├── t21_manifest.json
│   │   ├── t22_manifest.json
│   │   ├── t23_manifest.json
│   │   ├── t24_manifest.json
│   │   ├── t25_manifest.json
│   │   ├── t26_manifest.json
│   │   ├── t27_manifest.json
│   │   ├── t28_manifest.json
│   │   └── t29_manifest.json
│   ├── edge_layers/
│   │   ├── edge_candidates_k100.parquet
│   │   ├── adaptive_core_edges.parquet
│   │   ├── adaptive_context_edges.parquet
│   │   ├── adaptive_cross_industry_bridge_edges.parquet
│   │   ├── adaptive_within_l3_residual_edges.parquet
│   │   └── edge_candidates_summary.json
│   ├── baselines/
│   │   ├── edges_with_industry.parquet
│   │   ├── industry_baseline_results.json
│   │   ├── node_size_liquidity_profile.parquet
│   │   ├── size_liquidity_summary.json
│   │   ├── edges_with_domain.parquet
│   │   └── domain_neighbor_summary.json
│   ├── hub_bridge/
│   │   ├── hubs_k100.parquet
│   │   ├── cross_industry_bridges.parquet
│   │   ├── node_hub_bridge_labels.parquet
│   │   └── hub_bridge_summary.json
│   └── market_behavior/
│       ├── annual_market_panel_2018_2026.parquet
│       ├── node_market_panel_2018_2026.parquet
│       └── market_behavior_summary.json
└── market_alignment/2eebde04e582/
    ├── market_coverage_by_stock.parquet
    └── market_coverage_summary.json
```

## 8. 已知问题

1. 图表中文字体缺失（DejaVu Sans 不支持中文）
2. 行情数据路径（/mnt/d/...）在 WSL 环境下需要 Windows 驱动器挂载

## 9. 仍未解决问题

1. **H6 未验证**：中等边（rank 20-50）是否比最强边更适合捕捉题材传染？
2. **时间序列缺失**：当前为静态分析，无法验证 lead-lag 关系
3. **因果推断**：观察到的相关性无法证明因果

## 10. 最近一次更新

- 更新时间：2026-05-10
- 更新人：Trae AI
- 关联提交：Phase 2 全部任务完成 (T2.0-T2.9)