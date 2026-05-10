# PHASE2_1_PROJECT_STATE_UPDATE_TEMPLATE.md

## 1. 当前阶段

```text
当前阶段：Phase 2.1 - 多语义 view 修复、稳健基准与月度时序关联重验
当前目标：修复 Phase 2 关键 bug，并使用 main_business_detail/theme_text/chain_text/full_text 四个 view 重建语义图金融解释证据链。
```

---

## 2. 旧 Phase 2 结果状态

| 项目 | 状态 | 说明 |
|---|---|---|
| Phase 1 audit | HISTORICAL_REFERENCE | 仅代表 application_scenarios_json |
| k20 graph stats | PARTIALLY_VALID | 可参考早期结构 |
| k100 edge candidates | PARTIALLY_VALID | 边数可参考，mutual/reverse_score 不可用 |
| mutual_ratio | INVALIDATED_BY_BUG | 当前 1.0 不可信 |
| reverse_score | INVALIDATED_BY_BUG | 字典 key 错误 |
| size_liquidity_summary | INVALIDATED_BY_BUG | nodes_with_market_data=0 |
| industry_baseline | PARTIALLY_VALID | 单 view 结构参考，四 view 需重算 |
| domain_baseline | REQUIRES_RECOMPUTE | 依赖 size/liquidity 修复 |
| hub_bridge | REQUIRES_RECOMPUTE | 依赖 mutual 修复 |
| market_association | STATIC_PROXY_ONLY | 不是时序共振 |
| H5 | NOT_RETESTED_MONTHLY | 等待月度重验 |

---

## 3. Phase 2.1 研究对象

| view | 用途 |
|---|---|
| main_business_detail | 主营业务、同行 peer、可比公司 |
| theme_text | 主题、题材、叙事、成交冲击 |
| chain_text | 产业链、上下游、跨行业 lead-lag |
| full_text | 综合语义、multi-view baseline、hub 风险 |

---

## 4. 明确禁止

- GNN；
- 回测；
- 图因子；
- Ollama 自动标注；
- 新 embedding；
- application_scenarios_json 作为主研究对象；
- 把 lead-lag 写成 alpha；
- 把静态 proxy 当市场共振；
- failed task 伪成功。

---

## 5. 任务状态表

| 任务 | 状态 | 输出 |
|---|---|---|
| T2.1.0 old result audit | TODO | `PHASE2_OLD_RESULTS_AUDIT.md` |
| T2.1.1 multi-view audit | TODO | 四 view audit |
| T2.1.2 multi-view k100 graph | TODO | 四 view graph |
| T2.1.3 fixed edge candidates | TODO | edge_candidates_k100 |
| T2.1.4 industry comparison | TODO | industry_by_rank |
| T2.1.5 size/liquidity repair | TODO | node_size_liquidity_profile |
| T2.1.6 domain baselines | TODO | domain_baseline_comparison |
| T2.1.7 score regression | TODO | score_size_liquidity_regression |
| T2.1.8 hub/bridge | TODO | hub_bridge reports |
| T2.1.9 monthly panel | TODO | monthly matrices |
| T2.1.10 monthly corr lead-lag | TODO | monthly pair corr |
| T2.1.11 multi-view summary | TODO | MULTI_VIEW_RESEARCH_SUMMARY |
| T2.1.12 project state update | TODO | PROJECT_STATE |

---

## 6. 测试状态

| 测试 | 状态 |
|---|---|
| mutual logic test | TODO |
| reverse_score test | TODO |
| rank band naming test | TODO |
| market profile alignment test | TODO |
| view cache isolation test | TODO |
| monthly pair corr test | TODO |
| report schema test | TODO |

---

## 7. H5 状态

当前：

```text
H5 = REJECTED_STATIC_PROXY / NOT_RETESTED_MONTHLY
```

允许状态：

- REJECTED_STATIC_PROXY
- NOT_TESTED
- INSUFFICIENT_DATA
- SUPPORTED_MONTHLY_RESIDUAL
- SUPPORTED_MONTHLY_LEAD_LAG
- SUPPORTED_SHOCK_COOCCURRENCE
- MIXED
- INVALIDATED_BY_BUG

---

## 8. 进入 Phase 3 条件

只有当至少一个 view 在 matched random 后仍显示月度残差相关、lead-lag 或 shock co-occurrence 增量，并且去 hub 后仍稳健，才允许讨论 Phase 3。

否则 Phase 3 状态应保持：

```text
PHASE3_ALLOWED = false
```
