#!/usr/bin/env python3
"""
T2.8: 语义边与市场行为关联分析 (Refactored)
分析语义边是否具有市场共振效应 (H5 市场共振假设)。
包含月度残差矩阵构建、边级相关性计算和匹配随机基准。
严格遵循 Node Order Safety 和 Phase 2.3 规范。
"""
import sys
import json
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config
from semantic_graph_research.phase2_graph_layers import prepare_nodes_index

def main():
    parser = argparse.ArgumentParser(description="T2.8: 语义边与市场行为关联分析")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.8: 语义边与市场行为关联分析 (Refactored)")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path("cache") / "semantic_graph"
    if args.cache_key:
        cache_dir = cache_root / args.cache_key
    else:
        # 尝试从 config 中获取
        cache_dir_str = config.get("paths", {}).get("semantic_graph_cache")
        if cache_dir_str:
            cache_dir = Path(cache_dir_str)
        else:
            cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
            if not cache_dirs:
                print("[FAIL] 未找到缓存")
                sys.exit(1)
            cache_dir = sorted(cache_dirs)[-1]

    phase2_cache = cache_dir / "phase2"
    market_behavior_cache = phase2_cache / "market_behavior"
    resonance_cache = phase2_cache / "resonance"
    resonance_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = phase2_cache / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    # 1. 加载数据
    nodes = pd.read_parquet(cache_dir / "nodes.parquet")
    nodes = prepare_nodes_index(nodes, len(nodes))
    
    # 加载行业数据
    sw_member_path = Path(config["paths"]["stock_sw_member_path"])
    if sw_member_path.exists():
        sw_member = pd.read_parquet(sw_member_path)
        nodes = nodes.merge(sw_member[["ts_code", "l1_name", "l3_name"]], 
                          left_on="stock_code", right_on="ts_code", how="left")
    
    monthly_panel_path = market_behavior_cache / "node_monthly_panel_2018_2026.parquet"
    if not monthly_panel_path.exists():
        print(f"[FAIL] {monthly_panel_path} 不存在，请先运行 T2.7")
        sys.exit(1)
    panel = pd.read_parquet(monthly_panel_path)
    
    edges_path = phase2_cache / "edge_layers" / "edge_candidates_k100.parquet"
    edges = pd.read_parquet(edges_path)

    print(f"[OK] 加载 {len(nodes)} 节点, {len(edges)} 边, {len(panel)} 面板记录")

    # 2. 计算残差收益率 (Residual Returns)
    # Residual = Monthly_Return - Industry_L1_Mean_Return
    print("\n[Step 1] 计算月度残差收益率 (Stripping Industry L1 Effect)...")
    
    # 合并行业信息到面板
    panel = panel.merge(nodes[["node_id", "l1_name"]], on="node_id", how="left")
    
    # 计算月度行业均值
    industry_means = panel.groupby(["month", "l1_name"])["monthly_return"].mean().reset_index().rename(columns={"monthly_return": "l1_mean_return"})
    
    panel = panel.merge(industry_means, on=["month", "l1_name"], how="left")
    panel["residual_return"] = panel["monthly_return"] - panel["l1_mean_return"].fillna(0)
    
    # 3. 构建残差矩阵 (Node Order Safety)
    print("[Step 2] 构建残差矩阵 (Rows Aligned with node_id)...")
    all_months = sorted(panel["month"].unique())
    month_to_idx = {m: i for i, m in enumerate(all_months)}
    n_nodes = len(nodes)
    n_months = len(all_months)
    
    res_matrix = np.full((n_nodes, n_months), np.nan, dtype=np.float32)
    
    # 填充矩阵
    row_indices = panel["node_id"].values
    col_indices = panel["month"].map(month_to_idx).values
    res_matrix[row_indices, col_indices] = panel["residual_return"].values
    
    # 保存矩阵及 Manifest
    np.save(resonance_cache / "matrix_ret_resid_l1.npy", res_matrix)
    matrix_manifest = {
        "row_order": "node_id",
        "col_order": "month",
        "months": all_months,
        "shape": res_matrix.shape,
        "created_at": datetime.now().isoformat()
    }
    with open(resonance_cache / "matrix_manifest.json", "w") as f:
        json.dump(matrix_manifest, f, indent=2)

    # 4. 生成匹配随机边 (Matched Random Baseline)
    print("[Step 3] 生成匹配随机基准 (Matched by L1 Industry)...")
    np.random.seed(42)
    
    # 为每条语义边生成一条匹配随机边
    # 策略：保持 src 不变，在 dst 相同的 L1 行业内随机抽取一个 dst'
    def generate_matched_random(edges_df, nodes_df):
        matched_edges = []
        l1_groups = {l1: group["node_id"].values for l1, group in nodes_df.groupby("l1_name")}
        
        # 预先获取每个节点的行业
        node_to_l1 = nodes_df.set_index("node_id")["l1_name"].to_dict()
        
        for _, row in tqdm(edges_df.iterrows(), total=len(edges_df), desc="Generating matched edges"):
            src_id = int(row["src_node_id"])
            dst_id = int(row["dst_node_id"])
            dst_l1 = node_to_l1.get(dst_id, "UNKNOWN")
            
            if dst_l1 in l1_groups:
                candidates = l1_groups[dst_l1]
                # 排除自己和原 dst
                candidates = candidates[(candidates != src_id) & (candidates != dst_id)]
                if len(candidates) > 0:
                    random_dst = np.random.choice(candidates)
                else:
                    # 退而求其次，全局随机
                    random_dst = np.random.choice(nodes_df["node_id"].values)
            else:
                random_dst = np.random.choice(nodes_df["node_id"].values)
            
            matched_edges.append({
                "src_node_id": src_id,
                "dst_node_id": random_dst,
                "is_matched_random": True
            })
        return pd.DataFrame(matched_edges)

    # 为了提速，只对 k<=20 的边做详细分析
    edges_k20 = edges[edges["rank"] <= 20].copy()
    matched_edges_k20 = generate_matched_random(edges_k20, nodes)

    # 5. 计算边级共振 (Correlation)
    print("[Step 4] 计算边级残差相关性 (H5 Resonance)...")
    
    def compute_edge_corrs(edges_df, matrix):
        corrs = []
        for _, row in tqdm(edges_df.iterrows(), total=len(edges_df), desc="Computing correlations"):
            u = int(row["src_node_id"])
            v = int(row["dst_node_id"])
            
            vec_u = matrix[u]
            vec_v = matrix[v]
            
            # 过滤 NaN
            mask = np.isfinite(vec_u) & np.isfinite(vec_v)
            if mask.sum() >= 12: # 至少12个月的数据
                corr = np.corrcoef(vec_u[mask], vec_v[mask])[0, 1]
            else:
                corr = np.nan
            corrs.append(corr)
        return np.array(corrs)

    edges_k20["resonance_corr"] = compute_edge_corrs(edges_k20, res_matrix)
    matched_edges_k20["resonance_corr"] = compute_edge_corrs(matched_edges_k20, res_matrix)

    # 6. 统计显著性分析
    print("\n[Step 5] 统计显著性分析 (Semantic vs Matched Random)...")
    semantic_mean = edges_k20["resonance_corr"].dropna().mean()
    random_mean = matched_edges_k20["resonance_corr"].dropna().mean()
    lift = semantic_mean - random_mean
    
    # 简单的 Permutation Test 思想: 观察到的差值是否显著
    # 这里使用简单的均值对比和 T-检验作为初步参考 (严格应使用 Bootstrap)
    from scipy import stats
    t_stat, p_val = stats.ttest_ind(edges_k20["resonance_corr"].dropna(), 
                                   matched_edges_k20["resonance_corr"].dropna(), 
                                   equal_var=False)

    print(f"语义边平均相关性 (k<=20): {semantic_mean:.4f}")
    print(f"匹配随机边平均相关性: {random_mean:.4f}")
    print(f"超额共振 (Lift): {lift:.4f}")
    print(f"T-stat: {t_stat:.4f}, P-value: {p_val:.4g}")

    # 7. 保存结果
    print("\n[Step 6] 保存研究产物...")
    edges_k20.to_parquet(resonance_cache / "edge_resonance_metrics_k20.parquet", index=False)
    matched_edges_k20.to_parquet(resonance_cache / "matched_random_resonance_k20.parquet", index=False)
    
    summary = {
        "semantic_mean_corr": float(semantic_mean),
        "random_mean_corr": float(random_mean),
        "lift": float(lift),
        "t_stat": float(t_stat),
        "p_value": float(p_val),
        "n_edges": len(edges_k20),
        "min_valid_months": 12,
        "h5_status": "SUPPORTED" if p_val < 0.01 and lift > 0 else "PARTIALLY_SUPPORTED" if p_val < 0.05 else "REJECTED"
    }
    
    with open(resonance_cache / "resonance_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    manifest = {
        "task_id": "T2.8",
        "task_name": "Semantic market association and H5 resonance",
        "cache_key": cache_dir.name,
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success",
        "outputs": {
            "resonance_metrics": str(resonance_cache / "edge_resonance_metrics_k20.parquet"),
            "residual_matrix": str(resonance_cache / "matrix_ret_resid_l1.npy"),
            "summary": str(resonance_cache / "resonance_summary.json")
        },
        "node_order_safety": "node_id_contiguous"
    }

    with open(manifests_dir / "t28_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("T2.8 完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
