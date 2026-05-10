#!/usr/bin/env python3
"""
T2.1: 构建扩展候选边池
目标：构建 k=100 候选边池，或统一 k10/k20/k50 为候选边
生成 adaptive edge layers: core, context, cross_industry_bridge, within_l3_residual
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def get_config():
    import yaml
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "phase2_semantic_graph_research.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    semantic_config = {
        "semantic": {
            "vectors_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.npy",
            "meta_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.meta.json",
            "records_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/parquet/records-all.parquet",
            "expected_rows": 5502,
            "expected_dim": 1024,
            "expected_dtype": "float32",
            "allow_fallback": False,
        }
    }
    config = {**config, **semantic_config}
    return config

def main():
    project_root = Path(__file__).parent.parent
    config = get_config()
    cache_dir = project_root / "cache" / "semantic_graph" / "2eebde04e582"
    phase2_cache = cache_dir / "phase2" / "edge_layers"
    phase2_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.1: 构建扩展候选边池")
    print("=" * 60)

    from semantic_graph_research import load_semantic_view, build_faiss_knn
    import pandas as pd
    import numpy as np

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
        gpu_device = config.get("graph", {}).get("gpu_device", 0)
        neighbor_matrix = build_faiss_knn(vectors, k, gpu_device=gpu_device)
        neighbors_k100 = neighbor_matrix.indices
        scores_k100 = neighbor_matrix.scores

        np.savez(neighbors_k100_path, indices=neighbors_k100, scores=scores_k100)
        print(f"[OK] k={k} 邻居矩阵已保存: {neighbors_k100_path}")

    print(f"[OK] 邻居矩阵: shape={neighbors_k100.shape}")

    from semantic_graph_research.phase2_graph_layers import (
        build_edge_candidates,
        build_adaptive_core_edges,
        build_adaptive_context_edges,
        build_adaptive_cross_industry_bridge_edges,
        build_adaptive_within_l3_residual_edges,
    )

    print("\n[Step 3] 构建统一候选边池...")
    edges = build_edge_candidates(neighbors_k100, scores_k100, nodes, config["graph_candidate"]["rank_bands"])
    print(f"[OK] 候选边池: {len(edges)} edges")

    edges.to_parquet(phase2_cache / "edge_candidates_k100.parquet", index=False)
    print(f"[OK] 候选边池已保存: edge_candidates_k100.parquet")

    score_by_rank = edges.groupby("rank")["score"].agg(["mean", "median", "std", "count"])
    score_by_rank.to_json(phase2_cache / "edge_score_by_rank.json")
    print(f"[OK] Score by rank 统计已保存")

    print("\n[Step 4] 加载申万行业数据...")
    sw_member_path = Path(config["semantic"]["records_path"]).parent.parent / "sw_member.parquet"
    default_sw_path = Path("/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet")
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        print(f"[OK] 申万数据: {len(sw_member)} records")
    elif default_sw_path.exists():
        sw_member = pd.read_parquet(default_sw_path)
        print(f"[OK] 申万数据(默认路径): {len(sw_member)} records")
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
    }

    for layer_name in ["adaptive_core", "adaptive_context"]:
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
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [
            "cache/semantic_graph/2eebde04e582/nodes.parquet",
            "cache/semantic_graph/2eebde04e582/neighbors_k100.npz",
            str(default_sw_path),
        ],
        "outputs": [
            "phase2/edge_layers/edge_candidates_k100.parquet",
            "phase2/edge_layers/adaptive_core_edges.parquet",
            "phase2/edge_layers/adaptive_context_edges.parquet",
            "phase2/edge_layers/adaptive_cross_industry_bridge_edges.parquet",
            "phase2/edge_layers/adaptive_within_l3_residual_edges.parquet",
            "phase2/edge_layers/edge_candidates_summary.json",
        ],
        "parameters": {"k": k},
        "warnings": [],
        "error": None,
    }

    with open(manifests_dir / "t21_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.1 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()