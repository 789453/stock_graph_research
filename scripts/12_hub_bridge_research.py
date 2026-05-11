#!/usr/bin/env python3
"""
T2.6: Hub 与跨行业桥研究 (Refactored)
识别 hub 节点和跨行业桥边，分析其统计特征，并进行节点分类。
严格遵循 Node Order Safety 和 Phase 2.3 规范。
"""
import sys
import json
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from scipy.stats import entropy

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.phase2_graph_layers import prepare_nodes_index

def calculate_entropy(labels):
    if len(labels) == 0:
        return 0.0
    counts = pd.Series(labels).value_counts()
    return entropy(counts)

def main():
    parser = argparse.ArgumentParser(description="T2.6: Hub 与跨行业桥研究")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.6: Hub 与跨行业桥研究 (Refactored)")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path("cache") / "semantic_graph"
    if args.cache_key:
        cache_dir = cache_root / args.cache_key
    else:
        # 尝试从 config 中获取
        cache_dir_str = config.get("paths", {}).get("semantic_graph_cache")
        if cache_dir_str:
            cache_dir = Path(cache_dir_str)
        else:
            cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
            if not cache_dirs:
                print("[FAIL] 未找到缓存")
                sys.exit(1)
            cache_dir = sorted(cache_dirs)[-1]

    phase2_cache = cache_dir / "phase2"
    hub_bridge_cache = phase2_cache / "hub_bridge"
    hub_bridge_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = phase2_cache / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    # 1. 加载数据
    nodes_path = cache_dir / "nodes.parquet"
    if not nodes_path.exists():
        print(f"[FAIL] {nodes_path} 不存在")
        sys.exit(1)
        
    nodes = pd.read_parquet(nodes_path)
    nodes = prepare_nodes_index(nodes, len(nodes))
    
    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print(f"[FAIL] {edges_path} 不存在")
        sys.exit(1)
    edges = pd.read_parquet(edges_path)
    
    # 加载行业数据
    sw_member_path = Path(config["market"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        nodes = nodes.merge(sw_member[["ts_code", "l1_name", "l2_name", "l3_name"]], 
                          left_on="stock_code", right_on="ts_code", how="left")
    else:
        print("[WARN] 申万行业数据缺失")
        for col in ["l1_name", "l2_name", "l3_name"]:
            nodes[col] = "UNKNOWN"

    print(f"[OK] 加载 {len(nodes)} 节点和 {len(edges)} 边")

    # 2. 计算节点度指标
    print("\n[Step 1] 计算节点度与分布指标...")
    in_stats = edges.groupby("dst_node_id").agg(
        in_degree=("src_node_id", "count"),
        mean_in_score=("score", "mean")
    ).reindex(range(len(nodes)), fill_value=0)
    
    out_stats = edges.groupby("src_node_id").agg(
        out_degree=("dst_node_id", "count"),
        mean_out_score=("score", "mean")
    ).reindex(range(len(nodes)), fill_value=0)
    
    mutual_stats = edges[edges["is_mutual"]].groupby("src_node_id").agg(
        mutual_degree=("dst_node_id", "count")
    ).reindex(range(len(nodes)), fill_value=0)

    node_metrics = pd.DataFrame({
        "node_id": range(len(nodes)),
        "in_degree": in_stats["in_degree"].values,
        "out_degree": out_stats["out_degree"].values,
        "mutual_degree": mutual_stats["mutual_degree"].values,
        "mean_in_score": in_stats["mean_in_score"].values.astype(float),
        "mean_out_score": out_stats["mean_out_score"].values.astype(float),
    })

    # 3. 计算邻居熵
    print("[Step 2] 计算邻居行业熵...")
    # 计算每个源节点发出的邻居行业分布 (out-neighbor entropy)
    edges_with_ind_dst = edges.merge(nodes[["node_id", "l1_name", "l3_name"]], left_on="dst_node_id", right_on="node_id", how="left")
    
    # 计算每个源节点的指向行业分布 (in-neighbor entropy)
    edges_with_ind_src = edges.merge(nodes[["node_id", "l1_name", "l3_name"]], left_on="src_node_id", right_on="node_id", how="left")
    
    def get_entropy_stats(df, id_col, label_col):
        return df.groupby(id_col)[label_col].apply(calculate_entropy)

    node_metrics["neighbor_l1_entropy"] = get_entropy_stats(edges_with_ind_dst, "src_node_id", "l1_name").reindex(range(len(nodes)), fill_value=0.0).values
    node_metrics["neighbor_l3_entropy"] = get_entropy_stats(edges_with_ind_dst, "src_node_id", "l3_name").reindex(range(len(nodes)), fill_value=0.0).values
    
    # in_neighbor_l1_entropy: 谁在指向我？这些指向者的行业分布
    node_metrics["in_neighbor_l1_entropy"] = get_entropy_stats(edges_with_ind_src, "dst_node_id", "l1_name").reindex(range(len(nodes)), fill_value=0.0).values

    # 4. 统计重复文本/高分边
    print("[Step 3] 统计高分重复描述嫌疑...")
    high_score_counts = edges[edges["score"] >= 0.98].groupby("dst_node_id").size().reindex(range(len(nodes)), fill_value=0)
    node_metrics["duplicate_score_gt_098_count"] = high_score_counts.values

    # 5. 识别 Hub 类型
    print("[Step 4] 识别 Hub 类型分类...")
    
    # 计算行业内纯度 (out-degree purity)
    edges_merged = edges.merge(nodes[["node_id", "l1_name"]], left_on="src_node_id", right_on="node_id", how="left") \
                        .merge(nodes[["node_id", "l1_name"]], left_on="dst_node_id", right_on="node_id", how="left", suffixes=("_src", "_dst"))
    edges_merged["same_l1"] = (edges_merged["l1_name_src"] == edges_merged["l1_name_dst"]) & edges_merged["l1_name_src"].notna()
    same_l1_ratio = edges_merged.groupby("src_node_id")["same_l1"].mean().reindex(range(len(nodes)), fill_value=0.0)
    node_metrics["same_l1_ratio"] = same_l1_ratio.values

    def classify_hub(row):
        if row["in_degree"] < 20: # 门槛：入度至少20
            return "not_hub"
        if row["duplicate_score_gt_098_count"] > 10:
            return "template_duplicate_suspect"
        if row["in_neighbor_l1_entropy"] < 0.5 and row["same_l1_ratio"] > 0.7:
            return "industry_center"
        if row["in_neighbor_l1_entropy"] > 1.5:
            return "cross_industry_platform"
        return "mixed_hub"

    node_metrics["hub_type"] = node_metrics.apply(classify_hub, axis=1)

    # 6. 桥接节点 (Bridge Nodes)
    print("[Step 5] 识别跨行业桥节点...")
    cross_industry_edges = edges_merged[~edges_merged["same_l1"]].copy()
    bridge_stats = cross_industry_edges.groupby("src_node_id").agg(
        cross_industry_count=("dst_node_id", "count"),
        mean_cross_score=("score", "mean")
    ).reindex(range(len(nodes)), fill_value=0)
    
    node_metrics["cross_industry_count"] = bridge_stats["cross_industry_count"].values
    node_metrics["mean_cross_score"] = bridge_stats["mean_cross_score"].values.astype(float)
    
    # 桥接得分 (Bridge Score) = 跨行业比例 * 平均分
    node_metrics["bridge_score"] = (node_metrics["cross_industry_count"] / node_metrics["out_degree"].replace(0, 1)) * node_metrics["mean_cross_score"]

    # 7. 保存结果
    print("\n[Step 6] 保存研究产物...")
    final_nodes = nodes.merge(node_metrics, on="node_id")
    final_nodes.to_parquet(hub_bridge_cache / "node_hub_bridge_labels.parquet", index=False)
    final_nodes.to_csv(hub_bridge_cache / "node_hub_bridge_labels.csv", index=False)
    
    hubs = final_nodes[final_nodes["hub_type"] != "not_hub"].sort_values("in_degree", ascending=False)
    hubs.to_csv(hub_bridge_cache / "hubs_detailed.csv", index=False)
    
    bridges = final_nodes.sort_values("bridge_score", ascending=False).head(500)
    bridges.to_csv(hub_bridge_cache / "top_bridges.csv", index=False)

    # 8. 摘要与 Manifest
    summary = {
        "node_count": len(nodes),
        "hub_counts": final_nodes["hub_type"].value_counts().to_dict(),
        "mean_in_degree": float(node_metrics["in_degree"].mean()),
        "max_in_degree": int(node_metrics["in_degree"].max()),
        "cross_industry_edge_count": int(len(cross_industry_edges)),
        "template_duplicate_count": int((final_nodes["hub_type"] == "template_duplicate_suspect").sum()),
    }
    
    with open(hub_bridge_cache / "hub_bridge_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    manifest = {
        "task_id": "T2.6",
        "task_name": "Hub and cross-industry bridge research",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "outputs": {
            "node_labels": str(hub_bridge_cache / "node_hub_bridge_labels.parquet"),
            "summary": str(hub_bridge_cache / "hub_bridge_summary.json")
        },
        "node_order_safety": "node_id_contiguous"
    }

    with open(manifests_dir / "t26_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T2.6 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
