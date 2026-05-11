# PHASE 2.2 文档索引：市场共振、时序收益分解与可视化实证研究

## 0. 文档定位

Phase 2.2 是在 Phase 2.1 之后继续推进的研究实证阶段。它不应急于进入 GNN、回测、图因子生产化或交易信号包装，而应先完成三件事：

1. 修复并核对 Phase 2.1 中“报告、测试、实际代码”之间仍可能存在的不一致；
2. 用月度/周度/日度市场行为面板重新检验 H5：语义边是否解释市场共振；
3. 将所有中间数据、统计指标、随机基准、图表、报告沉淀为可复查资产。

本系列文档可直接放入项目 `docs/` 目录，命名统一使用 `PHASE2_2_*`。建议保留 Phase 2 / Phase 2.1 文档作为历史参考，但在 `PROJECT_STATE.md` 中标记：Phase 2 旧结果只作为 historical reference，Phase 2.1 作为 graph repair baseline，Phase 2.2 作为 market behavior validation baseline。

## 1. 文档清单

| 文件 | 用途 |
|---|---|
| `PHASE2_2_RESEARCH_MASTER_SPEC.md` | Phase 2.2 总体研究规范、边界、验收标准 |
| `PHASE2_2_TASKS_00_02_CODE_REPAIR_AND_CACHE.md` | 代码/测试/报告一致性修复，缓存与输出目录契约 |
| `PHASE2_2_TASKS_03_05_H5_MARKET_PANEL_AND_RESIDUALS.md` | H5 市场共振、收益残差、时序面板构造 |
| `PHASE2_2_TASKS_06_08_METRICS_BASELINES_AND_TESTS.md` | 边级指标、随机控制组、显著性与稳健性检验 |
| `PHASE2_2_TASKS_09_11_VISUALIZATION_AND_REPORTING.md` | 多样化中文可视化、报告、仪表盘与图表清单 |
| `PHASE2_2_CACHE_SCHEMA_AND_OUTPUT_CONTRACTS.md` | CSV/JSON/YAML/Parquet/PNG 输出字段契约 |
| `PHASE2_2_TEST_EXECUTION_CHECKLIST.md` | 测试执行、失败阻断、复现检查清单 |

## 2. 执行顺序

Phase 2.2 必须按下面顺序执行：

1. **T2.2.0 代码一致性核对**  
   先检查 `graph_builder.py`、`phase2_graph_layers.py`、`tests/test_phase2_1_critical_fixes.py` 是否一致。若测试引用的函数在实际模块不存在，必须先修复，不允许继续生成新结果。

2. **T2.2.1 缓存与 manifest 修复**  
   所有结果必须带 view、view_key、input fingerprint、代码 commit、config hash、执行时间、脚本名、参数和输入输出路径。

3. **T2.2.2 多 view 边表再冻结**  
   四个 view 的 k100 边表必须统一字段与 dtype。旧 `core/strong/stable/context/extended` 命名不得进入 Phase 2.2 结果。

4. **T2.2.3 市场月度面板构造**  
   先构造节点级月度收益、残差收益、波动、成交额/换手 shock、极端收益标记。

5. **T2.2.4 边级市场共振指标**  
   在语义边和 matched random 边上计算 residual correlation、lead-lag、shock co-occurrence、tail co-movement。

6. **T2.2.5 H5 证伪与解释**  
   H5 只允许被标为 `SUPPORTED_WITH_CONTROLS`、`PARTIALLY_SUPPORTED`、`REJECTED_AFTER_MONTHLY_TEST`、`INCONCLUSIVE`。禁止使用 “alpha confirmed”。

7. **T2.2.6 多 view 对比与可视化**  
   绘制行业纯度、边分数、随机基准、残差相关、lead-lag、hub/bridge、view overlap、regime stability 等中文图。

8. **T2.2.7 最终报告与 CI 保护**  
   若任何关键字段为 N/A、空 JSON、测试失败、缓存 manifest 缺失，最终报告必须失败而不是继续生成。

## 3. Phase 2.2 的原则

- 偏向研究实证，不做过度工程化；
- 保持算法正确、口径严格、缓存清楚；
- 对大矩阵使用向量化、矩阵乘法、分块计算、Parquet projection pushdown；
- 多保留中间结果，尤其是 CSV/JSON/YAML/Parquet；
- 任何图表都必须能追溯到源 CSV/JSON；
- 中文图表必须字体正确、标题清楚、坐标轴可读；
- 不把静态语义相似度直接解释为收益预测；
- 先验证市场共振，再考虑策略或图模型。
