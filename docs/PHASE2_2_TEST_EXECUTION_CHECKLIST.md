# PHASE 2.2 测试执行与验收清单

## 0. 执行原则

Phase 2.2 的测试不是形式化单元测试，而是研究正确性防线。所有测试必须能阻止以下错误：

- 报告声称修复，但源码未修；
- 测试引用函数不存在；
- 旧 edge candidate 逻辑进入主路径；
- 市场行为结果由行业暴露、hub、near duplicate 驱动；
- 空 JSON/CSV 被当作成功；
- 图表不是从缓存结果绘制；
- 中文图表字体失败但未报错。

## 1. 基础代码测试

```bash
pytest -q tests/test_phase2_1_critical_fixes.py
pytest -q tests/test_phase2_2_code_consistency.py
pytest -q tests/test_phase2_2_edge_contract.py
```

必须新增：

### `test_phase2_2_code_consistency.py`

检查：

- `derive_mutual_edges_fast` 存在；
- `assign_rank_band_exclusive` 存在；
- `build_edge_candidates_fixed` 存在；
- `prepare_nodes_index` 存在；
- 旧 `score_dict = {i:` 不在主路径；
- 主脚本调用 fixed 函数。

### `test_phase2_2_edge_contract.py`

检查：

- edge row count；
- no self-node；
- no self-stock；
- no self-record；
- reverse_score non-null for mutual；
- rank band names；
- dtype；
- finite score；
- manifest 完整。

## 2. 市场面板测试

```bash
pytest -q tests/test_phase2_2_market_panel.py
```

检查：

- 月份数；
- 股票覆盖；
- 缺失比例；
- residual matrix shape；
- residual 每月均值接近 0；
- 行业残差每月每行业均值接近 0；
- full neutral residual 没有全 NaN；
- 不允许停牌缺失被硬填 0。

## 3. H5 指标测试

```bash
pytest -q tests/test_phase2_2_h5_metrics.py
```

检查：

- pair correlation 对称性；
- lead-lag 方向定义；
- common_months；
- min_common_months 过滤；
- bootstrap 输出；
- permutation p-value 区间；
- random repeats 数量；
- matched random pool shortage 记录。

## 4. 可视化测试

```bash
pytest -q tests/test_phase2_2_visualization_contract.py
```

检查：

- PNG 存在；
- 同名 CSV/JSON 存在；
- JSON caption 存在；
- 中文字体可用；
- 图表不从临时 DataFrame 绘制；
- plot manifest 记录源文件；
- 不生成空白图。

## 5. 脚本执行顺序

```bash
python scripts/21_phase2_2_code_consistency_audit.py
python scripts/22_phase2_2_freeze_fixed_edge_candidates.py
python scripts/23_phase2_2_build_market_monthly_panel.py
python scripts/24_phase2_2_build_residual_matrices.py
python scripts/25_phase2_2_generate_matched_random_edges.py
python scripts/26_phase2_2_compute_edge_market_metrics.py
python scripts/27_phase2_2_statistical_tests.py
python scripts/28_phase2_2_hub_duplicate_sensitivity.py
python scripts/29_phase2_2_visualization_dashboard.py
python scripts/30_phase2_2_final_report.py
```

每个脚本必须：

- 读取前一任务 manifest；
- 若 `safe_to_continue=false` 立即停止；
- 写本任务 manifest；
- 写 md/json/csv 中间结果；
- 不重复计算已经有且 fingerprint 匹配的缓存；
- 支持 `--force` 强制重算；
- 支持 `--view chain_text` 单 view 调试。

## 6. 最终验收

最终验收命令：

```bash
pytest -q
python scripts/30_phase2_2_final_report.py --validate-only
```

验收条件：

| 条件 | 要求 |
|---|---|
| 代码一致性 | 通过 |
| 边表契约 | 四 view 全通过 |
| 市场面板 | 覆盖 >= 5400 股票 |
| H5 指标 | 每 view 每 rank band 有输出 |
| 随机基准 | 每控制组 >= 200 repeats |
| 稳健性 | hub/duplicate removal 有输出 |
| 可视化 | 至少 30 张 PNG，全部有 CSV/JSON |
| 报告 | 无 N/A，无空 JSON，无 H5 冲突 |
| 决策 | 每个 view 有明确 H5 状态 |

## 7. 推荐新增脚本名

| 脚本 | 功能 |
|---|---|
| `21_phase2_2_code_consistency_audit.py` | 审计代码/测试/报告一致性 |
| `22_phase2_2_freeze_fixed_edge_candidates.py` | 生成修复版边表 |
| `23_phase2_2_build_market_monthly_panel.py` | 构造月度节点面板 |
| `24_phase2_2_build_residual_matrices.py` | 构造收益残差矩阵 |
| `25_phase2_2_generate_matched_random_edges.py` | 生成 matched random 控制边 |
| `26_phase2_2_compute_edge_market_metrics.py` | 边级市场指标计算 |
| `27_phase2_2_statistical_tests.py` | 显著性、effect size、FDR |
| `28_phase2_2_hub_duplicate_sensitivity.py` | hub/near duplicate 稳健性 |
| `29_phase2_2_visualization_dashboard.py` | 多图绘制 |
| `30_phase2_2_final_report.py` | 最终报告与校验 |

## 8. 失败报告模板

若失败，报告必须写：

```text
FAILED TASK: T2.2.x
blocking_errors:
  - ...
safe_to_continue: false
recommended_fix:
  - ...
invalidated_outputs:
  - ...
```

不能写“部分成功”后继续生成最终结论。
