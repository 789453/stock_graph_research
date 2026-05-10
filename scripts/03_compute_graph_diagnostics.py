#!/usr/bin/env python3
"""
T4 - 图诊断计算
先描述图结构，再决定要不要做更复杂的图方法
"""
import sys
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest, save_graph_stats, save_layout_pca2
from semantic_graph_research.diagnostics import compute_graph_stats, compute_industry_diagnostics, make_neighbor_examples, compute_layout_pca2

def main():
    config_path = Path(__file__).parent.parent / "configs" / "phase1_semantic_graph.yaml"
    config = load_config(config_path)

    print("=" * 60)
    print("T4: 图诊断计算")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
    if not cache_dirs:
        print("[FAIL] 未找到缓存")
        sys.exit(1)

    cache_dir = sorted(cache_dirs)[-1]
    manifest = read_cache_manifest(cache_dir)
    print(f"[OK] 读取缓存: {cache_dir}")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    canonical_k = config["graph"]["canonical_k"]
    directed_edges = pd.read_parquet(cache_dir / f"edges_directed_k{canonical_k}.parquet")
    mutual_edges = pd.read_parquet(cache_dir / f"edges_mutual_k{canonical_k}.parquet")
    print(f"[OK] 加载边表: directed={len(directed_edges)}, mutual={len(mutual_edges)}")

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
    with open(cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T4 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()