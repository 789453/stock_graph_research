import os
import json
import time
import numpy as np
import pandas as pd
import yaml
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Any, List, Dict
import matplotlib.font_manager as fm

def setup_chinese_font():
    font_candidates = [
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "WenQuanYi Zen Hei",
        "Source Han Sans SC",
        "Microsoft YaHei",
        "SimHei",
    ]
    
    # Try to find font by name
    available = {f.name for f in fm.fontManager.ttflist}
    target_font = None
    for x in font_candidates:
        if x in available:
            target_font = x
            break
            
    # If not found by name, try to find by path
    if not target_font:
        potential_paths = [
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        ]
        for p in potential_paths:
            if os.path.exists(p):
                fe = fm.FontEntry(fname=p, name='CustomChineseFont')
                fm.fontManager.ttflist.insert(0, fe)
                target_font = 'CustomChineseFont'
                break
    
    if target_font:
        plt.rcParams['font.family'] = target_font
        plt.rcParams['axes.unicode_minus'] = False
        print(f"Using font: {target_font}")
    else:
        print("WARNING: No Chinese font found. Plots may have boxes for text.")
        # Final fallback to something that might work
        plt.rcParams['font.family'] = 'DejaVu Sans'

def run_visualization(global_config: dict[str, Any]):
    start_time = time.time()
    print("Starting T2.2.9: Visualization Dashboard...")
    setup_chinese_font()
    
    views = list(global_config["views"].keys())
    multi_view_data = []
    
    out_dir_mv = Path("outputs/plots/phase2_2/multi_view")
    out_dir_mv.mkdir(parents=True, exist_ok=True)
    
    for view_name in views:
        # Locate view data
        view_dir_22 = Path(f"cache/semantic_graph/phase2_2/views/{view_name}")
        manifest_files = list(view_dir_22.glob("*/manifests/view_stat_tests_manifest.json"))
        if not manifest_files: continue
        
        manifest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        view_key = manifest_files[0].parent.parent.name
        
        metrics_dir = view_dir_22 / view_key / "phase2_2/market_behavior"
        stat_dir = view_dir_22 / view_key / "phase2_2/stat_tests"
        sens_dir = view_dir_22 / view_key / "phase2_2/hub_bridge"
        
        test_results = pd.read_csv(stat_dir / "h5_metric_tests.csv")
        test_results["view"] = view_name
        multi_view_data.append(test_results)
        
    if not multi_view_data:
        print("No data found for visualization.")
        return
        
    df_all = pd.concat(multi_view_data)
    
    # Plot 1: Residual Correlation Comparison (Semantic vs Global Random)
    print("Generating residual correlation comparison plot...")
    plt.figure(figsize=(12, 6))
    subset = df_all[df_all["baseline_type"] == "global_random"]
    sns.barplot(data=subset, x="rank_layer", y="delta_mean", hue="view")
    plt.title("语义边超额残差收益相关 (vs 全局随机)")
    plt.ylabel("Delta Mean Correlation")
    plt.xlabel("Rank Band")
    plt.axhline(0, color='black', linestyle='--')
    
    plot_name = "residual_corr_delta_by_view"
    plt.savefig(out_dir_mv / f"{plot_name}.png", dpi=160, bbox_inches='tight')
    subset.to_csv(out_dir_mv / f"{plot_name}.csv", index=False)
    with open(out_dir_mv / f"{plot_name}.json", "w") as f:
        json.dump({
            "title": "语义边超额残差收益相关",
            "question": "在控制全市场收益后，语义边是否比随机边具有更高的收益相关性？",
            "key_reading": "柱状图高于0表示语义边具有增量信息。"
        }, f, indent=2, ensure_ascii=False)
    plt.close()
    
    # Plot 2: Z-Score Significance
    print("Generating Z-score significance plot...")
    plt.figure(figsize=(12, 6))
    sns.lineplot(data=subset, x="rank_layer", y="z_score", hue="view", marker='o')
    plt.title("语义边显著性 Z-Score (vs 全局随机)")
    plt.ylabel("Z-Score")
    plt.axhline(1.96, color='red', linestyle='--', label='95% Significance (1.96)')
    plt.legend()
    
    plot_name = "z_score_significance_by_view"
    plt.savefig(out_dir_mv / f"{plot_name}.png", dpi=160, bbox_inches='tight')
    plt.close()
    
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.9",
        "task_name": "visualization_dashboard",
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "outputs": [str(out_dir_mv / "residual_corr_delta_by_view.png")],
        "safe_to_continue": True
    }
    
    master_dir = Path("cache/semantic_graph/phase2_2/manifests")
    master_dir.mkdir(parents=True, exist_ok=True)
    with open(master_dir / "T2_2_9_viz_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    run_visualization(config)

if __name__ == "__main__":
    main()
