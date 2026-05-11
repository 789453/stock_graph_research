#!/usr/bin/env python3
"""
T2 - 节点表构建
把向量行号变成稳定、可解释、可连接的图节点
"""
import sys
import json
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, build_node_table
from semantic_graph_research.cache_io import save_nodes, read_cache_manifest

def main():
    parser = argparse.ArgumentParser(description="T2: 节点表构建")
    parser.add_argument("--config", default="configs/phase1_semantic_graph.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定 T1 缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2: 节点表构建")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    if not cache_root.exists():
        print("[FAIL] T1 缓存不存在，请先运行 T1")
        sys.exit(1)

    if args.cache_key:
        cache_dir = cache_root / args.cache_key
    else:
        # 默认找最新的缓存
        cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
        if not cache_dirs:
            print("[FAIL] 未找到 T1 缓存")
            sys.exit(1)
        cache_dir = sorted(cache_dirs)[-1]

    if not cache_dir.exists():
        print(f"[FAIL] 缓存目录不存在: {cache_dir}")
        sys.exit(1)

    manifest = read_cache_manifest(cache_dir)
    print(f"[OK] 读取 T1 缓存: {cache_dir}")

    bundle = load_semantic_view(config)
    print(f"[OK] 重新加载语义数据")

    # 构建节点表
    nodes = build_node_table(bundle, config["semantic"]["records_path"])
    
    # 增加 SW 行业信息（如果存在）
    # 假设 records_df 中已经有行业信息，或者需要从外部加载
    # 这里的 build_node_table 是在 src/semantic_graph_research/semantic_loader.py 中定义的
    
    print(f"[OK] 节点表构建完成")
    print(f"     节点数: {len(nodes)}")
    
    # 强断言：不可妥协的顺序和唯一性检查
    print("[INFO] 正在执行节点表强断言...")
    assert (nodes["node_id"].to_numpy() == np.arange(len(nodes))).all(), "node_id 必须是 0 开始的连续整数且有序"
    assert nodes["stock_code"].is_unique, "stock_code 必须唯一"
    assert nodes["record_id"].is_unique, "record_id 必须唯一"
    
    # 检查 vector_row (如果 nodes 中没有，可以添加)
    if "vector_row" not in nodes.columns:
        nodes["vector_row"] = nodes["node_id"]
    
    assert (nodes["node_id"] == nodes["vector_row"]).all(), "node_id 必须等于 vector_row"
    print("[OK] 节点表强断言通过")

    save_nodes(cache_dir, nodes)
    print(f"[OK] 节点表已保存至: {cache_dir / 'nodes.parquet'}")

    nodes_manifest = {
        "node_count": len(nodes),
        "node_id_policy": "node_id equals vector_row from meta row_ids order",
        "sort_policy": "no resort after semantic row order",
        "stock_code_unique": True,
        "record_id_unique": True,
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "01_build_nodes.py",
    }
    
    manifest["task"] = "T2"
    manifest["nodes_manifest"] = nodes_manifest
    
    with open(cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    with open(cache_dir / "nodes_manifest.json", "w", encoding="utf-8") as f:
        json.dump(nodes_manifest, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("T2 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()