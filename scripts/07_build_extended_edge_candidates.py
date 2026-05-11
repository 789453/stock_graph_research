import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, build_faiss_knn
from semantic_graph_research.phase2_graph_layers import (
    build_edge_candidates_fixed,
    build_adaptive_core_edges,
    build_adaptive_context_edges,
    build_adaptive_cross_industry_bridge_edges,
    build_adaptive_within_l3_residual_edges,
)

def main():
    parser = argparse.ArgumentParser(description="T2.1: 构建扩展候选边池")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.1: 构建扩展候选边池")
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

    phase2_cache = cache_dir / "phase2" / "edge_layers"
    phase2_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    print(f"[OK] 使用缓存目录: {cache_dir}")

    print("\n[Step 1] 加载向量和节点表...")
    bundle = load_semantic_view(config)
    vectors = bundle.vectors
    print(f"[OK] 向量: shape={vectors.shape}")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 节点表: {len(nodes)} nodes")

    k = 100
    neighbors_k100_path = cache_dir / f"neighbors_k{k}.npz"

    if neighbors_k100_path.exists():
        print(f"[INFO] k={k} 邻居矩阵已存在，加载...")
        data = dict(np.load(neighbors_k100_path))
        neighbors_k100 = data["indices"]
        scores_k100 = data["scores"]
    else:
        print(f"\n[Step 2] 构建 k={k} 邻居矩阵...")
        gpu_device = config.get("graph", {}).get("gpu_device", -1)
        neighbor_matrix = build_faiss_knn(vectors, k, gpu_device=gpu_device)
        neighbors_k100 = neighbor_matrix.indices
        scores_k100 = neighbor_matrix.scores

        np.savez(neighbors_k100_path, indices=neighbors_k100, scores=scores_k100)
        print(f"[OK] k={k} 邻居矩阵已保存: {neighbors_k100_path}")

    print(f"[OK] 邻居矩阵: shape={neighbors_k100.shape}")

    print("\n[Step 3] 构建统一候选边池...")
    # build_edge_candidates_fixed 已经包含了 rank_band_exclusive 和 cumulative_topk_flags
    edges = build_edge_candidates_fixed(neighbors_k100, scores_k100, nodes)
    print(f"[OK] 候选边池: {len(edges)} edges")

    # 强断言：rank 1-100 完整性
    assert edges.groupby("src_node_id").size().eq(100).all(), "每个节点的候选边数必须为 100"
    assert "rank_band_exclusive" in edges.columns, "缺少 rank_band_exclusive 字段"
    assert "top_001_010" in edges.columns, "缺少 top_001_010 累计标签"
    print("[OK] 候选边池验证通过")

    edges.to_parquet(phase2_cache / "edge_candidates_k100.parquet", index=False)
    print(f"[OK] 候选边池已保存: edge_candidates_k100.parquet")

    score_by_rank = edges.groupby("rank")["score"].agg(["mean", "median", "std", "count"])
    score_by_rank.to_json(phase2_cache / "edge_score_by_rank.json")
    print(f"[OK] Score by rank 统计已保存")

    print("\n[Step 4] 加载申万行业数据...")
    sw_member_path = Path(config["market"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        print(f"[OK] 申万数据: {len(sw_member)} records")
    else:
        sw_member = pd.DataFrame(columns=["ts_code", "l1_name", "l3_name"])
        print(f"[WARN] 申万数据不存在，使用空 DataFrame")

    print("\n[Step 5] 生成 Adaptive Edge Layers...")

    print("[5.1] adaptive_core_edges...")
    adaptive_core = build_adaptive_core_edges(edges, nodes)
    adaptive_core.to_parquet(phase2_cache / "adaptive_core_edges.parquet", index=False)
    print(f"[OK] adaptive_core: {len(adaptive_core)} edges")

    print("[5.2] adaptive_context_edges...")
    adaptive_context = build_adaptive_context_edges(edges)
    adaptive_context.to_parquet(phase2_cache / "adaptive_context_edges.parquet", index=False)
    print(f"[OK] adaptive_context: {len(adaptive_context)} edges")

    if len(sw_member) > 0:
        print("[5.3] adaptive_cross_industry_bridge_edges...")
        adaptive_cross = build_adaptive_cross_industry_bridge_edges(edges, nodes, sw_member)
        adaptive_cross.to_parquet(phase2_cache / "adaptive_cross_industry_bridge_edges.parquet", index=False)
        print(f"[OK] adaptive_cross_industry_bridge: {len(adaptive_cross)} edges")

        print("[5.4] adaptive_within_l3_residual_edges...")
        adaptive_within_l3 = build_adaptive_within_l3_residual_edges(edges, nodes, sw_member)
        adaptive_within_l3.to_parquet(phase2_cache / "adaptive_within_l3_residual_edges.parquet", index=False)
        print(f"[OK] adaptive_within_l3_residual: {len(adaptive_within_l3)} edges")
    else:
        print("[WARN] 跳过 cross_industry 和 within_l3（无申万数据）")

    print("\n[Step 6] 生成边层摘要...")
    summary = {
        "task": "T2.1",
        "k": k,
        "edge_candidates_count": len(edges),
        "edge_candidates_k100_shape": list(neighbors_k100.shape),
        "generated_at": datetime.now().isoformat(),
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "07_build_extended_edge_candidates.py",
    }

    for layer_name in ["adaptive_core", "adaptive_context", "adaptive_cross_industry_bridge", "adaptive_within_l3_residual"]:
        path = phase2_cache / f"{layer_name}_edges.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            summary[f"{layer_name}_count"] = len(df)
            summary[f"{layer_name}_nodes_covered"] = df["src_node_id"].nunique()

    with open(phase2_cache / "edge_candidates_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[OK] 边层摘要已保存")

    manifest = {
        "task_id": "T2.1",
        "task_name": "Extended edge candidate pool",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "parameters": {"k": k},
        "summary": summary,
    }

    with open(manifests_dir / "t21_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.1 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()