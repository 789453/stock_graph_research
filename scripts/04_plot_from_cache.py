#!/usr/bin/env python3
"""
T5 - 仅从缓存绘图
证明中间结果已被正确固化，图表生成不依赖重新计算上游
"""
import sys
import json
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def main():
    config_path = Path(__file__).parent.parent / "configs" / "phase1_semantic_graph.yaml"
    config = load_config(config_path)

    print("=" * 60)
    print("T5: 仅从缓存绘图")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
    if not cache_dirs:
        print("[FAIL] 未找到缓存")
        sys.exit(1)

    cache_dir = sorted(cache_dirs)[-1]
    print(f"[OK] 读取缓存: {cache_dir}")

    output_dir = Path(config["plots"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] 输出目录: {output_dir}")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 从缓存加载 nodes.parquet: {len(nodes)} nodes")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    canonical_k = config["graph"]["canonical_k"]
    print(f"\n--- 生成图表 (k={canonical_k}) ---")

    from semantic_graph_research.plotting import (
        plot_score_distribution_from_cache,
        plot_degree_distribution_from_cache,
        plot_pca2_scatter_from_cache,
        plot_ego_neighbors_from_cache,
    )

    print("[1/4] 生成 score_distribution_k20.png")
    plot_score_distribution_from_cache(cache_dir, output_dir)

    print("[2/4] 生成 degree_distribution_k20.png")
    plot_degree_distribution_from_cache(cache_dir, output_dir)

    print("[3/4] 生成 pca2_scatter_by_current_sw_l1.png")
    sw_member_path = Path(config["market"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member_current = pd.read_parquet(sw_member_path)
        plot_pca2_scatter_from_cache(cache_dir, output_dir, nodes, sw_member_current)
    else:
        print(f"[WARN] 申万数据不存在，跳过 PCA scatter 着色")

    print("[4/4] 生成 ego_neighbors_examples_k20.png")
    plot_ego_neighbors_from_cache(cache_dir, output_dir)

    print("\n" + "=" * 60)
    print(f"T5 完成 - 图表已保存至 {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()