# Semantic Graph Research Docs — Reading Order

这组文档不是为了把项目先做成“系统”，而是为了让第一轮研究能够稳定、透明、可复现地落地。

## 推荐阅读顺序

1. `README_FOR_TRAE.md`  
   给 Trae / 交互 IDE 的入口文件。每次新窗口先读它。

2. `RESEARCH_CONSTITUTION.md`  
   研究优先的总原则、禁止事项、边界。

3. `DATA_CONTRACTS.md`  
   真实数据源、字段身份、时间边界、允许与禁止的用法。

4. `PHASE1_SEMANTIC_GRAPH_ENGINEERING_SPEC.md`  
   第一轮主工程文档。真正要执行的任务、缓存、测试、图表、验收标准都在这里。

5. `PROJECT_STATE_TEMPLATE.md`  
   每次完成一个任务后要更新的状态文件模板。

6. `TASK_CARD_TEMPLATE.md`  
   将大任务切成单张可执行卡片时使用。

7. `AI_WORKING_PROTOCOL.md`  
   约束 AI 不漂移、不自作主张扩范围的工作规程。

## 这组文档解决什么问题

- 防止“真实 1024 维向量”被 mock、TF-IDF、PCA 替代。
- 防止第一轮就把图融合、聚类、因子、回测、生产化全部混在一起。
- 防止一个任务对话拖长以后，Trae 忘记项目当前到底在验证什么。
- 强制中间结果落盘，后续绘图必须从缓存读取，阻断上下文污染。
- 让每一轮研究都有明确的研究问题、失败判据和下一步入口。

## 第一轮的唯一研究目标

> 判断 `application_scenarios_json` 的真实语义向量，是否能够形成一张可解释、可复现、非退化的 A 股语义近邻图。

第一轮不是为了证明它能赚钱，也不是为了证明某个复杂图模型有效。  
第一轮先把“图有没有研究价值”这件事做对。
