#!/usr/bin/env python3
"""
T2.2: 边层统计与真实分数分布
计算每个 rank band 的分数统计，生成报告
"""
import sys
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def main():
    project_root = Path(__file__).parent.parent
    cache_dir = project_root / "cache" / "semantic_graph" / "2eebde04e582"
    phase2_cache = cache_dir / "phase2" / "edge_layers"
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = project_root / "outputs" / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.2: 边层统计与真实分数分布")
    print("=" * 60)

    import pandas as pd

    edges_path = phase2_cache / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在，请先运行 T2.1")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    print("\n[Step 1] 按 rank_band 统计...")
    rank_band_stats = edges.groupby("rank_band").agg(
        count=("score", "count"),
        mean=("score", "mean"),
        median=("score", "median"),
        std=("score", "std"),
        min=("score", "min"),
        max=("score", "max"),
        p25=("score", lambda x: x.quantile(0.25)),
        p75=("score", lambda x: x.quantile(0.75)),
        p90=("score", lambda x: x.quantile(0.90)),
        p95=("score", lambda x: x.quantile(0.95)),
    ).round(4)
    print(rank_band_stats)

    rank_band_stats_path = output_dir / "edge_layer_rank_band_stats.md"
    with open(rank_band_stats_path, "w", encoding="utf-8") as f:
        f.write("# Edge Layer Statistics by Rank Band\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Score Distribution\n\n")
        f.write(rank_band_stats.to_string() + "\n\n")
    print(f"[OK] 统计报告已保存: {rank_band_stats_path}")

    print("\n[Step 2] 按 rank 统计...")
    rank_stats = edges.groupby("rank").agg(
        count=("score", "count"),
        mean=("score", "mean"),
        median=("score", "median"),
        std=("score", "std"),
    ).round(4)
    print(rank_stats.head(20))

    rank_stats_path = output_dir / "edge_layer_rank_stats.md"
    with open(rank_stats_path, "w", encoding="utf-8") as f:
        f.write("# Edge Statistics by Rank\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Score by Rank (1-100)\n\n")
        f.write(rank_stats.head(100).to_string() + "\n\n")
    print(f"[OK] Rank 统计已保存: {rank_stats_path}")

    print("\n[Step 3] Mutual vs Non-mutual 统计...")
    mutual_stats = edges.groupby("is_mutual").agg(
        count=("score", "count"),
        mean=("score", "mean"),
        median=("score", "median"),
        std=("score", "std"),
    ).round(4)
    print(mutual_stats)

    print("\n[Step 4] 按 score_quantile 统计...")
    quantile_cols = [c for c in edges.columns if c.startswith("score_quantile_")]
    quantile_stats = {}
    for col in quantile_cols:
        q_name = col.replace("score_quantile_", "p")
        count = edges[col].sum()
        mean_score = edges[edges[col] == True]["score"].mean() if count > 0 else 0
        quantile_stats[q_name] = {"count": int(count), "mean_score_if_selected": float(round(mean_score, 4))}
    print(json.dumps(quantile_stats, indent=2))

    print("\n[Step 5] 生成综合摘要...")
    summary = {
        "total_edges": int(len(edges)),
        "total_nodes": int(edges["src_node_id"].nunique()),
        "mutual_edge_count": int(edges["is_mutual"].sum()),
        "mutual_ratio": round(float(edges["is_mutual"].mean()), 4),
        "rank_band_distribution": {
            band: int(count) for band, count in edges["rank_band"].value_counts().items()
        },
        "score_global_mean": round(float(edges["score"].mean()), 4),
        "score_global_std": round(float(edges["score"].std()), 4),
        "score_global_min": round(float(edges["score"].min()), 4),
        "score_global_max": round(float(edges["score"].max()), 4),
        "rank_band_stats": rank_band_stats.to_dict(),
        "quantile_stats": quantile_stats,
    }

    summary_path = phase2_cache / "edge_layer_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] 边层摘要已保存: {summary_path}")

    manifest = {
        "task_id": "T2.2",
        "task_name": "Edge layer statistics",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [str(edges_path)],
        "outputs": [
            str(rank_band_stats_path),
            str(rank_stats_path),
            str(summary_path),
        ],
        "parameters": {},
        "warnings": [],
        "error": None,
    }

    with open(manifests_dir / "t22_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.2 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()