# PHASE2_1_RESEARCH_HYPOTHESES_AND_FALSIFICATION.md

## 1. 文档目的

本文件定义 Phase 2.1 的研究假设、证据要求和证伪标准。Phase 2.1 不追求“证明图能赚钱”，而是检验四个语义 view 是否在行业、市值、流动性之外，对月度市场行为、风险传导和 lead-lag 存在描述性解释力。

---

## 2. 总假设

### H0：旧 Phase 2 静态 proxy 不足以证明市场行为共振

当前结论：

> 在当前静态、非中性化、非时序 lead-lag 的定义下，语义边分数不能直接解释市场行为共振。

这不是否定语义图，而是要求 Phase 2.1 用月度时序和匹配基准重验。

证据要求：

- 旧静态 proxy 不再作为 H5 支持证据；
- H5 状态改为 `REJECTED_STATIC_PROXY / NOT_RETESTED_MONTHLY`；
- 所有报告删除 H5 support/rejected 冲突。

---

## 3. H1：四个 view 捕捉不同经济关系

### H1-main

`main_business_detail` 捕捉主营业务和同行 peer。

支持证据：

- same L3 lift 在四 view 中较高；
- same L3 + size/liquidity matched random 后仍有行业内残差结构；
- core rank band 比 context/extended 更同业。

证伪条件：

- 控制 L3、size、liquidity 后完全无增量；
- score 大部分由市值、流动性解释；
- 行业内随机基准与语义边无差异。

### H1-theme

`theme_text` 捕捉题材、叙事和市场关注扩散。

支持证据：

- cross L1 边比例较高；
- amount shock co-movement 高于 matched random；
- extreme up co-occurrence 高于 random；
- rank_021_050 或 rank_051_100 有题材扩散特征。

证伪条件：

- cross L1 semantic 与 cross L1 random 无差异；
- 成交冲击和极端上涨共现不高于随机；
- 结果完全由 hub 驱动。

### H1-chain

`chain_text` 捕捉产业链、上下游和跨行业传导。

支持证据：

- cross L1 lead-lag 高于 cross L1 random；
- 去 hub 后仍成立；
- chain_text bridge edges 有明确行业矩阵结构；
- 下跌共振或波动共振高于随机基准。

证伪条件：

- cross L1 边只是在数量上多，但市场行为不高于 random；
- lead-lag 行业残差后消失；
- 去 hub 后完全消失。

### H1-full

`full_text` 捕捉综合信息，但可能混入 hub 和近重复。

支持证据：

- 多项指标稳健；
- 去 hub 后仍保留；
- near duplicate 风险可控；
- 与其他 view 有合理 overlap。

证伪条件：

- near duplicate 过多；
- hub 过度集中；
- 去 hub 后结果消失；
- 仅 full 强但无法解释边类型。

---

## 4. H2：语义边不只是行业分类复刻

支持证据：

- same L3 semantic 高于 same L3 random；
- same L3 + size/liquidity matched random 后仍有增量；
- cross L1 semantic 高于 cross L1 random；
- 行业残差月度相关仍有差异。

证伪条件：

- 所有结果在行业内随机基准下消失；
- 所有结果在 size/liquidity matched 后消失；
- cross industry 结果不高于 cross industry random。

---

## 5. H3：规模和流动性不能完全解释语义分数

支持证据：

- score 对 log market cap、turnover、amount 回归中，行业和 size/liquidity 控制后仍保留 view-specific 结构；
- same_size_bucket_ratio_by_rank 不完全解释 score；
- same_liquidity_bucket_ratio_by_rank 不完全解释 score。

证伪条件：

- score 主要由规模差异和流动性差异解释；
- matched random 后语义边无增量；
- 高 score 边集中在同规模、同流动性但无业务解释。

---

## 6. H4：hub 既可能有价值，也可能污染图

支持证据：

- hub 可分为产业中心、主题中心、产业链枢纽、综合平台；
- 去 top 1% hub 后主要结论仍存在；
- hub 样例可解释；
- hub entropy 与市场行为关系有结构。

证伪条件：

- 去 hub 后所有结果消失；
- top hub 大多是泛化文本或近重复；
- hub 的行业熵极高且边权不稳；
- hub 驱动所有跨行业结果。

---

## 7. H5-Monthly：月度市场行为增量

正式定义：

> 在行业、市值、流动性中性化与匹配随机基准之后，至少一个语义 view 的某类边在月度收益残差、波动、成交冲击或 lead-lag 上显著高于对应基准。

支持类型：

- `SUPPORTED_MONTHLY_RESIDUAL`
- `SUPPORTED_MONTHLY_LEAD_LAG`
- `SUPPORTED_SHOCK_COOCCURRENCE`
- `MIXED`

证伪条件：

- 所有 view 在 matched random 后无差异；
- 月度残差相关不高于随机；
- lead-lag 仅未中性化有效；
- 成交冲击共现不高于随机；
- 去 hub 后消失。

---

## 8. H6：多 view 共识边更可靠

支持证据：

- multi-view consensus edge 的行业纯度和市场行为稳定性高于 single-view edge；
- consensus edge 去 hub 后仍稳定；
- consensus edge 的 near duplicate 风险可控。

证伪条件：

- consensus edge 只是 full_text hub；
- multi-view overlap 不高于随机；
- consensus edge 市场行为不高于 single-view。

---

## 9. 决策矩阵

| H 状态 | 下一步 |
|---|---|
| H1 支持，H5 不支持 | 语义图用于经济结构，不进入交易信号 |
| H1/H2 支持，H5 mixed | 保留有效 view，继续事件窗口 |
| H5 支持且去 hub 稳健 | 允许讨论 Phase 3 简单观察型信号 |
| H3 被证伪 | 必须强化 size/liquidity matched baseline |
| H4 被证伪 | 禁止 smoothing |
| 全部不支持 | 回到语义数据质量和边样例审计 |
