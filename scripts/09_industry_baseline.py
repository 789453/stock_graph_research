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

def permutation_test_industry(edges, nodes, level="l3", n_perm=1000):
    """简单的排列检验，计算 p 值"""
    actual_ratio = edges[f"same_{level}"].mean()
    
    # 模拟随机对齐
    perm_ratios = []
    dst_industries = nodes[f"{level}_name"].dropna().values
    n_edges = len(edges)
    
    for _ in range(n_perm):
        # 随机抽取行业标签
        random_dst_industries = np.random.choice(dst_industries, size=n_edges)
        src_industries = edges[f"{level}_name_src"].values
        perm_ratio = np.mean(src_industries == random_dst_industries)
        perm_ratios.append(perm_ratio)
        
    p_value = np.mean(np.array(perm_ratios) >= actual_ratio)
    return float(p_value), float(np.mean(perm_ratios))

def main():
    parser = argparse.ArgumentParser(description="T2.3: 行业 L1/L2/L3 基准")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    parser.add_argument("--n-perm", type=int, default=1000, help="排列检验次数")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.3: 行业 L1/L2/L3 基准")
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
    baselines_cache = cache_dir / "phase2" / "baselines"
    baselines_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = cache_dir / "phase2" / "manifests"
    output_dir = Path(config["plots"]["output_dir"]).parent / "reports" / "phase2"
    output_dir.mkdir(parents=True, exist_ok=True)

    edges_path = phase2_cache / "edge_candidates_k100.parquet"
    if not edges_path.exists():
        print("[FAIL] edge_candidates_k100.parquet 不存在，请先运行 T2.1")
        sys.exit(1)

    edges = pd.read_parquet(edges_path)
    print(f"[OK] 加载候选边池: {len(edges)} edges")

    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    sw_member_path = Path(config["market"]["stock_sw_member_path"])
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
    ).merge(
        nodes_with_industry[["node_id", "l1_name", "l2_name", "l3_name"]],
        left_on="dst_node_id",
        right_on="node_id",
        how="left",
        suffixes=("_src", "_dst")
    )

    print("\n[Step 2] 计算同行业标志...")
    edges_merged["same_l1"] = (edges_merged["l1_name_src"] == edges_merged["l1_name_dst"]) & edges_merged["l1_name_src"].notna()
    edges_merged["same_l2"] = (edges_merged["l2_name_src"] == edges_merged["l2_name_dst"]) & edges_merged["l2_name_src"].notna()
    edges_merged["same_l3"] = (edges_merged["l3_name_src"] == edges_merged["l3_name_dst"]) & edges_merged["l3_name_src"].notna()

    print("\n[Step 3] 计算随机基准与排列检验...")
    n_nodes = len(nodes_with_industry)
    baselines = {}
    for level in ["l1", "l2", "l3"]:
        groups = nodes_with_industry.groupby(f"{level}_name").size()
        random_ratio = sum((c / n_nodes) ** 2 for c in groups) if n_nodes > 0 else 0
        baselines[level] = random_ratio

    print("\n[Step 4] 按 rank_band_exclusive 统计同行业比例与 Lift...")
    band_col = "rank_band_exclusive" if "rank_band_exclusive" in edges_merged.columns else "rank_band"
    
    results = {}
    for band in edges_merged[band_col].unique():
        band_edges = edges_merged[edges_merged[band_col] == band]
        results[band] = {}
        for level in ["l1", "l2", "l3"]:
            ratio = band_edges[f"same_{level}"].mean()
            lift = ratio / baselines[level] if baselines[level] > 0 else 0
            p_val, _ = permutation_test_industry(band_edges, nodes_with_industry, level=level, n_perm=args.n_perm)
            
            results[band][f"{level}_ratio"] = round(float(ratio), 4)
            results[band][f"{level}_lift"] = round(float(lift), 2)
            results[band][f"{level}_p_val"] = p_val

    print(json.dumps(results, indent=2))

    # 保存结果
    edges_merged.to_parquet(baselines_cache / "edges_with_industry.parquet", index=False)
    
    results_path = baselines_cache / "industry_baseline_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "industry_stats": results,
            "random_baseline": baselines,
            "created_at_utc": pd.Timestamp.utcnow().isoformat(),
            "script": "09_industry_baseline.py",
        }, f, indent=2, ensure_ascii=False)

    print(f"[OK] 结果已保存至: {results_path}")

    manifest = {
        "task_id": "T2.3",
        "task_name": "Industry L1/L2/L3 baseline",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "summary": results,
    }

    with open(manifests_dir / "t23_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T2.3 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()