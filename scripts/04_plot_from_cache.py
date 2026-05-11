#!/usr/bin/env python3
"""
T5 - 仅从缓存绘图
证明中间结果已被正确固化，图表生成不依赖重新计算上游
"""
import sys
import json
import argparse
from pathlib import Path
import hashlib
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def setup_chinese_font():
    font_name = "WenQuanYi Micro Hei"
    if font_name in (f.name for f in fm.fontManager.ttflist):
        plt.rcParams.update({
            "font.family": "sans-serif",
            "font.sans-serif": [font_name, "DejaVu Sans"],
            "axes.unicode_minus": False,
        })
        print(f"[INFO] 已设置中文字体: {font_name}")
    else:
        print(f"[WARN] 未找到字体: {font_name}，可能无法正常显示中文")

def get_file_sha256(file_path):
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description="T5: 仅从缓存绘图")
    parser.add_argument("--config", default="configs/phase1_semantic_graph.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T5: 仅从缓存绘图")
    print(f"Config: {args.config}")
    print("=" * 60)

    setup_chinese_font()

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

    print(f"[OK] 读取缓存: {cache_dir}")

    output_dir = Path(config["plots"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] 输出目录: {output_dir}")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 从缓存加载 nodes.parquet: {len(nodes)} nodes")

    canonical_k = config["graph"]["canonical_k"]
    print(f"\n--- 生成图表 (k={canonical_k}) ---")

    from semantic_graph_research.plotting import (
        plot_score_distribution_from_cache,
        plot_degree_distribution_from_cache,
        plot_pca2_scatter_from_cache,
        plot_ego_neighbors_from_cache,
    )

    plot_manifest = {}

    def run_plot(plot_func, filename, *args, **kwargs):
        print(f"[INFO] 正在生成 {filename}...")
        plot_func(cache_dir, output_dir, *args, **kwargs)
        file_path = output_dir / filename
        if file_path.exists():
            size = file_path.stat().st_size
            if size < 1000:
                print(f"[WARN] {filename} 文件太小 ({size} bytes)，可能绘图失败")
                status = "warning"
            else:
                print(f"[OK] {filename} 生成成功")
                status = "ok"
            
            plot_manifest[filename] = {
                "plot_file": filename,
                "path": str(file_path),
                "size_bytes": size,
                "status": status,
                "created_at_utc": pd.Timestamp.utcnow().isoformat(),
            }
        else:
            print(f"[FAIL] {filename} 未生成")
            plot_manifest[filename] = {"status": "fail"}

    run_plot(plot_score_distribution_from_cache, f"score_distribution_k{canonical_k}_true.png")
    run_plot(plot_degree_distribution_from_cache, "degree_distribution_k20.png")

    sw_member_path = Path(config["market"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member_current = pd.read_parquet(sw_member_path)
        run_plot(plot_pca2_scatter_from_cache, "pca2_scatter_by_current_sw_l1.png", nodes, sw_member_current)
    else:
        print(f"[WARN] 申万数据不存在，跳过 PCA scatter")

    run_plot(plot_ego_neighbors_from_cache, "ego_neighbors_examples_k20.png")

    # 保存图表清单
    with open(output_dir / "plot_manifest.json", "w", encoding="utf-8") as f:
        json.dump(plot_manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"T5 完成 - 图表清单已保存至 {output_dir / 'plot_manifest.json'}")
    print("=" * 60)

if __name__ == "__main__":
    main()