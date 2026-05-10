# DOC_INDEX_PHASE2_1.md

## 1. 文档目的

本索引用于 Phase 2.1：多语义 view 修复、稳健基准与月度时序关联重验。它不是 Phase 2 的简单改名，而是对 Phase 2 中已发现问题的修复、对研究对象的升级、对金融证据链的重建。

Phase 2.1 的主研究对象不再是单一 `application_scenarios_json`，而是四个语义 view：

- `main_business_detail`
- `theme_text`
- `chain_text`
- `full_text`

每个 view 必须独立审计、独立构图、独立缓存、独立出报告，最后再做 multi-view 汇总。旧的 `application_scenarios_json` 结果只保留为历史参考，不再作为 Phase 2.1 主研究结论。

---

## 2. 推荐阅读顺序

### 2.1 每个新会话必须先读

1. `PROJECT_STATE.md`
2. `docs/a_share_semantic_dataset_数据格式说明.md`
3. `docs/tushare-data-README.md`
4. `docs/PHASE2_1_COMPLETE_CONTINUOUS_SPEC.md`
5. `docs/DOC_INDEX_PHASE2_1.md`

### 2.2 做代码修复前读

1. `docs/PHASE2_1_AI_WORKING_PROTOCOL_UPDATE.md`
2. `docs/PHASE2_1_CACHE_CONTRACTS.md`
3. `docs/PHASE2_1_TASKS_00_02_REPAIR_AND_MULTI_VIEW_EDGE_LAYERS.md`

### 2.3 做行业、市值、流动性基准前读

1. `docs/PHASE2_1_RESEARCH_HYPOTHESES_AND_FALSIFICATION.md`
2. `docs/PHASE2_1_TASKS_03_05_BASELINES_AND_DOMAINS.md`
3. `configs/phase2_1_multi_view_research.yaml`

### 2.4 做 hub、bridge、月度市场行为前读

1. `docs/PHASE2_1_TASKS_06_09_HUB_BRIDGE_MARKET_BEHAVIOR.md`
2. `docs/PHASE2_1_CACHE_CONTRACTS.md`
3. `docs/PHASE2_1_RESEARCH_HYPOTHESES_AND_FALSIFICATION.md`

### 2.5 更新状态前读

1. `docs/PHASE2_1_PROJECT_STATE_UPDATE_TEMPLATE.md`
2. `outputs/reports/phase2_1/*`
3. `cache/semantic_graph/multi_view/manifests/*`

---

## 3. Phase 2.1 文档列表

| 文档 | 用途 |
|---|---|
| `PHASE2_1_COMPLETE_CONTINUOUS_SPEC.md` | 连续完整主规格文档，定义总边界、任务、结果解释 |
| `DOC_INDEX_PHASE2_1.md` | 当前文档，给 AI 和人类一个阅读入口 |
| `PHASE2_1_AI_WORKING_PROTOCOL_UPDATE.md` | 约束 Trae/AI 的工作方式，防止任务漂移 |
| `PHASE2_1_CACHE_CONTRACTS.md` | 定义四 view、多 view、市场行为、报告缓存格式 |
| `PHASE2_1_PROJECT_STATE_UPDATE_TEMPLATE.md` | 定义 PROJECT_STATE 如何更新 |
| `PHASE2_1_RESEARCH_HYPOTHESES_AND_FALSIFICATION.md` | 研究假设、证伪条件、H5 新定义 |
| `PHASE2_1_SEMANTIC_GRAPH_RESEARCH_IMPLEMENTATION_2026_05_10.md` | 实施总纲补充，承接主文档但更偏落地清单 |
| `PHASE2_1_TASKS_00_02_REPAIR_AND_MULTI_VIEW_EDGE_LAYERS.md` | 旧结果冻结、四 view audit、k100、多 view edge candidates |
| `PHASE2_1_TASKS_03_05_BASELINES_AND_DOMAINS.md` | 行业、规模、流动性、随机基准、score 回归 |
| `PHASE2_1_TASKS_06_09_HUB_BRIDGE_MARKET_BEHAVIOR.md` | hub/bridge、月度面板、lead-lag、multi-view summary |

---

## 4. 当前必须记住的结论

Phase 2.1 开始时，必须接受以下事实：

1. Phase 2 旧结果不是全部作废，但关键金融结论不能直接继承。
2. `mutual_ratio=1.0` 是 bug 信号，不是图结构奇迹。
3. `reverse_score` 当前不可用。
4. `nodes_with_market_data=0` 是字段/匹配口径错误，不是市场数据真的缺失。
5. `industry_comparison:{}` 为空，说明行业、市值、流动性之外的增量还没有被证明。
6. 在静态、非中性化、非时序 lead-lag 的定义下，语义边分数不能直接解释市场行为共振。
7. Phase 2.1 必须重新做四 view、月度、matched random、行业残差、hub 稳健性。

---

## 5. 执行顺序总览

```text
T2.1.0  old result audit
T2.1.1  multi-view semantic audit
T2.1.2  multi-view k100 graph
T2.1.3  fixed edge candidates and rank bands
T2.1.4  multi-view industry baselines
T2.1.5  repaired size/liquidity profile
T2.1.6  domain and matched random baselines
T2.1.7  score exposure regression
T2.1.8  multi-view hub and bridge
T2.1.9  monthly market panel
T2.1.10 monthly pair corr and lead-lag
T2.1.11 multi-view summary
T2.1.12 project state update
```

一次只做一个任务。每完成一个任务，必须写 manifest、summary、log 和必要缓存。

---

## 6. 禁止事项

Phase 2.1 禁止：

- GNN；
- 回测；
- 图因子；
- Ollama 自动标注；
- 新 embedding；
- 生产化 API；
- 把 lead-lag 写成 alpha；
- 把静态 proxy 当市场共振；
- 四 view 缓存混用；
- failed task 继续生成 success report；
- summary 中裸写 `N/A`。

---

## 7. 最终验收

Phase 2.1 最终必须能回答：

1. 哪个 view 最能解释行业结构？
2. 哪个 view 最能解释跨行业桥？
3. 哪个 view 最适合题材/成交冲击？
4. 哪个 view 最适合产业链 lead-lag？
5. 规模、流动性中性化后语义边是否仍有增量？
6. cross L1 semantic 是否高于 cross L1 random？
7. 去 hub 后结论是否保留？
8. H5 是支持、拒绝、混合还是证据不足？
9. 是否允许进入 Phase 3？
