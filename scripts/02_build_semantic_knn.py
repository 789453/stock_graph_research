#!/usr/bin/env python3
"""
T3 - 真实向量上的 FAISS kNN 构图
使用真实 1024 维语义向量构造近邻图
"""
import sys
import json
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, build_faiss_knn, neighbors_to_directed_edges, derive_mutual_edges
from semantic_graph_research.cache_io import read_cache_manifest, save_neighbors, save_edges

def main():
    parser = argparse.ArgumentParser(description="T3: FAISS kNN 构图")
    parser.add_argument("--config", default="configs/phase1_semantic_graph.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    parser.add_argument("--k", type=int, help="覆盖配置中的 k 值")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T3: FAISS kNN 构图")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    if not cache_root.exists():
        print("[FAIL] 缓存目录不存在")
        sys.exit(1)

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

    bundle = load_semantic_view(config)
    vectors = bundle.vectors
    print(f"[OK] 加载向量: shape={vectors.shape}")

    gpu_device = config["graph"].get("gpu_device", -1)
    sensitivity_k = [args.k] if args.k else config["graph"]["sensitivity_k"]
    print(f"[OK] GPU device: {gpu_device}, k values: {sensitivity_k}")

    knn_manifests = {}

    for k in sensitivity_k:
        print(f"\n--- Processing k={k} ---")

        neighbors = build_faiss_knn(vectors, k, gpu_device=gpu_device)
        print(f"[OK] k={k} kNN 完成: indices.shape={neighbors.indices.shape}")

        assert neighbors.indices.shape == (len(bundle.row_ids), k), f"indices shape 应为 ({len(bundle.row_ids)}, {k})"
        assert neighbors.scores.shape == (len(bundle.row_ids), k), f"scores shape 应为 ({len(bundle.row_ids)}, {k})"
        
        # 验证没有自邻居
        row_ids = np.arange(len(bundle.row_ids))
        has_self = (neighbors.indices == row_ids[:, None]).any()
        assert not has_self, "存在 self-neighbor"
        print(f"[OK] k={k} 验证通过")

        save_neighbors(cache_dir, neighbors)
        print(f"[OK] k={k} 邻居矩阵已保存")

        nodes_path = cache_dir / "nodes.parquet"
        if not nodes_path.exists():
            print(f"[FAIL] nodes.parquet 不存在，请先运行 T2")
            sys.exit(1)
        nodes = pd.read_parquet(nodes_path)

        directed_edges = neighbors_to_directed_edges(neighbors, nodes)
        directed_edges.to_parquet(cache_dir / f"edges_directed_k{k}.parquet", index=False)
        print(f"[OK] k={k} 有向边表已保存: {len(directed_edges)} edges")

        mutual_edges = derive_mutual_edges(directed_edges)
        mutual_edges.to_parquet(cache_dir / f"edges_mutual_k{k}.parquet", index=False)
        print(f"[OK] k={k} 双向边表已保存: {len(mutual_edges)} edges")

        knn_manifests[f"k{k}"] = {
            "k": k,
            "metric": "cosine_via_l2_normalized_inner_product",
            "self_neighbor_removed": True,
            "indices_shape": list(neighbors.indices.shape),
            "scores_shape": list(neighbors.scores.shape),
            "score_min": float(np.min(neighbors.scores)),
            "score_mean": float(np.mean(neighbors.scores)),
            "score_max": float(np.max(neighbors.scores)),
            "gpu_used": gpu_device >= 0,
            "directed_edges_count": len(directed_edges),
            "mutual_edges_count": len(mutual_edges),
            "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        }

    manifest["task"] = "T3"
    manifest["k_values"] = sensitivity_k
    manifest["knn_manifests"] = knn_manifests
    
    with open(cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    with open(cache_dir / "knn_manifest.json", "w", encoding="utf-8") as f:
        json.dump(knn_manifests, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T3 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()