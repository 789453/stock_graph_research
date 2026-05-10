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

# ==================== 0. 中文可视化配置 ====================

def setup_chinese_font():
    """严格遵循 temp_plot1.py 的字体配置逻辑"""
    font_candidates = [
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
        "WenQuanYi Zen Hei",
        "Source Han Sans SC",
        "Microsoft YaHei",
        "SimHei",
    ]
    
    # 1. 尝试按名称查找
    available = {f.name for f in fm.fontManager.ttflist}
    target_font = None
    for x in font_candidates:
        if x in available:
            target_font = x
            break
            
    # 2. 如果未找到，尝试按路径加载 (WSL/Linux 常见路径)
    if not target_font:
        potential_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
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
        print(f"✅ 使用字体: {target_font}")
    else:
        print("⚠️ 警告: 未找到中文字体，图表可能显示乱码。")
        plt.rcParams['font.family'] = 'DejaVu Sans'

# ==================== 1. 绘图辅助函数 ====================

def save_plot_with_data(fig, plot_dir: Path, plot_name: str, data_df: pd.DataFrame, metadata: Dict):
    """保存 PNG、CSV 和 JSON，严格对齐 T2.2.10 契约"""
    plot_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存图片
    fig.savefig(plot_dir / f"{plot_name}.png", dpi=160, bbox_inches='tight')
    
    # 保存数据
    data_df.to_csv(plot_dir / f"{plot_name}.csv", index=False)
    
    # 保存元数据
    metadata.update({
        "plot_name": plot_name,
        "phase": "phase2_2",
        "source_csv": f"{plot_name}.csv",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
    })
    with open(plot_dir / f"{plot_name}.json", "w", encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    plt.close(fig)

# ==================== 2. 核心绘图逻辑 ====================

class ComprehensiveViz:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.views = list(self.config["views"].keys())
        self.base_out_dir = Path("outputs/plots/phase2_2")
        setup_chinese_font()

    def run_all(self):
        print("🚀 开始执行 T2.2.9: 全面精美图表生成...")
        multi_view_results = []
        
        for view_name in self.views:
            print(f"--- 处理视图: {view_name} ---")
            view_data = self._load_view_data(view_name)
            if not view_data:
                continue
            
            self._plot_category_b_score_structure(view_name, view_data)
            self._plot_category_d_h5_resonance(view_name, view_data)
            self._plot_category_f_shock_cooccurrence(view_name, view_data)
            self._plot_category_g_hub_bridge(view_name, view_data)
            
            if "stat_tests" in view_data:
                multi_view_results.append(view_data["stat_tests"])

        if multi_view_results:
            self._plot_category_h_multi_view_comparison(pd.concat(multi_view_results))

    def _load_view_data(self, view_name: str) -> Dict[str, Any]:
        view_dir_22 = Path(f"cache/semantic_graph/phase2_2/views/{view_name}")
        manifest_files = list(view_dir_22.glob("*/manifests/view_stat_tests_manifest.json"))
        if not manifest_files:
            return None
        
        manifest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        view_key = manifest_files[0].parent.parent.name
        v_path = view_dir_22 / view_key
        
        data = {
            "key": view_key,
            "edges": pd.read_parquet(v_path / "phase2_2/market_behavior/edge_market_metrics.parquet"),
            "layer_summary": pd.read_csv(v_path / "phase2_2/market_behavior/edge_market_metrics_by_layer.csv"),
            "stat_tests": pd.read_csv(v_path / "phase2_2/stat_tests/h5_metric_tests.csv"),
            "sensitivity": pd.read_csv(v_path / "phase2_2/hub_bridge/sensitivity_analysis.csv")
        }
        data["stat_tests"]["view"] = view_name
        return data

    def _plot_category_b_score_structure(self, view_name: str, data: Dict):
        """B. 分数结构: 分数分布直方图"""
        print("  绘制 Category B: 分数结构...")
        edges = data["edges"]
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(data=edges, x="score", bins=50, kde=True, ax=ax)
        ax.set_title(f"视图 {view_name} 语义分数分布", fontsize=14)
        ax.set_xlabel("余弦相似度分数")
        ax.set_ylabel("边数量")
        
        stats = edges["score"].describe().to_frame().reset_index()
        save_plot_with_data(fig, self.base_out_dir / view_name, "score_distribution_by_view", 
                           stats, {"caption": "展示了语义边的分数集中度，用于验证 H2 假设。"})

    def _plot_category_d_h5_resonance(self, view_name: str, data: Dict):
        """D. H5 市场共振: Raw vs Residual Correlation 对比"""
        print("  绘制 Category D: 市场共振对比...")
        summary = data["layer_summary"]
        
        # 准备对比数据
        plot_df = summary.melt(id_vars="rank_band_exclusive", 
                               value_vars=["corr_raw_return", "corr_resid_full_neutral"],
                               var_name="Metric", value_name="Correlation")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(data=plot_df, x="rank_band_exclusive", y="Correlation", hue="Metric", ax=ax)
        ax.set_title(f"视图 {view_name}: 原始收益 vs 全中性残差收益相关性", fontsize=14)
        ax.set_xlabel("Rank Band")
        ax.set_ylabel("平均相关系数")
        
        save_plot_with_data(fig, self.base_out_dir / view_name, "raw_vs_residual_corr_by_view", 
                           plot_df, {"caption": "对比了控制行业/市值前后的相关性，判断是否为虚假相关。"})

    def _plot_category_f_shock_cooccurrence(self, view_name: str, data: Dict):
        """F. shock 与极端共现: 极端上涨/下跌共现率"""
        print("  绘制 Category F: 极端共现率...")
        summary = data["layer_summary"]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        summary.plot(x="rank_band_exclusive", y=["cooccur_extreme_up", "cooccur_extreme_down"], 
                    kind="bar", ax=ax)
        ax.set_title(f"视图 {view_name}: 极端行情共现率 (Top/Bottom 5%)", fontsize=14)
        ax.set_ylabel("共现概率")
        
        save_plot_with_data(fig, self.base_out_dir / view_name, "extreme_cooccurrence_by_view", 
                           summary[["rank_band_exclusive", "cooccur_extreme_up", "cooccur_extreme_down"]], 
                           {"caption": "验证语义近邻是否在极端行情下表现出协同效应。"})

    def _plot_category_g_hub_bridge(self, view_name: str, data: Dict):
        """G. hub / bridge: 入度分布"""
        print("  绘制 Category G: Hub 节点分析...")
        edges = data["edges"]
        in_degrees = edges.groupby("dst_node_id").size()
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.histplot(in_degrees, bins=30, ax=ax, log_scale=(False, True))
        ax.set_title(f"视图 {view_name}: 节点入度分布 (Log Scale)", fontsize=14)
        ax.set_xlabel("入度 (被作为近邻引用的次数)")
        ax.set_ylabel("节点数量 (Log)")
        
        save_plot_with_data(fig, self.base_out_dir / view_name, "hub_indegree_distribution", 
                           in_degrees.describe().to_frame().reset_index(), 
                           {"caption": "识别图中的 Hub 节点，用于后续稳健性检验。"})

    def _plot_category_h_multi_view_comparison(self, all_tests_df: pd.DataFrame):
        """H. 多 view 比较: 各视图超额相关性 (Delta Mean)"""
        print("  绘制 Category H: 多视图横向对比...")
        subset = all_tests_df[all_tests_df["baseline_type"] == "global_random"]
        
        fig, ax = plt.subplots(figsize=(12, 7))
        sns.barplot(data=subset, x="rank_layer", y="delta_mean", hue="view", ax=ax)
        ax.set_title("跨视图语义边超额残差相关性 (vs 全局随机)", fontsize=15)
        ax.axhline(0, color='black', linestyle='--', alpha=0.5)
        ax.set_ylabel("Delta Correlation (语义 - 随机)")
        
        save_plot_with_data(fig, self.base_out_dir / "multi_view", "h5_multi_view_comparison", 
                           subset, {"caption": "综合对比四个语义视图在控制组下的表现，锁定最优视图。"})

if __name__ == "__main__":
    viz = ComprehensiveViz("configs/phase2_1_multi_view_research.yaml")
    viz.run_all()
