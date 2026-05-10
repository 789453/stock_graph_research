# PHASE2_TASKS_03_05_BASELINES_AND_DOMAINS

## T2.3 Industry baseline

使用当前申万 L1/L2/L3 作为常态化行业标签。不是历史逐日行业变迁表。

基准：
- global random
- same L1 random
- same L2 random
- same L3 random
- cross L1 random

重点：语义边是否在 L3 内部仍有更细结构；跨 L1 高分边是否高于跨 L1 随机。

## T2.4 Size and liquidity domain

使用 2018-2026 的 daily/basic 数据构造市值桶和流动性桶。优先 DuckDB 或 Polars lazy scan，做列选择和日期谓词下推。

字段：
- total_mv
- circ_mv
- turnover_rate
- amount

输出 node_size_liquidity_profile。

## T2.5 Domain neighbor analysis

比较：
- top5/top10/top20/top50/top100
- rank 1-5/6-10/11-20/21-50/51-100
- same_l3 / cross_l1 / same_mv_bucket / same_liquidity_bucket
- middle 与 tail

输出 domain_neighbor_stats 和图表。
