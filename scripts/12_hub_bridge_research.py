#!/usr/bin/env python3
"""
T2.6: Hub 与跨行业桥研究
识别 hub 节点和跨行业桥边，分析其统计特征
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / "cache" / "semantic_graph" / "2eebde04e582"
    phase2_cache = cache_dir / "phase2"
    hub_bridge_cache = phase2_cache / "hub_bridge"
    hub_bridge_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = project_root / "outputs" / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.6: Hub 与跨行业桥研究")
    print("=" * 60)

    import pandas as pd
    import numpy as np

    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在，请先运行 T2.1")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    sw_member_path = Path("/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet")
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        print(f"[OK] 申万数据: {len(sw_member)} records")
    else:
        sw_member = pd.DataFrame(columns=["ts_code", "l1_name", "l2_name", "l3_name"])

    print("\n[Step 1] 计算节点出度和入度...")
    in_degrees = edges.groupby("dst_node_id").size().reindex(range(len(nodes)), fill_value=0)
    out_degrees = edges.groupby("src_node_id").size().reindex(range(len(nodes)), fill_value=0)

    node_stats = pd.DataFrame({
        "node_id": range(len(nodes)),
        "in_degree_k100": in_degrees.values,
        "out_degree_k100": out_degrees.values,
    })

    k20_edges = edges[edges["rank"] <= 20]
    in_deg20 = k20_edges.groupby("dst_node_id").size().reindex(range(len(nodes)), fill_value=0)
    out_deg20 = k20_edges.groupby("src_node_id").size().reindex(range(len(nodes)), fill_value=0)
    node_stats["in_degree_k20"] = in_deg20.values
    node_stats["out_degree_k20"] = out_deg20.values

    print("\n[Step 2] 计算度统计...")
    degree_stats = {
        "in_degree_k100": {
            "mean": round(float(node_stats["in_degree_k100"].mean()), 2),
            "std": round(float(node_stats["in_degree_k100"].std()), 2),
            "min": int(node_stats["in_degree_k100"].min()),
            "max": int(node_stats["in_degree_k100"].max()),
            "median": float(node_stats["in_degree_k100"].median()),
        },
        "in_degree_k20": {
            "mean": round(float(node_stats["in_degree_k20"].mean()), 2),
            "std": round(float(node_stats["in_degree_k20"].std()), 2),
            "min": int(node_stats["in_degree_k20"].min()),
            "max": int(node_stats["in_degree_k20"].max()),
            "median": float(node_stats["in_degree_k20"].median()),
        },
    }
    print(json.dumps(degree_stats, indent=2))

    print("\n[Step 3] 识别 Hub 节点 (top 5% in-degree)...")
    hub_threshold_k100 = node_stats["in_degree_k100"].quantile(0.95)
    hub_threshold_k20 = node_stats["in_degree_k20"].quantile(0.95)
    node_stats["is_hub_k100"] = node_stats["in_degree_k100"] >= hub_threshold_k100
    node_stats["is_hub_k20"] = node_stats["in_degree_k20"] >= hub_threshold_k20

    hubs_k100 = node_stats[node_stats["is_hub_k100"]].copy()
    hubs_k20 = node_stats[node_stats["is_hub_k20"]].copy()
    print(f"Hub 节点数量 (k100, top 5%): {len(hubs_k100)}")
    print(f"Hub 节点数量 (k20, top 5%): {len(hubs_k20)}")

    print("\n[Step 4] 添加行业信息和节点元数据...")
    nodes_with_stats = nodes.merge(node_stats, on="node_id", how="left")
    nodes_with_industry = nodes_with_stats.merge(
        sw_member[["ts_code", "l1_name", "l2_name", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )

    if len(hubs_k100) > 0:
        hub_k100_with_info = nodes_with_industry[nodes_with_industry["is_hub_k100"]].copy()
        hub_k100_with_info = hub_k100_with_info.sort_values("in_degree_k100", ascending=False)
        print("\nTop 10 Hub 节点 (k100):")
        print(hub_k100_with_info[["stock_code", "stock_name", "l1_name", "in_degree_k100", "in_degree_k20"]].head(10).to_string(index=False))

        hub_k100_with_info.to_parquet(hub_bridge_cache / "hubs_k100.parquet", index=False)
        print(f"[OK] hubs_k100.parquet 已保存: {len(hub_k100_with_info)} nodes")

    print("\n[Step 5] 识别跨行业边...")
    edges_merged = edges.merge(
        nodes_with_industry[["node_id", "l1_name"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_src"),
    )
    edges_merged = edges_merged.merge(
        nodes_with_industry[["node_id", "l1_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_dst"),
    )

    edges_merged["cross_industry"] = ~(
        (edges_merged["l1_name"] == edges_merged["l1_name_dst"]) &
        edges_merged["l1_name"].notna()
    )

    cross_industry_edges = edges_merged[edges_merged["cross_industry"]].copy()
    print(f"跨行业边数量: {len(cross_industry_edges)}")
    print(f"跨行业边比例: {len(cross_industry_edges) / len(edges) * 100:.2f}%")

    print("\n[Step 6] 分析 Hub 节点的跨行业连接...")
    if len(hubs_k100) > 0:
        hub_cross_edges = cross_industry_edges[cross_industry_edges["src_node_id"].isin(hubs_k100["node_id"])]
        print(f"Hub (k100) 发出的跨行业边数量: {len(hub_cross_edges)}")

        hub_cross_by_rank = hub_cross_edges.groupby("rank").size()
        print("\nHub 跨行业边按 rank 分布 (前10):")
        print(hub_cross_by_rank.head(10))

    print("\n[Step 7] 识别跨行业桥节点...")
    cross_by_src = cross_industry_edges.groupby("src_node_id").agg(
        cross_industry_count=("cross_industry", "sum"),
        mean_cross_score=("score", "mean"),
    ).reset_index()

    bridge_threshold = cross_by_src["cross_industry_count"].quantile(0.95)
    cross_by_src["is_bridge"] = cross_by_src["cross_industry_count"] >= bridge_threshold

    bridges = cross_by_src[cross_by_src["is_bridge"]].copy()
    bridges_with_info = bridges.merge(
        nodes_with_industry,
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_old"),
    )
    bridges_with_info = bridges_with_info.sort_values("cross_industry_count", ascending=False)
    print(f"\n跨行业桥节点数量 (top 5%): {len(bridges)}")
    print("\nTop 10 跨行业桥节点:")
    print(bridges_with_info[["stock_code", "stock_name", "l1_name", "cross_industry_count", "mean_cross_score"]].head(10).to_string(index=False))

    bridges_with_info.to_parquet(hub_bridge_cache / "cross_industry_bridges.parquet", index=False)
    print(f"[OK] cross_industry_bridges.parquet 已保存: {len(bridges_with_info)} nodes")

    print("\n[Step 8] 保存节点 Hub/Bridge 标签...")
    node_labels = nodes_with_industry[["node_id", "stock_code", "stock_name", "in_degree_k100", "in_degree_k20", "is_hub_k100", "is_hub_k20"]].copy()
    node_labels = node_labels.merge(
        cross_by_src[["src_node_id", "cross_industry_count", "is_bridge"]].rename(columns={"src_node_id": "node_id"}),
        on="node_id",
        how="left",
    )
    node_labels["cross_industry_count"] = node_labels["cross_industry_count"].fillna(0).astype(int)
    node_labels["is_bridge"] = node_labels["is_bridge"].fillna(False)
    node_labels.to_parquet(hub_bridge_cache / "node_hub_bridge_labels.parquet", index=False)
    print(f"[OK] node_hub_bridge_labels.parquet 已保存: {len(node_labels)} nodes")

    print("\n[Step 9] 生成摘要...")
    summary = {
        "total_nodes": int(len(nodes)),
        "hub_k100_count": int(len(hubs_k100)),
        "hub_k100_threshold": float(hub_threshold_k100),
        "hub_k20_count": int(len(hubs_k20)),
        "hub_k20_threshold": float(hub_threshold_k20),
        "cross_industry_edge_count": int(len(cross_industry_edges)),
        "cross_industry_edge_ratio": round(float(len(cross_industry_edges) / len(edges)), 4),
        "bridge_node_count": int(len(bridges)),
        "degree_stats": degree_stats,
    }

    summary_path = hub_bridge_cache / "hub_bridge_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] hub_bridge_summary.json 已保存")

    manifest = {
        "task_id": "T2.6",
        "task_name": "Hub and cross-industry bridge research",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [str(edges_path), str(sw_member_path)],
        "outputs": [
            str(hub_bridge_cache / "hubs_k100.parquet"),
            str(hub_bridge_cache / "cross_industry_bridges.parquet"),
            str(hub_bridge_cache / "node_hub_bridge_labels.parquet"),
            str(summary_path),
        ],
        "parameters": {},
        "warnings": [],
        "error": None,
    }

    with open(manifests_dir / "t26_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.6 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()