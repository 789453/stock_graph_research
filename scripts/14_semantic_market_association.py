#!/usr/bin/env python3
"""
T2.8: 语义边与市场行为关联分析
分析 semantic edge layers 是否与市场行为共振相关
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
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = project_root / "outputs" / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("T2.8: 语义边与市场行为关联分析")
    print("=" * 60)

    import pandas as pd
    import numpy as np

    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    market_panel_path = phase2_cache / "market_behavior" / "node_market_panel_2018_2026.parquet"
    if not market_panel_path.exists():
        print("[FAIL] node_market_panel 不存在，请先运行 T2.7")
        sys.exit(1)

    market_panel = pd.read_parquet(market_panel_path)
    print(f"[OK] 加载市场面板: {len(market_panel)} nodes")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    print(f"[OK] 加载节点表: {len(nodes)} nodes")

    print("\n[Step 1] 合并市场行为到边表...")
    edges_with_market = edges.merge(
        market_panel[["node_id", "avg_annual_return", "avg_volatility", "avg_mean_amount"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_src"),
    )
    edges_with_market = edges_with_market.merge(
        market_panel[["node_id", "avg_annual_return", "avg_volatility", "avg_mean_amount"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("", "_dst"),
    )

    print("\n[Step 2] 计算边对的市场行为差异...")
    edges_with_market["return_diff"] = abs(
        edges_with_market["avg_annual_return"] - edges_with_market["avg_annual_return_dst"]
    )
    edges_with_market["vol_diff"] = abs(
        edges_with_market["avg_volatility"] - edges_with_market["avg_volatility_dst"]
    )

    print("\n[Step 3] 按 rank_band 分析市场行为差异...")
    rank_band_behavior = []
    for band in ["core", "strong", "stable", "context", "extended"]:
        band_edges = edges_with_market[edges_with_market["rank_band"] == band]
        if len(band_edges) == 0:
            continue
        valid_return = band_edges["return_diff"].dropna()
        valid_vol = band_edges["vol_diff"].dropna()
        rank_band_behavior.append({
            "rank_band": band,
            "count": len(band_edges),
            "return_diff_mean": round(float(valid_return.mean()), 4) if len(valid_return) > 0 else np.nan,
            "return_diff_std": round(float(valid_return.std()), 4) if len(valid_return) > 0 else np.nan,
            "vol_diff_mean": round(float(valid_vol.mean()), 4) if len(valid_vol) > 0 else np.nan,
            "vol_diff_std": round(float(valid_vol.std()), 4) if len(valid_vol) > 0 else np.nan,
        })

    rank_band_df = pd.DataFrame(rank_band_behavior)
    print("\n按 rank_band 的市场行为差异:")
    print(rank_band_df.to_string(index=False))

    print("\n[Step 4] 计算分数与市场行为差异的相关性...")
    k20_edges = edges_with_market[edges_with_market["rank"] <= 20]
    k20_edges_valid = k20_edges.dropna(subset=["score", "return_diff", "vol_diff"])

    if len(k20_edges_valid) > 100:
        score_return_corr = float(k20_edges_valid["score"].corr(k20_edges_valid["return_diff"]))
        score_vol_corr = float(k20_edges_valid["score"].corr(k20_edges_valid["vol_diff"]))
        print(f"\n分数 vs 收益差异相关性 (k<=20): {score_return_corr:.4f}")
        print(f"分数 vs 波动率差异相关性 (k<=20): {score_vol_corr:.4f}")
    else:
        score_return_corr = np.nan
        score_vol_corr = np.nan
        print("\n数据不足，跳过相关性计算")

    print("\n[Step 5] 对比同行业 vs 跨行业边的市场行为差异...")
    if "same_l1" in edges_with_market.columns:
        same_industry = edges_with_market[edges_with_market["same_l1"] == True]["return_diff"].dropna()
        cross_industry = edges_with_market[edges_with_market["same_l1"] == False]["return_diff"].dropna()

        industry_comparison = {
            "same_industry_return_diff_mean": round(float(same_industry.mean()), 4) if len(same_industry) > 0 else np.nan,
            "cross_industry_return_diff_mean": round(float(cross_industry.mean()), 4) if len(cross_industry) > 0 else np.nan,
            "same_industry_count": int(len(same_industry)),
            "cross_industry_count": int(len(cross_industry)),
        }
        print("\n同行业 vs 跨行业收益差异:")
        print(json.dumps(industry_comparison, indent=2))
    else:
        industry_comparison = {}

    print("\n[Step 6] Hub vs 非 Hub 节点的市场行为差异...")
    hub_labels_path = phase2_cache / "hub_bridge" / "node_hub_bridge_labels.parquet"
    if hub_labels_path.exists():
        hub_labels = pd.read_parquet(hub_labels_path)
        market_with_hub = market_panel.merge(
            hub_labels[["node_id", "is_hub_k100"]],
            on="node_id",
            how="left",
        )
        hub_market = market_with_hub[market_with_hub["is_hub_k100"] == True]
        non_hub_market = market_with_hub[market_with_hub["is_hub_k100"] != True]

        hub_comparison = {
            "hub_avg_return_mean": round(float(hub_market["avg_annual_return"].mean()), 4) if len(hub_market) > 0 else np.nan,
            "hub_avg_return_std": round(float(hub_market["avg_annual_return"].std()), 4) if len(hub_market) > 0 else np.nan,
            "non_hub_avg_return_mean": round(float(non_hub_market["avg_annual_return"].mean()), 4) if len(non_hub_market) > 0 else np.nan,
            "non_hub_avg_return_std": round(float(non_hub_market["avg_annual_return"].std()), 4) if len(non_hub_market) > 0 else np.nan,
            "hub_count": int(len(hub_market)),
            "non_hub_count": int(len(non_hub_market)),
        }
        print("\nHub vs 非 Hub 市场行为:")
        print(json.dumps(hub_comparison, indent=2))
    else:
        hub_comparison = {}

    print("\n[Step 7] 保存结果...")
    edges_with_market.to_parquet(output_dir / "edges_with_market_behavior.parquet", index=False)
    print(f"[OK] edges_with_market_behavior.parquet 已保存")

    summary = {
        "total_edges_analyzed": int(len(edges_with_market)),
        "rank_band_behavior": rank_band_df.to_dict(orient="records"),
        "score_return_corr_k20": round(float(score_return_corr), 4) if not np.isnan(score_return_corr) else None,
        "score_vol_corr_k20": round(float(score_vol_corr), 4) if not np.isnan(score_vol_corr) else None,
        "industry_comparison": industry_comparison,
        "hub_comparison": hub_comparison,
    }

    summary_path = output_dir / "semantic_market_association_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] semantic_market_association_summary.json 已保存")

    rank_band_df.to_csv(output_dir / "rank_band_market_behavior.csv", index=False)
    print(f"[OK] rank_band_market_behavior.csv 已保存")

    manifest = {
        "task_id": "T2.8",
        "task_name": "Semantic edge and market behavior association",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "inputs": [str(edges_path), str(market_panel_path)],
        "outputs": [
            str(output_dir / "edges_with_market_behavior.parquet"),
            str(summary_path),
            str(output_dir / "rank_band_market_behavior.csv"),
        ],
        "parameters": {},
        "warnings": [],
        "error": None,
    }

    with open(manifests_dir / "t28_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.8 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()