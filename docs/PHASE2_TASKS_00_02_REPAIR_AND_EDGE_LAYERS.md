# PHASE2_TASKS_00_02_REPAIR_AND_EDGE_LAYERS

## T2.0 Phase 1 repair and test report

目标：修复 alignment、self-neighbor、mutual 命名、score distribution、PROJECT_STATE 测试状态。

步骤：
1. 增强 `semantic_loader.py` 对重复 record_id、重复 stock_code、row_ids 与 records 的逐行绑定检查。
2. 增强 `graph_builder.py` 在核心函数内检查 self-neighbor 与每行填满 k。
3. 修改 mutual 统计命名，保留 `n_mutual_edges_directed_rows` 与 `n_mutual_pairs_unique`。
4. 修改 plotting，真实读取 `edges_directed_k20.parquet.score` 画分布。
5. 运行 pytest，写 `outputs/reports/phase2/phase1_pytest_summary.md`。
6. 更新 PROJECT_STATE：测试通过则 PASSED，阶段转入 Phase 2。

输出：见主文档 T2.0。

## T2.1 Extended edge candidate pool

目标：构建 k100 候选边池，或至少统一 k10/k20/k50 成为候选边。

核心思想：固定 k 是候选生成，不是最终图。Phase 2 用候选边池生成变长研究边层。

边层：
- adaptive_core
- adaptive_context
- adaptive_cross_industry_bridge
- adaptive_within_l3_residual

输出：`edge_candidates_k100.parquet` 与各类 adaptive edges。

## T2.2 Edge layer diagnostics

目标：真实 score 分布、rank band、mutual/non-mutual、节点 degree、自适应 degree。

必须输出：
- score histogram by rank band
- score by rank line plot
- reciprocity by rank band
- adaptive degree distribution
- edge_layer_diagnostics.md
