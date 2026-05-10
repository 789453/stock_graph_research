#!/usr/bin/env python3
"""
T2.5: 域内与跨域邻居分析
分析同规模/流动性域内和跨域的邻居分数差异
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / "cache" / "semantic_graph" / "2eebde04e582"
    phase2_cache = cache_dir / "phase2"
    baselines_cache = phase2_cache / "baselines"
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = project_root / "outputs" / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.5: 域内与跨域邻居分析")
    print("=" * 60)

    import pandas as pd
    import numpy as np

    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在，请先运行 T2.1")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    profile_path = baselines_cache / "node_size_liquidity_profile.parquet"
    if profile_path.exists():
        profile = pd.read_parquet(profile_path)
        print(f"[OK] 加载节点画像: {len(profile)} nodes")
    else:
        print("[WARN] 节点画像不存在，跳过规模/流动性分析")
        profile = pd.DataFrame(columns=["node_id", "size_quintile", "liquidity_quintile"])

    print("\n[Step 1] 合并规模/流动性信息...")
    edges_with_domain = edges.merge(
        profile[["node_id", "size_quintile", "liquidity_quintile"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_src"),
    )
    edges_with_domain = edges_with_domain.merge(
        profile[["node_id", "size_quintile", "liquidity_quintile"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_dst"),
    )

    edges_with_domain["same_size"] = (
        edges_with_domain["size_quintile"] == edges_with_domain["size_quintile_dst"]
    ) & edges_with_domain["size_quintile"].notna()
    edges_with_domain["same_liquidity"] = (
        edges_with_domain["liquidity_quintile"] == edges_with_domain["liquidity_quintile_dst"]
    ) & edges_with_domain["liquidity_quintile"].notna()
    edges_with_domain["same_domain"] = edges_with_domain["same_size"] & edges_with_domain["same_liquidity"]

    print("\n[Step 2] 按规模域内/跨域统计...")
    if "size_quintile" in edges_with_domain.columns:
        size_stats = []
        for q in [1, 2, 3, 4, 5]:
            q_edges = edges_with_domain[edges_with_domain["size_quintile"] == q]
            if len(q_edges) > 0:
                same_ratio = float(q_edges["same_size"].mean())
                same_mean_score = float(q_edges[q_edges["same_size"] == True]["score"].mean()) if q_edges["same_size"].sum() > 0 else np.nan
                cross_mean_score = float(q_edges[q_edges["same_size"] == False]["score"].mean()) if (~q_edges["same_size"]).sum() > 0 else np.nan
                size_stats.append({
                    "size_quintile": q,
                    "total_neighbors": len(q_edges),
                    "same_size_ratio": round(same_ratio, 4),
                    "same_size_mean_score": round(same_mean_score, 4) if not np.isnan(same_mean_score) else None,
                    "cross_size_mean_score": round(cross_mean_score, 4) if not np.isnan(cross_mean_score) else None,
                })
        size_df = pd.DataFrame(size_stats)
        print("\n按规模 quintile 的域内/跨域统计:")
        print(size_df.to_string(index=False))

    print("\n[Step 3] 按流动性域内/跨域统计...")
    if "liquidity_quintile" in edges_with_domain.columns:
        liq_stats = []
        for q in [1, 2, 3, 4, 5]:
            q_edges = edges_with_domain[edges_with_domain["liquidity_quintile"] == q]
            if len(q_edges) > 0:
                same_ratio = float(q_edges["same_liquidity"].mean())
                same_mean_score = float(q_edges[q_edges["same_liquidity"] == True]["score"].mean()) if q_edges["same_liquidity"].sum() > 0 else np.nan
                cross_mean_score = float(q_edges[q_edges["same_liquidity"] == False]["score"].mean()) if (~q_edges["same_liquidity"]).sum() > 0 else np.nan
                liq_stats.append({
                    "liquidity_quintile": q,
                    "total_neighbors": len(q_edges),
                    "same_liquidity_ratio": round(same_ratio, 4),
                    "same_liquidity_mean_score": round(same_mean_score, 4) if not np.isnan(same_mean_score) else None,
                    "cross_liquidity_mean_score": round(cross_mean_score, 4) if not np.isnan(cross_mean_score) else None,
                })
        liq_df = pd.DataFrame(liq_stats)
        print("\n按流动性 quintile 的域内/跨域统计:")
        print(liq_df.to_string(index=False))

    print("\n[Step 4] 按 rank_band 统计域内比例...")
    if "rank_band" in edges_with_domain.columns:
        rank_band_domain_stats = edges_with_domain.groupby("rank_band").agg(
            total=("score", "count"),
            same_size_count=("same_size", "sum"),
            same_liquidity_count=("same_liquidity", "sum"),
            same_domain_count=("same_domain", "sum"),
        ).reset_index()
        rank_band_domain_stats["same_size_ratio"] = (rank_band_domain_stats["same_size_count"] / rank_band_domain_stats["total"]).round(4)
        rank_band_domain_stats["same_liquidity_ratio"] = (rank_band_domain_stats["same_liquidity_count"] / rank_band_domain_stats["total"]).round(4)
        rank_band_domain_stats["same_domain_ratio"] = (rank_band_domain_stats["same_domain_count"] / rank_band_domain_stats["total"]).round(4)
        print("\n按 rank_band 的域内比例:")
        print(rank_band_domain_stats.to_string(index=False))

    print("\n[Step 5] 规模×流动性交叉分析...")
    if "size_quintile" in edges_with_domain.columns and "liquidity_quintile" in edges_with_domain.columns:
        cross_stats = []
        for sq in [1, 2, 3, 4, 5]:
            for lq in [1, 2, 3, 4, 5]:
                cell_edges = edges_with_domain[
                    (edges_with_domain["size_quintile"] == sq) &
                    (edges_with_domain["liquidity_quintile"] == lq)
                ]
                if len(cell_edges) > 0:
                    same_domain_ratio = float(cell_edges["same_domain"].mean())
                    mean_score = float(cell_edges["score"].mean())
                    cross_stats.append({
                        "size_q": sq,
                        "liq_q": lq,
                        "count": len(cell_edges),
                        "same_domain_ratio": round(same_domain_ratio, 4),
                        "mean_score": round(mean_score, 4),
                    })
        cross_df = pd.DataFrame(cross_stats)
        print("\n规模×流动性交叉统计 (前10行):")
        print(cross_df.head(10).to_string(index=False))

    print("\n[Step 6] 保存结果...")
    edges_with_domain.to_parquet(baselines_cache / "edges_with_domain.parquet", index=False)
    print(f"[OK] edges_with_domain.parquet 已保存")

    summary = {
        "total_edges": int(len(edges_with_domain)),
        "size_quintile_stats": size_df.to_dict(orient="records") if "size_quintile" in edges_with_domain.columns else [],
        "liquidity_quintile_stats": liq_df.to_dict(orient="records") if "liquidity_quintile" in edges_with_domain.columns else [],
        "rank_band_domain_ratio": rank_band_domain_stats.to_dict(orient="records") if "rank_band" in edges_with_domain.columns else [],
    }

    summary_path = baselines_cache / "domain_neighbor_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] domain_neighbor_summary.json 已保存")

    size_df.to_csv(output_dir / "domain_size_stats.csv", index=False) if "size_quintile" in edges_with_domain.columns else None
    liq_df.to_csv(output_dir / "domain_liquidity_stats.csv", index=False) if "liquidity_quintile" in edges_with_domain.columns else None
    print(f"[OK] CSV 报告已保存")

    manifest = {
        "task_id": "T2.5",
        "task_name": "Domain neighbor analysis",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [str(edges_path), str(profile_path)],
        "outputs": [
            str(baselines_cache / "edges_with_domain.parquet"),
            str(summary_path),
        ],
        "parameters": {},
        "warnings": [],
        "error": None,
    }

    with open(manifests_dir / "t25_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.5 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()