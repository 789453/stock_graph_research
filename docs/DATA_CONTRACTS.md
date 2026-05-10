# Data Contracts

## 1. 第一轮唯一允许使用的真实语义输入

### 语义向量

- 研究 view：`application_scenarios_json`
- Windows 原始描述路径：  
  `\\wsl.localhost\Ubuntu\home\purple_born\QuantSum\stock_graph_research\a_share_semantic_dataset\npy\application_scenarios_json\application_scenarios_json-all.npy`
- Ubuntu / WSL 侧建议实际路径：  
  `/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.npy`

### 必须同时读取的配套文件

同一数据集根目录下必须读取：

- `npy/application_scenarios_json/application_scenarios_json-all.meta.json`
- `parquet/records-all.parquet`

### 语义数据已知契约

- 总记录数：`5502`
- 股票数：`5502`
- embedding 维度：`1024`
- NPY dtype：`float32`
- 通过 `record_id` 与 `view-all.meta.json` 中的 `row_ids` 对齐
- `records.jsonl` 中的旧 `vector_paths` 可能过期，不能作为合并后向量读取依据
- JSON 类 view 在 Parquet 中是字符串；但第一轮近邻构图直接使用已经存在的向量矩阵，不重新编码文本

### 第一轮禁止的数据替代

- 禁止 mock vector
- 禁止 sample vector 代替全量真实向量
- 禁止 TF-IDF 代替真实 embedding
- 禁止 PCA 降维向量代替真实 embedding 构图
- 禁止 silently fallback

## 2. 行情与基本面数据

### 数据源位置

用户当前真实数据位于 Windows D 盘。  
在 Ubuntu / WSL 中通常按 `/mnt/d/...` 访问；如果本机挂载方式不同，以实际可读路径为准。

- SQLite 元数据：  
  `D:\Trading\data_ever_26_3_14\data\meta\control.sqlite3`
- DuckDB 仓库：  
  `D:\Trading\data_ever_26_3_14\data\meta\warehouse.duckdb`
- 申万行业成分：  
  `D:\Trading\data_ever_26_3_14\data\silver\stock_sw_member.parquet`
- 股票每日指标：  
  `D:\Trading\data_ever_26_3_14\data\silver\stock_daily_basic.parquet`
- 股票日线行情：  
  `D:\Trading\data_ever_26_3_14\data\silver\stock_daily.parquet`

### 第一轮对行情数据的使用边界

第一轮只做**节点覆盖率普查**，不做因子研究，不做回测，不做标签训练。

允许产出：

- 每只股票在 `2010-01-01` 至 `2026-04-30` 请求区间内的：
  - `daily` 行数
  - `daily_basic` 行数
  - 最早日期
  - 最晚日期
  - 是否缺失严重
- 全局覆盖率摘要
- 实际可用的最大日期

禁止在第一轮产出：

- 动量因子
- 反转因子
- 基本面因子
- 行业中性化
- 图平滑后的收益预测
- 回测结论

### 时间契约

- 研究请求窗口：`2010-01-01` 到 `2026-04-30`
- 实际数据结束日必须从真实文件中读取并写入 manifest
- 若真实文件截止日早于 `2026-04-30`，以真实最大日期为准，不补造数据

## 3. 申万行业成分数据

### 已知身份

- 数据集：`stock_sw_member`
- 接口：`index_member_all`
- 文档说明：当前最新成分
- 关键字段：`l1_code/l1_name/l2_code/l2_name/l3_code/l3_name/ts_code/name/in_date`

### 第一轮允许用途

- 当前截面的标签解释
- 当前行业标签覆盖率
- 语义近邻图的行业一致性诊断
- 随机基线对照

### 第一轮禁止用途

- 不能当作 2010—2026 的历史行业标签
- 不能用来构造历史图边
- 不能用来做历史回测时的行业真值
- 不能据此声称某年某日股票属于某行业

## 4. 节点身份契约

### 节点主键

- `record_id`：语义记录唯一 ID
- `node_id`：研究管线内部稳定整数 ID，必须由 `row_ids` 顺序生成
- `stock_code`：证券代码，用于后续与行情和行业表连接

### 节点表最低字段

| 字段 | 含义 |
|---|---|
| `node_id` | 0 到 N-1 的整数 |
| `record_id` | 语义记录唯一 ID |
| `stock_code` | 股票代码 |
| `stock_name` | 股票简称 |
| `asof_date` | 语义快照日期 |
| `semantic_view` | 固定为 `application_scenarios_json` |

## 5. 数据错误时的处理

以下任何一项发生时，必须直接失败：

- NPY 文件不存在
- meta 文件不存在
- records parquet 不存在
- NPY 维度不是 2 维
- NPY 维度不是 `(*, 1024)`
- 行数不是 meta `row_ids` 数量
- `row_ids` 不能与 `records-all.parquet` 中 `record_id` 完整对齐
- 向量存在 NaN / Inf
- 读取到的 view 不是 `application_scenarios_json`
- 代码试图启用 fallback 数据

失败是正确行为。  
悄悄换一套数据继续跑，才是错误。
