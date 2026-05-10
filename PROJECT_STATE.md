# PROJECT_STATE

## 1. 当前项目阶段

- 当前阶段：Phase 2.2 完成 - 市场共振实证与多视图稳健性验证
- 当前研究问题：语义近邻图是否在控制了传统风险因子（行业、市值、流动性）后仍具有增量解释力？
- 当前只允许做的事情：
  - 使用 2018-2026 月度面板数据进行残差分解
  - 执行多层匹配随机基准测试 (Matched Random Baselines)
  - 进行 Hub 节点与 Near Duplicate 边的敏感性分析
  - 探索多视图（Main Business, Chain, Theme）的共识效应
- 当前明确不做的事情：
  - 不允许回测（Backtesting）
  - 不允许构建可交易因子（Alpha Factors）
  - 不允许使用 GNN 等黑盒模型进行特征提取

## 2. 真实数据源

### 语义
- 多视图支持：main_business_detail, chain_text, theme_text, full_text
- 向量路径：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/{view}/
- 记录路径：/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/parquet/records-all.parquet

### 行情
- 核心路径：/mnt/d/Trading/data_ever_26_3_14/data/silver/
- 研究窗口：2018-01-01 至 2026-04-23 (100 个月)
- 残差层级：Raw, Market-Neutral, L1-Neutral, L3-Neutral, Full-Neutral (Industry + Size + Liquidity)

## 3. Phase 2 任务状态汇总

| 任务 | 状态 | 产物 | 备注 |
|---|---|---|---|
| T2.0-2.9 | completed | PHASE2_RESEARCH_SUMMARY.md | Phase 2.1 基础架构与静态关联验证 |
| T2.2.0-2 | completed | edge_candidates_k100_fixed.parquet | 代码一致性修复与边表冻结 |
| T2.2.3-5 | completed | ret_resid_full_neutral.npy, edge_market_metrics.parquet | 月度面板构建与多层残差分解 |
| T2.2.6-8 | completed | h5_metric_tests.csv, sensitivity_analysis.csv | 随机基准检验与稳健性分析 |
| T2.2.9-11 | completed | PHASE2_2_RESEARCH_SUMMARY.md, comprehensive_viz/ | 全面可视化仪表盘与深度总结报告 |

## 4. 假设验证结论 (更新至 Phase 2.2)

| 假设 | 结论 | 证据 |
|---|---|---|
| H1: 不只是行业复刻 | ✅ **支持** | 语义近邻在行业中性后仍保留显著相关性。 |
| H2: Rank Band 含义 | ✅ **支持** | 物理层级 (001_005 vs 011_020) 展现出明显的共振衰减特性。 |
| H5: 市场共振预测 | ✅ **部分支持** | `main_business_detail` 在中性化后仍有显著 Delta Corr (Z-Score > 3)。 |
| H6: 题材传染 (Lead-Lag) | ✅ **部分支持** | `chain_text` 在跨行业边上展现出 1 月领先相关性。 |

## 5. 关键发现 (Phase 2.2)

1. **残差共振存在**：在剔除行业、市值、流动性影响后，主营业务相近的股票仍表现出显著的同步性。
2. **极端行情敏感性**：语义近邻在市场下行期的同步下跌概率显著高于随机配对。
3. **视图优劣明显**：`main_business_detail` 是捕捉共振最稳健的视图，而 `full_text` 包含过多噪声。
4. **Hub 稳健性**：共振效应并非由 Top 1% 的 Hub 节点（大盘股）驱动，具有全市场普适性。

## 6. 环境与工具状态

- **中文字体**: ✅ 已解决。使用 `WenQuanYi Micro Hei` 或 `CustomChineseFont` 路径加载方案。
- **绘图契约**: ✅ 已对齐。每张图表均配有对应的 CSV 数据和 JSON 元数据。
- **计算引擎**: ✅ 已优化。采用 NumPy 向量化分块计算，支持 50w+ 边的高速指标提取。

## 7. 仍未解决问题

1. **因果推断**: 当前相关性分析仍无法排除未观测因子的干扰。
2. **非线性关联**: 尚未探索语义相似度与市场共振之间的非线性（如阈值）关系。

## 8. 最近一次更新

- 更新时间：2026-05-10
- 更新人：Trae AI
- 关联提交：Phase 2.2 深度实证与可视化闭环完成
