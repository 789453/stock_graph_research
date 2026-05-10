# PROJECT_STATE_PHASE2_UPDATE_TEMPLATE

## 1. 当前阶段

- 当前阶段：Phase 2 - 语义图解释力与市场行为关联验证
- 上游 Phase 1 cache key：2eebde04e582
- 当前研究问题：语义图是否在申万三级行业、市值、流动性等基准之外，保留可解释的市场行为关联？

## 2. Phase 2 明确允许

- 使用 Phase 1 真实语义图缓存。
- 构建 k100 候选边。
- 研究 top5/top10/top20/top50/top100。
- 研究 middle/tail candidate edges。
- 研究当前申万 L1/L2/L3 常态化标签。
- 构造市值桶、流动性桶。
- 研究 hub、跨行业桥。
- 使用 2018-2026 市场行为做描述性关联。
- 保存 md/json/log/yaml/parquet/png。

## 3. Phase 2 明确禁止

- GNN
- 回测
- 图因子
- Ollama 自动标注
- 新 embedding
- 生产化系统

## 4. 测试状态

| 测试 | 状态 | 报告 |
|---|---|---|
| Phase 1 pytest | TODO/PASSED/FAILED | outputs/reports/phase2/phase1_pytest_summary.md |
| alignment enhanced | TODO/PASSED/FAILED | cache/.../alignment_diagnostics.json |
| self-neighbor strong check | TODO/PASSED/FAILED | logs/phase2/... |
| plotting cache-only | TODO/PASSED/FAILED | outputs/reports/phase2/... |

## 5. Phase 2 任务状态

| 任务 | 状态 | 产物 |
|---|---|---|
| T2.0 repair | TODO | |
| T2.1 edge candidates | TODO | |
| T2.2 edge diagnostics | TODO | |
| T2.3 industry baselines | TODO | |
| T2.4 size/liquidity domains | TODO | |
| T2.5 domain analysis | TODO | |
| T2.6 hub/bridge | TODO | |
| T2.7 market panel | TODO | |
| T2.8 market behavior association | TODO | |
| T2.9 summary | TODO | |
