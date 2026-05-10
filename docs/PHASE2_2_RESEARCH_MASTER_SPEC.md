# PHASE 2.2 总体研究规范：语义图市场共振与时序收益分解

## 0. 核心目标

Phase 2.2 的目标是回答一个比 Phase 2.1 更严格的问题：

> 在行业、市值、流动性、市场收益等控制之后，语义图边是否仍能解释股票之间的市场行为共振？

这里的“市场行为共振”不是静态 score-return 相关，也不是简单的平均收益差异，而应包括：

- 月度收益相关；
- 市场残差收益相关；
- 申万一级残差收益相关；
- 申万三级残差收益相关；
- 成交额 shock 共现；
- 换手率 shock 共现；
- 波动率共振；
- 极端上涨/下跌共现；
- lead-lag 方向性；
- 牛熊/高波动/行业主题 regime 下的稳定性。

Phase 2.2 仍然不是回测阶段。输出可以证明“语义边有解释价值”或“语义边在当前定义下无增量”，但不能直接宣称 alpha。

## 1. 当前项目状态判断

Phase 2.1 已经生成了四个 view 的基础结果：

- `main_business_detail`
- `theme_text`
- `chain_text`
- `full_text`

并已经把 `matched_market_nodes` 修复到 5502/5502，说明市场 profile 对齐在报告层面已经完成。但 Phase 2.2 必须先复核以下一致性问题：

1. 测试文件是否引用了当前源码中真实存在的函数；
2. `graph_builder.py` 是否真正包含 `derive_mutual_edges_fast`；
3. `phase2_graph_layers.py` 是否真正包含 `assign_rank_band_exclusive`、`prepare_nodes_index`、`build_edge_candidates_fixed`；
4. 旧 `build_edge_candidates` 中 reverse_score 字典 key 错误是否仍在主路径中；
5. Phase 2.1 报告声称 FIXED 的项目，是否由源码、测试、cache manifest 三者共同证明。

若上述任何一点不通过，Phase 2.2 的 T2.2.0 必须先修复，不得继续市场行为研究。

## 2. 研究边界

### 2.1 允许

- 使用四个已存在 view；
- 使用现有 embedding，不重新 embedding；
- 使用 k=100 图；
- 使用 kNN 边表、mutual 边、rank band、view overlap；
- 使用 Tushare 日频行情和日频基本指标；
- 构造月度、周度、日度统计面板；
- 构造行业、市值、流动性、中性化残差；
- 使用随机边、同 L3 随机边、跨 L1 随机边、size/liquidity matched random；
- 输出大量中间 CSV/JSON/YAML/Parquet/PNG；
- 做事件/窗口/分 regime 描述性分析；
- 做 permutation、bootstrap、block bootstrap 等统计稳健性检查。

### 2.2 禁止

- 新 embedding；
- GNN；
- 回测；
- 交易组合；
- 图因子；
- 使用未来不可得信息做预测；
- 把 lead-lag 描述写成可交易 alpha；
- 把静态 cross-sectional score 直接解释为市场共振；
- 把 `same_l3_random=1.0` 这种由抽样条件决定的指标解释为发现；
- 忽略行业、市值、流动性控制。

## 3. H5 重新定义

旧 H5：

> 语义边能解释市场行为共振。

Phase 2.2 中重写为：

> H5.1：语义边的月度残差收益相关显著高于 matched random 边。  
> H5.2：语义边的成交额/换手 shock 共现显著高于 matched random 边。  
> H5.3：跨行业语义边在控制 size/liquidity 后仍存在显著 residual co-movement。  
> H5.4：`chain_text` 的跨行业边在 1/2/3 月 lead-lag 上优于随机跨行业边。  
> H5.5：`theme_text` 的中等 rank 边在极端上涨/题材扩散共现上优于强同行边。  
> H5.6：多 view consensus 边比单 view 边更稳定。

## 4. 结果解释准则

| 结果形态 | 解释 |
|---|---|
| 原始收益相关高，行业残差后消失 | 语义边主要复制行业暴露 |
| 同 L3 控制后仍高于随机 | 行业内业务语义有增量 |
| 跨 L1 控制后仍高于随机 | 可能存在产业链/题材桥 |
| 成交额 shock 共现高但收益相关弱 | 语义边可能解释关注度/流动性而非收益 |
| lead-lag 不稳定 | 不足以进入策略研究 |
| 只有少数月份显著 | 可能是 regime/事件驱动，需要分阶段研究 |
| 多 view consensus 显著 | 稳健业务关系可能更强 |
| near duplicate 边驱动显著性 | 结果不可信，需去重后重测 |

## 5. 验收标准

Phase 2.2 完成时必须交付：

1. 代码一致性修复报告；
2. 四 view 统一边表 manifest；
3. 月度节点面板；
4. 至少三类残差收益矩阵；
5. 语义边 vs 多类随机边的市场共振指标；
6. 每个 view、每个 rank band 的 H5 结论；
7. 多 view overlap 与 consensus 分析；
8. 中文图表不少于 30 张；
9. CSV/JSON/YAML 输出契约完整；
10. 测试全部通过；
11. 最终 `PHASE2_2_RESEARCH_SUMMARY.md` 不得有 N/A、空 JSON、互相矛盾结论。
