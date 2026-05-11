#!/usr/bin/env python3
"""
T4 - 图诊断计算
先描述图结构，再决定要不要做更复杂的图方法
"""
import sys
import json
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest, save_graph_stats, save_layout_pca2
from semantic_graph_research.diagnostics import compute_graph_stats, compute_industry_diagnostics, make_neighbor_examples, compute_layout_pca2

def main():
    parser = argparse.ArgumentParser(description="T4: 图诊断计算")
    parser.add_argument("--config", default="configs/phase1_semantic_graph.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T4: 图诊断计算")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    if args.cache_key:
        cache_dir = cache_root / args.cache_key
    else:
        cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
        if not cache_dirs:
            print("[FAIL] 未找到缓存")
            sys.exit(1)
        cache_dir = sorted(cache_dirs)[-1]

    if not cache_dir.exists():
        print(f"[FAIL] 缓存目录不存在: {cache_dir}")
        sys.exit(1)

    manifest = read_cache_manifest(cache_dir)
    print(f"[OK] 读取缓存: {cache_dir}")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    canonical_k = config["graph"]["canonical_k"]
    directed_edges = pd.read_parquet(cache_dir / f"edges_directed_k{canonical_k}.parquet")
    mutual_edges = pd.read_parquet(cache_dir / f"edges_mutual_k{canonical_k}.parquet")
    print(f"[OK] 加载边表: directed={len(directed_edges)}, mutual={len(mutual_edges)}")

    # 强断言：节点 ID 范围和自环检查
    print("[INFO] 正在执行边表强断言...")
    assert directed_edges["src_node_id"].between(0, len(nodes)-1).all(), "src_node_id 超出范围"
    assert directed_edges["dst_node_id"].between(0, len(nodes)-1).all(), "dst_node_id 超出范围"
    assert not (directed_edges["src_node_id"] == directed_edges["dst_node_id"]).any(), "存在自环边"
    assert directed_edges.groupby("src_node_id").size().nunique() == 1, "每个节点的出度必须一致"
    print("[OK] 边表强断言通过")

    print("\n--- 计算图结构统计 ---")
    with tqdm(desc="compute_graph_stats", unit="step") as pbar:
        pbar.update(1)
        graph_stats = compute_graph_stats(nodes, directed_edges, mutual_edges, show_progress=True)
        pbar.update(1)
    for key, value in graph_stats.items():
        print(f"  {key}: {value}")

    save_graph_stats(cache_dir, canonical_k, graph_stats)
    print(f"[OK] 图统计已保存: graph_stats_k{canonical_k}.json")

    print("\n--- 加载申万行业数据 ---")
    sw_member_path = Path(config["market"]["stock_sw_member_path"])
    if not sw_member_path.exists():
        print(f"[WARN] 申万数据不存在: {sw_member_path}")
        sw_member_current = pd.DataFrame(columns=["ts_code", "l1_name", "l2_name", "l3_name"])
    else:
        sw_member_current = pd.read_parquet(sw_member_path)
        print(f"[OK] 申万数据加载: {len(sw_member_current)} records")

    # 扩展指标：按 rank 统计分数和行业一致性
    print("\n--- 计算扩展诊断指标 (Score/Industry by Rank) ---")
    
    # 关联行业信息
    node_with_industry = nodes.merge(
        sw_member_current[["ts_code", "l1_name", "l2_name", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )
    
    edges_with_industry = directed_edges.merge(
        node_with_industry[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
    ).merge(
        node_with_industry[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("_src", "_dst")
    )
    
    edges_with_industry["same_l1"] = (edges_with_industry["l1_name_src"] == edges_with_industry["l1_name_dst"]) & edges_with_industry["l1_name_src"].notna()
    edges_with_industry["same_l2"] = (edges_with_industry["l2_name_src"] == edges_with_industry["l2_name_dst"]) & edges_with_industry["l2_name_src"].notna()
    edges_with_industry["same_l3"] = (edges_with_industry["l3_name_src"] == edges_with_industry["l3_name_dst"]) & edges_with_industry["l3_name_src"].notna()
    
    # 计算互惠状态
    mutual_pairs = set(zip(mutual_edges["src_node_id"], mutual_edges["dst_node_id"]))
    edges_with_industry["is_mutual"] = edges_with_industry.apply(lambda row: (row["src_node_id"], row["dst_node_id"]) in mutual_pairs, axis=1)
    
    stats_by_rank = edges_with_industry.groupby("rank").agg({
        "score": ["mean", "median", "min", "max"],
        "same_l1": "mean",
        "same_l2": "mean",
        "same_l3": "mean",
        "is_mutual": "mean"
    })
    stats_by_rank.columns = [f"{col[0]}_{col[1]}" if isinstance(col, tuple) else col for col in stats_by_rank.columns]
    stats_by_rank.to_csv(cache_dir / "stats_by_rank.csv")
    print(f"[OK] 分 Rank 统计已保存: stats_by_rank.csv")
    
    # 入度分布和 Hub 节点
    in_degrees = directed_edges.groupby("dst_node_id").size().reindex(range(len(nodes)), fill_value=0)
    in_degree_dist = in_degrees.value_counts().sort_index()
    in_degree_dist.to_csv(cache_dir / "in_degree_distribution.csv")
    
    hub_nodes = nodes.copy()
    hub_nodes["in_degree"] = in_degrees.values
    hub_nodes = hub_nodes.sort_values("in_degree", ascending=False).head(100)
    hub_nodes.to_csv(cache_dir / "hub_top_nodes.csv", index=False)
    print(f"[OK] Hub 节点分析已保存: hub_top_nodes.csv")
    
    # 疑似重复文本审计 (Score > 0.98)
    duplicate_suspects = directed_edges[directed_edges["score"] > 0.98].copy()
    duplicate_suspects = duplicate_suspects.merge(
        nodes[["node_id", "stock_name"]], left_on="src_node_id", right_on="node_id"
    ).merge(
        nodes[["node_id", "stock_name"]], left_on="dst_node_id", right_on="node_id", suffixes=("_src", "_dst")
    )
    duplicate_suspects.to_csv(cache_dir / "score_gt_098_pairs.csv", index=False)
    print(f"[OK] 疑似重复项审计已保存: score_gt_098_pairs.csv (count={len(duplicate_suspects)})")

    print("\n--- 计算行业诊断 ---")
    with tqdm(desc="compute_industry_diagnostics", unit="step") as pbar:
        pbar.update(1)
        industry_diagnostics = compute_industry_diagnostics(nodes, directed_edges, sw_member_current, show_progress=True)
        pbar.update(1)
    industry_diagnostics.to_parquet(cache_dir / "industry_diagnostics_k20.parquet", index=False)
    print(f"[OK] 行业诊断已保存: {len(industry_diagnostics)} records")

    print("\n--- 生成邻居样例 ---")
    if len(sw_member_current) > 0:
        with tqdm(desc="make_neighbor_examples", unit="step") as pbar:
            pbar.update(1)
            neighbor_examples = make_neighbor_examples(nodes, directed_edges, sw_member_current, n_examples=12)
            pbar.update(1)
        neighbor_examples.to_parquet(cache_dir / "neighbor_examples_k20.parquet", index=False)
        print(f"[OK] 邻居样例已保存: {len(neighbor_examples)} records")

    print("\n--- 计算 PCA2 布局 ---")
    from semantic_graph_research import load_semantic_view
    bundle = load_semantic_view(config)
    layout = compute_layout_pca2(bundle.vectors, list(range(len(nodes))))
    save_layout_pca2(cache_dir, layout)
    print(f"[OK] PCA2 布局已保存: {len(layout)} nodes")

    sw_join = nodes.merge(
        sw_member_current[["ts_code", "l1_name", "l2_name", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )
    sw_join.to_parquet(cache_dir / "industry_join_current.parquet", index=False)
    print(f"[OK] 行业关联表已保存")

    manifest["task"] = "T4"
    manifest["diagnostics_manifest"] = {
        "canonical_k": canonical_k,
        "has_stats_by_rank": True,
        "has_hub_analysis": True,
        "has_duplicate_suspects": True,
        "duplicate_suspects_count": len(duplicate_suspects),
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "03_compute_graph_diagnostics.py",
    }
    
    with open(cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T4 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()