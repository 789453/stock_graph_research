# PHASE2_OLD_RESULTS_AUDIT

## 1. 审计目的
对 Phase 2 的研究结果进行系统性回顾，明确其作为 Phase 2.1 起点的有效性。识别已发现的 bug、逻辑错误和口径偏差，防止错误结论延续到多视图研究阶段。

## 2. 核心状态汇总

| 旧结果项 | 状态 | 审计结论与处理意见 |
|---|---|---|
| Phase 1 semantic audit | **VALID (HISTORICAL)** | 仅代表 `application_scenarios_json` 视图的历史对齐情况，Phase 2.1 需要对四个新视图重做审计。 |
| k20 graph stats | **PARTIALLY VALID** | 可作为早期低 k 值图结构的参考，但 Phase 2.1 统一使用 k=100。 |
| mutual_ratio = 1.0 | **INVALIDATED_BY_BUG** | **重大 Bug**：`phase2_graph_layers.py` 中互惠逻辑实现错误，导致几乎所有边都被误判为互惠。该结论不可信，必须重算。 |
| reverse_score | **INVALIDATED_BY_BUG** | **重大 Bug**：字典查询 Key 错误导致反向分数几乎全部丢失（为 0）。严重污染了 `score_mean_if_mutual`。 |
| size_liquidity_summary | **INVALIDATED_BY_BUG** | **口径错误**：`nodes_with_market_data=0` 与分桶结果并存，说明字段统计逻辑有误（`total_mv` vs `total_market_cap`）。必须使用修复后的行情侧字段重算。 |
| industry baseline | **PARTIALLY VALID** | 单视图（`application_scenarios_json`）下的行业 Lift 具有参考价值，但 Phase 2.1 需对比四视图的表现。 |
| domain baseline | **REQUIRES_RECOMPUTE** | 依赖于市值和流动性分桶的修复，当前结果不可靠。 |
| hub/bridge | **REQUIRES_RECOMPUTE** | 依赖于互惠逻辑修复和多视图数据。 |
| semantic_market_association | **STATIC_PROXY_ONLY** | 仅为静态横截面相关，不能解释为市场行为共振，更不能直接支持 H5 假设。 |
| PHASE2_RESEARCH_SUMMARY | **REQUIRES_REWRITE** | 存在 H5 结论冲突和 N/A 字段，需在 Phase 2.1 结束后重写。 |

## 3. 已识别的重大逻辑缺陷 (Must Fix)

1. **互惠边逻辑 (Mutual Logic)**：
   - **错误现象**：`mutual_ratio` 接近 1.0。
   - **根本原因**：在检查反向边时，存储 key 和查询 key 方向一致，导致自查自中。
   - **修复方案**：对边 `(u, v)`，必须检查是否存在 `(v, u)`。

2. **反向分数查询 (Reverse Score Lookup)**：
   - **错误现象**：`reverse_score` 几乎全是 0。
   - **根本原因**：使用了 DataFrame 的整数 index 作为字典 key，但查询时使用了 node_id tuple。
   - **修复方案**：使用 `(src, dst)` 映射到 `(rank, score)` 的哈希表或执行 self-merge。

3. **市值/流动性匹配 (Market Data Alignment)**：
   - **错误现象**：`nodes_with_market_data = 0` 但有分桶数据。
   - **根本原因**：合并字段名不匹配（`total_mv` 与 `total_market_cap` 混用）。
   - **修复方案**：统一使用修复后的 `median_total_mv` 等字段。

## 4. H5 假设状态更新

- **H5 (语义边预测市场共振)**：
  - **当前状态**：**REJECTED_STATIC_PROXY**。
  - **理由**：Phase 2 仅进行了静态分析，且分数与收益相关性极低 (0.0109)。Phase 2.1 将通过月度时序、残差相关和 Lead-Lag 重新检验。

## 5. 结论
Phase 2 证明了研究框架的可行性，但其金融结论受限于 bug 和静态视角，不能直接作为 Phase 2.1 的主结论。Phase 2.1 将冻结 `application_scenarios_json` 的结果为历史参考，全面转向四视图研究。
