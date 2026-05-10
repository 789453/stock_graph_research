# PHASE2_1_AI_WORKING_PROTOCOL_UPDATE.md

## 1. 文档目的

本文件定义 Phase 2.1 中 Trae、交互 IDE AI 或其他代码助手的工作规程。Phase 2.1 是研究修复与证据重建阶段，不是“继续加功能”的阶段。AI 的首要责任不是写更多代码，而是保证研究口径正确、缓存清楚、任务不漂移、失败不伪装成功。

---

## 2. AI 每次开始前必须确认

每次新会话必须先确认：

- 当前阶段是 Phase 2.1，不是 Phase 2；
- 主研究 view 是 `main_business_detail`、`theme_text`、`chain_text`、`full_text`；
- `application_scenarios_json` 只作为历史参考；
- 禁止 GNN、回测、图因子、Ollama 自动标注；
- 当前要执行的是哪一个任务；
- 上一个任务是否成功；
- 该任务依赖的 cache 是否存在；
- 是否存在 invalidated old result。

---

## 3. 工作顺序

AI 必须按以下顺序执行：

1. 读取 `PROJECT_STATE.md`。
2. 读取 `PHASE2_1_COMPLETE_CONTINUOUS_SPEC.md`。
3. 读取当前任务对应的任务文档。
4. 读取 `PHASE2_1_CACHE_CONTRACTS.md`。
5. 检查输入文件和缓存。
6. 执行任务。
7. 写 manifest。
8. 写 summary json。
9. 写 summary md。
10. 写 log。
11. 更新 PROJECT_STATE 或输出建议更新片段。

不得跳过 manifest，不得先生成报告再补数据。

---

## 4. 失败处理协议

如果出现以下情况，任务必须失败：

- `mutual_ratio == 1.0`；
- `reverse_score` 全 0 或几乎全 0；
- `matched_market_nodes < 5400`；
- `industry_comparison` 为空；
- 四 view 缓存路径重叠；
- summary 中出现关键字段 `N/A`；
- 月度矩阵节点顺序与 node_id 不一致；
- lead-lag 命名不清；
- 文件读取使用全量 parquet 后再过滤，且数据量巨大；
- view 之间混用了旧 cache key。

失败时必须写：

```json
{
  "status": "failed",
  "error_type": "...",
  "error_message": "...",
  "safe_to_continue": false,
  "required_fix": "..."
}
```

不允许用 warning 替代失败。

---

## 5. 禁止任务漂移

Phase 2.1 中 AI 不得主动引入：

- GNN；
- GraphSAGE；
- PyG；
- 回测框架；
- 多因子 IC；
- 组合净值；
- 自动调参；
- Ollama 标注；
- 新 embedding；
- 复杂生产化模块；
- API 服务；
- 数据库迁移；
- 前端 dashboard。

如需建议下一阶段，也只能写入 `future_work`，不得在当前任务实现。

---

## 6. 命名纪律

### 6.1 rank band

必须使用：

- `rank_001_005`
- `rank_006_010`
- `rank_011_020`
- `rank_021_050`
- `rank_051_100`

### 6.2 cumulative topK

必须使用：

- `top_001_005`
- `top_001_010`
- `top_001_020`
- `top_001_050`
- `top_001_100`

不能写模糊的 `top10_mean`。如果是第 6—10 名，必须写 `rank_006_010`。

### 6.3 lead-lag

必须使用：

- `src_leads_dst_1m`
- `dst_leads_src_1m`
- `src_leads_dst_2m`
- `dst_leads_src_2m`
- `src_leads_dst_3m`
- `dst_leads_src_3m`

不能写 predictor、alpha、signal。

---

## 7. view 隔离纪律

任何输出路径都必须包含 view name 或 multi_view：

正确：

```text
cache/semantic_graph/views/chain_text/{view_key}/edge_layers/edge_candidates_k100.parquet
outputs/reports/phase2_1/theme_text/VIEW_RESEARCH_REPORT.md
outputs/plots/phase2_1/multi_view/view_comparison_dashboard.png
```

错误：

```text
cache/semantic_graph/phase2/edge_candidates_k100.parquet
outputs/reports/phase2_1/VIEW_RESEARCH_REPORT.md
```

旧 `2eebde04e582` 不得作为四 view 的 cache key。

---

## 8. 日志要求

每个任务日志至少记录：

- task id；
- task name；
- view name；
- view key；
- input files；
- output files；
- row counts；
- elapsed time；
- warnings；
- failure reason；
- next recommended task。

日志粒度保持任务级，不要每只股票打印一行。

---

## 9. 报告语言纪律

正确写法：

- “描述性支持”
- “月度残差相关高于匹配随机基准”
- “cross L1 semantic 高于 cross L1 random”
- “该结果不等价于回测”
- “H5 在该子问题上得到支持/证据不足/被拒绝”

错误写法：

- “产生 alpha”
- “策略有效”
- “可以交易”
- “图因子有效”
- “回测结果”
- “预测收益”

---

## 10. AI 完成任务后的自检

提交前必须回答：

1. 是否使用了正确 view？
2. 是否写入 view 隔离缓存？
3. 是否写 manifest？
4. 是否写 summary json？
5. 是否写 summary md？
6. 是否写 log？
7. 是否存在裸 `N/A`？
8. 是否有关键字段缺失？
9. 是否有 failed but success 的伪成功？
10. 是否需要更新 PROJECT_STATE？
