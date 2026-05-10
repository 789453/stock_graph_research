#!/usr/bin/env python3
"""
T2.3: 行业 L1/L2/L3 基准
计算每个 rank band 的同行业比例，与随机基准对比
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
    baselines_cache = cache_dir / "phase2" / "baselines"
    baselines_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = project_root / "outputs" / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.3: 行业 L1/L2/L3 基准")
    print("=" * 60)

    import pandas as pd
    import numpy as np

    edges_path = phase2_cache / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在，请先运行 T2.1")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    sw_member_path = Path("/mnt/d/Trading/data_ever_26_3_14/data/silver/stock_sw_member.parquet")
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        print(f"[OK] 申万数据: {len(sw_member)} records")
    else:
        print("[WARN] 申万数据不存在，使用空行业标签")
        sw_member = pd.DataFrame(columns=["ts_code", "l1_name", "l2_name", "l3_name"])

    print("\n[Step 1] 合并行业信息...")
    nodes_with_industry = nodes.merge(
        sw_member[["ts_code", "l1_name", "l2_name", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )

    edges_merged = edges.merge(
        nodes_with_industry[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_src"),
    )
    edges_merged = edges_merged.merge(
        nodes_with_industry[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_dst"),
    )

    print("\n[Step 2] 计算同行业标志...")
    edges_merged["same_l1"] = (edges_merged["l1_name"] == edges_merged["l1_name_dst"]) & edges_merged["l1_name"].notna()
    edges_merged["same_l2"] = (edges_merged["l2_name"] == edges_merged["l2_name_dst"]) & edges_merged["l2_name"].notna()
    edges_merged["same_l3"] = (edges_merged["l3_name"] == edges_merged["l3_name_dst"]) & edges_merged["l3_name"].notna()

    print("\n[Step 3] 按 rank_band 和行业层统计...")
    rank_bands = ["core", "strong", "stable", "context", "extended"]
    industry_levels = ["l1", "l2", "l3"]

    results = {}
    for band in rank_bands:
        band_edges = edges_merged[edges_merged["rank_band"] == band]
        if len(band_edges) == 0:
            continue
        results[band] = {}
        for level in industry_levels:
            same_key = f"same_{level}"
            if same_key in band_edges.columns:
                same_ratio = float(band_edges[same_key].mean())
                total = len(band_edges)
                same_count = int(band_edges[same_key].sum())
                results[band][f"{level}_same_ratio"] = round(same_ratio, 4)
                results[band][f"{level}_same_count"] = same_count
                results[band][f"{level}_total"] = total

    print("\n按 rank_band 的同行业比例:")
    print(json.dumps(results, indent=2))

    print("\n[Step 4] 按 rank 统计同行业比例...")
    rank_industry_stats = []
    for rank in [1, 5, 10, 20, 50, 100]:
        rank_edges = edges_merged[edges_merged["rank"] == rank]
        if len(rank_edges) == 0:
            continue
        row = {"rank": rank, "count": len(rank_edges)}
        for level in industry_levels:
            same_key = f"same_{level}"
            if same_key in rank_edges.columns:
                row[f"{level}_same_ratio"] = round(float(rank_edges[same_key].mean()), 4)
        rank_industry_stats.append(row)

    rank_df = pd.DataFrame(rank_industry_stats)
    print(rank_df.to_string(index=False))

    print("\n[Step 5] 计算随机基准...")
    n_nodes = len(nodes_with_industry)
    l1_groups = nodes_with_industry.groupby("l1_name").size()
    l2_groups = nodes_with_industry.groupby("l2_name").size()
    l3_groups = nodes_with_industry.groupby("l3_name").size()

    random_l1 = sum((c / n_nodes) ** 2 for c in l1_groups) if len(l1_groups) > 0 else 0
    random_l2 = sum((c / n_nodes) ** 2 for c in l2_groups) if len(l2_groups) > 0 else 0
    random_l3 = sum((c / n_nodes) ** 2 for c in l3_groups) if len(l3_groups) > 0 else 0

    print(f"\n随机基准（同行业概率）:")
    print(f"  L1: {random_l1:.4f}")
    print(f"  L2: {random_l2:.4f}")
    print(f"  L3: {random_l3:.4f}")

    print("\n[Step 6] 计算 lift（相对于随机的倍数）...")
    for band in results:
        for level in industry_levels:
            same_ratio = results[band].get(f"{level}_same_ratio", 0)
            random基准 = {"l1": random_l1, "l2": random_l2, "l3": random_l3}.get(level, 0)
            if random基准 > 0:
                results[band][f"{level}_lift"] = round(same_ratio / random基准, 2)
            else:
                results[band][f"{level}_lift"] = None

    print("\n带 lift 的统计:")
    print(json.dumps(results, indent=2))

    print("\n[Step 7] 保存结果...")
    edges_merged.to_parquet(baselines_cache / "edges_with_industry.parquet", index=False)
    print(f"[OK] edges_with_industry.parquet 已保存")

    results_path = baselines_cache / "industry_baseline_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "rank_band_industry_stats": results,
            "rank_industry_stats": rank_df.to_dict(orient="records"),
            "random_baseline": {
                "l1": round(float(random_l1), 4),
                "l2": round(float(random_l2), 4),
                "l3": round(float(random_l3), 4),
            },
            "note": "当前申万行业标签，仅供参考（非历史真值）",
        }, f, indent=2, ensure_ascii=False)
    print(f"[OK] industry_baseline_results.json 已保存")

    rank_df.to_csv(output_dir / "industry_baseline_by_rank.csv", index=False)
    print(f"[OK] industry_baseline_by_rank.csv 已保存")

    manifest = {
        "task_id": "T2.3",
        "task_name": "Industry L1/L2/L3 baseline",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [str(edges_path), str(sw_member_path)],
        "outputs": [
            str(baselines_cache / "edges_with_industry.parquet"),
            str(results_path),
            str(output_dir / "industry_baseline_by_rank.csv"),
        ],
        "parameters": {},
        "warnings": ["当前申万行业标签，仅供参考（非历史真值）"],
        "error": None,
    }

    with open(manifests_dir / "t23_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.3 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()