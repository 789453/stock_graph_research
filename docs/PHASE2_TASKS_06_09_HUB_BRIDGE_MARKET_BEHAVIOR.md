# PHASE2_TASKS_06_09_HUB_BRIDGE_MARKET_BEHAVIOR

## T2.6 Hub and bridge

研究 hub 是否是产业中心、平台、题材中心、文本泛化或异常候选。输出 top hubs、hub entropy、cross-industry bridge matrix。

不使用 Ollama，不做自动标注，只做规则候选与样例导出。

## T2.7 Market panel 2018-2026

构建节点级市场行为面板，只读必要列和日期范围。输出 ret、vol、amount shock、turnover shock、market/L1/L3 residual。

## T2.8 Pairwise market behavior association

对边层和基准样本计算：
- return correlation
- residual return correlation
- volatility co-movement
- amount shock co-occurrence
- extreme up/down co-occurrence

不叫因子，不做回测，不做组合收益。

## T2.9 Phase 2 summary

汇总所有证据，判断：
- 哪些边层保留；
- 哪些边层丢弃；
- hub 是否可控；
- 跨行业桥是否值得继续；
- 是否允许 Phase 3 进入简单图信号研究。
