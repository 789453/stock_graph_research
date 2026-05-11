import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.cache_io import read_cache_manifest

def main():
    parser = argparse.ArgumentParser(description="T2.2: 边层统计与真实分数分布")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.2: 边层统计与真实分数分布")
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
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = Path(config["plots"]["output_dir"]).parent / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    edges_path = phase2_cache / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在，请先运行 T2.1")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    # 加载节点和行业信息
    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    sw_member_path = Path(config["market"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        nodes = nodes.merge(sw_member[["ts_code", "l1_name", "l2_name", "l3_name"]], left_on="stock_code", right_on="ts_code", how="left")
    
    # 关联行业
    edges = edges.merge(nodes[["node_id", "l1_name", "l2_name", "l3_name"]], left_on="src_node_id", right_on="node_id", how="left").merge(
        nodes[["node_id", "l1_name", "l2_name", "l3_name"]], left_on="dst_node_id", right_on="node_id", how="left", suffixes=("_src", "_dst")
    )
    
    edges["same_l1"] = (edges["l1_name_src"] == edges["l1_name_dst"]) & edges["l1_name_src"].notna()
    edges["same_l2"] = (edges["l2_name_src"] == edges["l2_name_dst"]) & edges["l2_name_src"].notna()
    edges["same_l3"] = (edges["l3_name_src"] == edges["l3_name_dst"]) & edges["l3_name_src"].notna()

    print("\n[Step 1] 按 rank_band_exclusive 统计...")
    # 确保列名正确
    band_col = "rank_band_exclusive" if "rank_band_exclusive" in edges.columns else "rank_band"
    
    agg_dict = {
        "score": ["count", "mean", "median", "std"],
        "is_mutual": "mean",
        "same_l1": "mean",
        "same_l2": "mean",
        "same_l3": "mean"
    }
    
    rank_band_stats = edges.groupby(band_col).agg(agg_dict).round(4)
    print(rank_band_stats)

    print("\n[Step 2] 按 cumulative topK 统计...")
    cumulative_stats = []
    for k in [5, 10, 20, 50, 100]:
        mask = edges["rank"] <= k
        subset = edges[mask]
        stats = {
            "topK": f"top_{k:03d}",
            "count": len(subset),
            "score_mean": subset["score"].mean(),
            "mutual_ratio": subset["is_mutual"].mean(),
            "same_l1_ratio": subset["same_l1"].mean(),
            "same_l3_ratio": subset["same_l3"].mean(),
        }
        cumulative_stats.append(stats)
    
    cumulative_df = pd.DataFrame(cumulative_stats).set_index("topK").round(4)
    print(cumulative_df)

    # 保存报告
    report_path = output_dir / "edge_layer_statistics.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Edge Layer Statistics\n\n")
        f.write(f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Exclusive Rank Band Stats\n\n")
        f.write(rank_band_stats.to_markdown() + "\n\n")
        f.write("## Cumulative TopK Stats\n\n")
        f.write(cumulative_df.to_markdown() + "\n\n")
    print(f"[OK] 统计报告已保存: {report_path}")

    print("\n[Step 3] 生成综合摘要...")
    summary = {
        "total_edges": int(len(edges)),
        "total_nodes": int(edges["src_node_id"].nunique()),
        "mutual_ratio": round(float(edges["is_mutual"].mean()), 4),
        "score_global_mean": round(float(edges["score"].mean()), 4),
        "rank_band_stats": rank_band_stats.to_dict(),
        "cumulative_stats": cumulative_df.to_dict(),
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "08_edge_layer_statistics.py",
    }

    summary_path = phase2_cache / "edge_layer_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"[OK] 边层摘要已保存: {summary_path}")

    manifest = {
        "task_id": "T2.2",
        "task_name": "Edge layer statistics",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "summary": summary,
    }

    with open(manifests_dir / "t22_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存")

    print("\n" + "=" * 60)
    print("T2.2 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()