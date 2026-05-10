# PHASE2_AI_WORKING_PROTOCOL_UPDATE

## 1. Phase 2 禁止事项

- 禁止 GNN。
- 禁止回测。
- 禁止图因子。
- 禁止 Ollama 自动标注。
- 禁止新 embedding。
- 禁止 mock 替代真实数据。
- 禁止为了跑通而读取全量大表再过滤。
- 禁止把当前申万标签写成历史行业真值。
- 禁止把描述性 lead-lag 叫 alpha。

## 2. AI 执行顺序

1. 先读 PROJECT_STATE。
2. 再读 Phase 2 主文档。
3. 再读 cache contracts。
4. 一次只做一个任务。
5. 做完任务必须写 manifest、summary、log。
6. 如果测试失败，停止，不进入下一任务。
7. 图表只读缓存。
8. 报告只读缓存。

## 3. 研究语言约束

正确说法：
- 描述性关联
- 市场行为共振
- 语义边解释力
- 基准对比
- 证伪结果
- 候选现象

错误说法：
- alpha
- 策略
- 回测
- 因子有效
- 可交易信号
