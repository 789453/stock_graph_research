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
    parser = argparse.ArgumentParser(description="T2.5: 域内与跨域邻居分析")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.5: 域内与跨域邻居分析")
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

    phase2_cache = cache_dir / "phase2"
    baselines_cache = phase2_cache / "baselines"
    baselines_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = Path(config["plots"]["output_dir"]).parent / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在，请先运行 T2.1")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    
    profile_path = baselines_cache / "node_size_liquidity_profile.parquet"
    if profile_path.exists():
        profile = pd.read_parquet(profile_path)
        print(f"[OK] 加载节点画像: {len(profile)} nodes")
    else:
        print("[WARN] 节点画像不存在，跳过规模/流动性分析")
        profile = pd.DataFrame(columns=["node_id", "size_bucket", "liquidity_bucket"])

    # 加载行业数据
    sw_member_path = Path(config["market"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        nodes = nodes.merge(sw_member[["ts_code", "l1_name", "l2_name", "l3_name"]], left_on="stock_code", right_on="ts_code", how="left")

    print("\n[Step 1] 合并规模/流动性与行业信息...")
    edges_full = edges.merge(
        nodes[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
    ).merge(
        nodes[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("_src", "_dst")
    )
    
    edges_full = edges_full.merge(
        profile[["node_id", "size_bucket", "liquidity_bucket"]],
        left_on="src_node_id",
        right_on="node_id",
        how="left",
    ).merge(
        profile[["node_id", "size_bucket", "liquidity_bucket"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("_src", "_dst")
    )

    print("\n[Step 2] 标记边类型 (Edge Type Labeling)...")
    
    # 定义边类型标签
    def label_edge_type(row):
        labels = []
        # 行业维度
        if row["l3_name_src"] == row["l3_name_dst"] and pd.notna(row["l3_name_src"]):
            labels.append("same_l3_peer")
        elif row["l1_name_src"] == row["l1_name_dst"] and pd.notna(row["l1_name_src"]):
            labels.append("same_l1_cross_l3")
        else:
            labels.append("cross_l1")
            if row["score"] > 0.8:
                labels.append("cross_l1_high_score")
        
        # 规模与流动性维度
        if row["size_bucket_src"] == row["size_bucket_dst"] and row["size_bucket_src"] != -1:
            labels.append("size_similar")
        else:
            labels.append("size_different")
            
        if row["liquidity_bucket_src"] == row["liquidity_bucket_dst"] and row["liquidity_bucket_src"] != -1:
            labels.append("liquidity_similar")
        else:
            labels.append("liquidity_different")
            
        # 特殊标记
        if row["score"] >= 0.98:
            labels.append("potential_template_duplicate")
        
        if row["is_mutual"]:
            labels.append("mutual")
            
        return "|".join(labels)

    edges_full["edge_types"] = edges_full.apply(label_edge_type, axis=1)

    print("\n[Step 3] 统计边类型分布...")
    type_stats = edges_full.groupby("edge_types")["score"].agg(["count", "mean", "std"]).sort_values("count", ascending=False)
    print(type_stats.head(20))

    print("\n[Step 4] 保存结果...")
    edges_full.to_parquet(baselines_cache / "edges_with_domain_and_labels.parquet", index=False)
    print(f"[OK] edges_with_domain_and_labels.parquet 已保存")

    summary = {
        "total_edges": int(len(edges_full)),
        "top_edge_types": type_stats.head(50).to_dict(),
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "11_domain_neighbor_analysis.py",
    }

    summary_path = baselines_cache / "domain_neighbor_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    manifest = {
        "task_id": "T2.5",
        "task_name": "Domain neighbor analysis",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "summary": summary,
    }

    with open(manifests_dir / "t25_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T2.5 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()