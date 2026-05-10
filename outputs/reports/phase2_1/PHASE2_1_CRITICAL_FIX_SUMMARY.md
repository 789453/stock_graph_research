# Phase 2.1 Critical Local Fixes & Multi-View Baseline Report

## 1. Overview
本报告总结了对 Phase 2 遗留问题的深度修复以及 Phase 2.1 四视图基础统计的重新生成。按照 `PHASE2_1_3_CRITICAL_LOCAL_FIX_GUIDE.md` 的要求，我们完成了从构图逻辑到金融基准的全链路修复。

## 2. 核心修复清单 (T2.1.3)

| 修复项 | 状态 | 验证方法 |
|---|---|---|
| Mutual 逻辑修复 | ✅ FIXED | `mutual_ratio` 从 1.0 降至 ~0.5，已通过 `derive_mutual_edges_fast` 验证。 |
| Reverse Score 修复 | ✅ FIXED | `reverse_score` 字典查询 Bug 已修，互惠边的反向分数非空率达 100%。 |
| Rank Band 命名规范 | ✅ FIXED | 统一使用 `rank_001_005` 等物理含义明确的命名，废弃 core/strong 等模糊命名。 |
| Node Index 不变量 | ✅ FIXED | 强制校验 `node_id` 必须为 0..n-1 且与 DataFrame Index 对齐。 |
| Near Duplicate 审计 | ✅ FIXED | 输出 `near_duplicate_edges.csv`，对 score >= 0.999999 的边进行标记。 |
| Self-Edge 清理 | ✅ FIXED | 强制校验 `src != dst` (node_id, stock_code, record_id)。 |

## 3. 多视图基础统计 (T2.1.4)

| 视图 | Nodes | Edges (k100) | Mutual Ratio | Same L3 (Top 5) | Same L3 (Top 100) |
|---|---:|---:|---:|---:|---:|
| main_business_detail | 5502 | 550,200 | 0.4932 | 0.4265 | 0.2814 |
| theme_text | 5502 | 550,200 | 0.4942 | 0.3506 | 0.2115 |
| chain_text | 5502 | 550,200 | 0.5765 | 0.4028 | 0.2542 |
| full_text | 5502 | 550,200 | 0.5742 | 0.3463 | 0.2087 |

## 4. 市值/流动性 Profile (T2.1.5)
- **Matched Nodes**: 5502 / 5502 (100% 对齐)
- **方法**: 使用 DuckDB 高效计算 2018-01-01 至今的中位数指标。
- **分桶**: 完成 `total_mv_bucket_10` 和 `turnover_rate_bucket_10` 划分。

## 5. 组合基准分析 (T2.1.6)
对每个视图执行了 6 类组合基准测试，验证语义边的增量信息：
- **Incremental Info**: 在 `main_business_detail` 视图中，`rank_001_005` 的 `same_l3_ratio` (0.4265) 显著高于 `same_l3_same_size_random` 基准。
- **Cross L1 Analysis**: 语义边在跨行业连接上的表现优于随机基准，为后续 Hub/Bridge 分析提供了基础。

## 6. H5 假设状态更新
按照 P6 规约，对 H5 假设进行重新定性：

- **H5 (语义边预测市场共振)**: **REJECTED_STATIC_PROXY**
- **理由**: Phase 2 的静态横截面相关性极低。Phase 2.1 将通过月度时序、残差相关和 Lead-Lag 重新检验，目前状态为 **NOT_RETESTED_MONTHLY**。

## 7. 结论
Phase 2.1 的“地基”已重新打好。边表 `edge_candidates_k100.parquet` 的正确性、互惠性、反向分数和行业对齐均已通过严苛审计。

**下一步计划**:
- 进入 `T2.1.7` Hub/Bridge 节点识别。
- 执行 `T2.1.8` 语义层级动态演化分析。
- 最终通过月度收益残差矩阵验证 H5 假设。
