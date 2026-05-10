#!/usr/bin/env python3
"""
T2 - 节点表构建
把向量行号变成稳定、可解释、可连接的图节点
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, build_node_table
from semantic_graph_research.cache_io import save_nodes, read_cache_manifest

def main():
    config_path = Path(__file__).parent.parent / "configs" / "phase1_semantic_graph.yaml"
    config = load_config(config_path)

    print("=" * 60)
    print("T2: 节点表构建")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    if not cache_root.exists():
        print("[FAIL] T1 缓存不存在，请先运行 T1")
        sys.exit(1)

    cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
    if not cache_dirs:
        print("[FAIL] 未找到 T1 缓存")
        sys.exit(1)

    cache_dir = sorted(cache_dirs)[-1]
    manifest = read_cache_manifest(cache_dir)
    print(f"[OK] 读取 T1 缓存: {cache_dir}")

    bundle = load_semantic_view(config)
    print(f"[OK] 重新加载语义数据")

    nodes = build_node_table(bundle, config["semantic"]["records_path"])
    print(f"[OK] 节点表构建完成")
    print(f"     节点数: {len(nodes)}")
    print(f"     node_id 范围: {nodes['node_id'].min()} - {nodes['node_id'].max()}")
    print(f"     record_id 唯一数: {nodes['record_id'].nunique()}")
    print(f"     stock_code 唯一数: {nodes['stock_code'].nunique()}")

    assert len(nodes) == 5502, f"节点数应为 5502，实际为 {len(nodes)}"
    assert nodes["node_id"].min() == 0 and nodes["node_id"].max() == 5501, "node_id 应为 0-5501 连续"
    assert nodes["record_id"].nunique() == 5502, "record_id 应全部唯一"
    assert nodes["stock_code"].nunique() == 5502, "stock_code 应全部唯一"
    print("[OK] 节点表验证通过")

    save_nodes(cache_dir, nodes)
    print(f"[OK] 节点表已保存至: {cache_dir / 'nodes.parquet'}")

    manifest["task"] = "T2"
    manifest["nodes_count"] = len(nodes)
    with open(cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("T2 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()