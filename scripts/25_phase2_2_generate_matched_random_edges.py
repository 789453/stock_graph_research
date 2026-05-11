#!/usr/bin/env python3
"""
T2.2.5: 生成匹配随机边 (Refactored)
为语义边生成匹配随机边（Matched Random Edges），用于对比研究。
严格遵循 Node Order Safety。
"""
import os
import json
import time
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm

sys_path = str(Path(__file__).parent.parent / "src")
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from semantic_graph_research import load_config
from semantic_graph_research.phase2_graph_layers import prepare_nodes_index

def generate_matched_random_edges(args):
    start_time = time.time()
    
    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.2.5: 生成匹配随机边 (Refactored)")
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
            cache_dir = sorted(cache_dirs)[-1]

    phase2_cache = cache_dir / "phase2"
    resonance_cache = phase2_cache / "resonance"
    resonance_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = phase2_cache / "manifests"

    # 1. 加载节点与行业
    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    nodes = prepare_nodes_index(nodes, len(nodes))
    
    sw_member_path = Path(config["paths"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        nodes = nodes.merge(sw_member[["ts_code", "l1_name", "l3_name"]], 
                          left_on="stock_code", right_on="ts_code", how="left")
    
    # 2. 加载边
    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    edges = pd.read_parquet(edges_path)
    # 只针对前20个邻居生成匹配随机边以节省空间
    edges_k20 = edges[edges["rank"] <= 20].copy()
    print(f"[OK] 加载 {len(edges_k20)} 条候选边 (k<=20)")

    # 3. 生成匹配逻辑
    print("[Step 1] 生成匹配随机基准...")
    np.random.seed(42)
    
    # 预先构建行业池
    l1_pools = {l1: group["node_id"].values for l1, group in nodes.groupby("l1_name")}
    node_to_l1 = nodes.set_index("node_id")["l1_name"].to_dict()
    
    matched_results = []
    
    for _, row in tqdm(edges_k20.iterrows(), total=len(edges_k20), desc="Generating matches"):
        src_id = int(row["src_node_id"])
        dst_id = int(row["dst_node_id"])
        dst_l1 = node_to_l1.get(dst_id, "UNKNOWN")
        
        # 匹配策略：寻找一个与原 dst 相同 L1 行业的随机节点
        if dst_l1 in l1_pools:
            pool = l1_pools[dst_l1]
            # 排除自己和原 dst
            pool = pool[(pool != src_id) & (pool != dst_id)]
            if len(pool) > 0:
                random_dst = np.random.choice(pool)
            else:
                random_dst = np.random.choice(nodes["node_id"].values)
        else:
            random_dst = np.random.choice(nodes["node_id"].values)
            
        matched_results.append({
            "src_node_id": src_id,
            "semantic_dst_node_id": dst_id,
            "random_dst_node_id": random_dst,
            "rank": row["rank"]
        })
        
    matched_df = pd.DataFrame(matched_results)
    
    # 4. 保存结果
    output_path = resonance_cache / "matched_random_edges_k20.parquet"
    matched_df.to_parquet(output_path, index=False)
    print(f"[OK] 匹配随机边已保存: {output_path}")

    # 5. Manifest
    elapsed = time.time() - start_time
    manifest = {
        "task_id": "T2.2.5",
        "task_name": "generate_matched_random_edges",
        "status": "success",
        "cache_key": cache_dir.name,
        "outputs": {
            "matched_random_edges": str(output_path)
        },
        "parameters": {
            "n_repeats": 1,
            "match_criteria": "same_l1_industry",
            "seed": 42
        }
    }
    
    with open(manifests_dir / "t25_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"T2.2.5 完成. Elapsed: {elapsed:.1f}s")

def main():
    parser = argparse.ArgumentParser(description="T2.2.5: 生成匹配随机边")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()
    generate_matched_random_edges(args)

if __name__ == "__main__":
    main()
