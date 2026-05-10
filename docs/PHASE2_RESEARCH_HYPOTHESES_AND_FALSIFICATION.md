# PHASE2_RESEARCH_HYPOTHESES_AND_FALSIFICATION

## 1. 文档目的

Phase 2 的核心不是“继续写更多代码”，而是把语义图的金融价值拆成可以被证伪的研究假设。每个假设都必须对应明确数据、明确基准、明确输出文件、明确失败条件。

## 2. 研究假设总表

| 编号 | 假设 | 需要的数据 | 最小证据 | 证伪条件 |
|---|---|---|---|---|
| H1 | 语义图不只是行业分类复刻 | edges, SW L1/L2/L3, 市值/流动性桶 | same_l3/random/size baseline 对比 | 控制 L3、市值、流动性后完全无增量 |
| H2 | 不同 rank band 对应不同金融含义 | k50/k100 edges, score, rank | top5 强行业纯度；middle 跨域更强 | rank band 结构完全无差异 |
| H3 | hub 有类型差异，不能简单 smoothing | in-degree, entropy, mutual ratio | hub 可分为产业/平台/题材/泛化 | hub 多为不可解释泛化噪声 |
| H4 | 跨行业桥可能捕捉产业链或题材扩散 | cross_l1/cross_l3 edges | 高分跨域边高于随机跨域基准 | 跨域边与随机无区别 |
| H5 | 语义边能解释市场行为共振 | 2018-2026 returns/vol/amount | residual corr 或 shock co-occurrence 高于基准 | 仅原始收益有效，残差后消失 |
| H6 | 中等边可能比最强边更适合题材/风险传染 | rank 21-100 | 波动/成交/极端共现优于随机 | top100 只是噪声扩展 |

## 3. 假设解释

### H1：语义图不只是行业分类复刻

强行业一致性不是坏事，但不是终点。真正的问题是语义边在三级行业内部是否比随机同行更细，跨行业高分边是否比随机跨行业边更有市场行为联系。如果语义图只在全局随机基准上显得有效，而在 same_l3 + market_cap bucket 基准下消失，那么它的金融价值会被限制在“行业分类连续化”层面。

### H2：不同 rank band 有不同含义

固定 k=20 只是一张基础图。Phase 2 应该比较 top5、top10、top20、top50、top100，以及 middle 与 tail。top5 可能高度同业，top21—50 可能更像主题上下文，top51—100 可能是弱传染候选。若所有 rank band 表现一致，则说明 rank 分层没有意义。

### H3：hub 是重点风险

hub 能让 mutual component 很大，也可能破坏局部解释。如果高入度节点本身是产业中心，则有研究价值；如果只是文本模板泛化，则会污染边层。Phase 2 要将 hub 降权/剔除后的结果与原始结果比较，而不是直接 smoothing。

### H4：跨行业桥是增量价值核心

同三级行业边很容易被现有行业分类解释，跨行业高分边才可能体现语义图区别于申万分类的增量。例如同一应用场景、同一产业链、同一主题投资线索可能跨越多个 L1/L2。Phase 2 需要输出跨行业桥矩阵和典型样例，但不做 Ollama 自动标注。

### H5：市场行为关联是金融价值证据

Phase 2 不做回测，也不做因子。但若语义边完全不能解释收益、波动、成交共振，那么后续图模型没有基础。市场行为验证只做描述性统计：pair correlation、residual correlation、volatility co-movement、amount shock co-occurrence、extreme return co-occurrence。

### H6：中等边与题材/风险传染

题材传染未必发生在 top5 强业务边之间。Phase 2 应保留 rank 21—100 的候选关系，但必须用基准检验，不可直接当作有效边。若中等边在成交额冲击、波动共振、极端上涨/下跌共现上强于随机跨域边，则它们值得进入 Phase 3 的观察列表。

## 4. 不允许的结论

Phase 2 不能写：

- 这个图因子有效；
- 这个图可以回测；
- 这个图能赚钱；
- GNN 应该上线；
- smoothing 必然有用。

Phase 2 只能写：

- 某类边在某个基准下有/无描述性增量；
- 某类边有/无金融解释价值；
- 某类边值得/不值得进入 Phase 3。
