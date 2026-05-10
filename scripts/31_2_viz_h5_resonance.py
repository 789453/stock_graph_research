import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import yaml

# ==================== 0. 环境与配置 ====================

def setup_chinese_font():
    import matplotlib.font_manager as fm
    font_candidates = ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "SimHei", "DejaVu Sans"]
    available = {f.name for f in fm.fontManager.ttflist}
    target_font = next((x for x in font_candidates if x in available), "DejaVu Sans")
    plt.rcParams['font.family'] = target_font
    plt.rcParams['axes.unicode_minus'] = False
    return target_font

def save_artifact(fig, path_prefix: Path, plot_name: str, data: pd.DataFrame, caption: str):
    path_prefix.mkdir(parents=True, exist_ok=True)
    fig.savefig(path_prefix / f"{plot_name}.png", dpi=140, bbox_inches='tight')
    data.to_csv(path_prefix / f"{plot_name}.csv", index=False)
    meta = {"plot_name": plot_name, "caption": caption, "generated_at": pd.Timestamp.now().isoformat()}
    with open(path_prefix / f"{plot_name}.json", "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    plt.close(fig)

# ==================== 1. 引擎 2: H5 Resonance & Shocks ====================

class ResonanceShockEngine:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.views = list(self.config["views"].keys())
        self.out_root = Path("outputs/plots/phase2_2")
        setup_chinese_font()

    def run(self):
        print("📈 启动引擎 2: 市场共振与 Shock 分析 (Category D, F)")
        for view in self.views:
            data = self._load_data(view)
            if data is None: continue
            self._plot_category_d_resonance(view, data)
            self._plot_category_f_shocks(view, data)

    def _load_data(self, view: str):
        v_dir = Path(f"cache/semantic_graph/phase2_2/views/{view}")
        m_files = list(v_dir.glob("*/manifests/view_market_metrics_manifest.json"))
        if not m_files: return None
        m_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        v_path = m_files[0].parent.parent
        
        return {
            "metrics": pd.read_parquet(v_path / "phase2_2/market_behavior/edge_market_metrics.parquet"),
            "layer_summary": pd.read_csv(v_path / "phase2_2/market_behavior/edge_market_metrics_by_layer.csv"),
            "stat_tests": pd.read_csv(v_path / "phase2_2/stat_tests/h5_metric_tests.csv")
        }

    def _plot_category_d_resonance(self, view, data):
        """D. H5 市场共振深度可视化"""
        print(f"  正在生成 {view} Category D (市场共振)...")
        tests = data["stat_tests"]
        
        # D2: Delta Heatmap (语义 vs 各种随机基准)
        pivot_delta = tests.pivot(index="rank_layer", columns="baseline_type", values="delta_mean")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(pivot_delta, annot=True, fmt=".4f", cmap="RdYlGn", center=0, ax=ax)
        ax.set_title(f"视图 {view}: 语义超额相关性 (Delta) 热力图")
        save_artifact(fig, self.out_root / view, "h5_delta_heatmap", pivot_delta.reset_index(), "超额相关性热力图")

        # D4: Z-Score 显著性 (P-value proxy)
        pivot_z = tests.pivot(index="rank_layer", columns="baseline_type", values="z_score")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(pivot_z, annot=True, fmt=".2f", cmap="YlOrRd", ax=ax)
        ax.set_title(f"视图 {view}: 显著性 Z-Score 热力图 (验证 H5)")
        save_artifact(fig, self.out_root / view, "h5_pvalue_heatmap", pivot_z.reset_index(), "显著性Z-Score热力图")

        # D6: Bootstrap CI Forest Plot (示意实现)
        subset = tests[tests["baseline_type"] == "global_random"]
        fig, ax = plt.subplots(figsize=(10, 6))
        for i, row in subset.iterrows():
            ax.errorbar(row["semantic_mean"], i, 
                        xerr=[[row["semantic_mean"] - row["bootstrap_ci_low"]], [row["bootstrap_ci_high"] - row["semantic_mean"]]], 
                        fmt='o', capsize=5, label=row["rank_layer"])
        ax.set_yticks(range(len(subset)))
        ax.set_yticklabels(subset["rank_layer"])
        ax.axvline(0, color='gray', linestyle='--')
        ax.set_title(f"视图 {view}: 语义边相关性 Bootstrap 置信区间")
        save_artifact(fig, self.out_root / view, "h5_bootstrap_ci_forest", subset, "Bootstrap置信区间森林图")

    def _plot_category_f_shocks(self, view, data):
        """F. Shock 与极端共现可视化"""
        print(f"  正在生成 {view} Category F (Shock 共现)...")
        summary = data["layer_summary"]
        
        # F3: 极端上涨共现率
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=summary, x="rank_band_exclusive", y="cooccur_extreme_up", palette="Reds", ax=ax)
        ax.set_title(f"视图 {view}: 极端上涨 (Top 5%) 共现率")
        save_artifact(fig, self.out_root / view, "extreme_up_cooccurrence", summary, "极端上涨共现率柱状图")

        # F4: 极端下跌共现率
        fig, ax = plt.subplots(figsize=(8, 5))
        sns.barplot(data=summary, x="rank_band_exclusive", y="cooccur_extreme_down", palette="Blues_r", ax=ax)
        ax.set_title(f"视图 {view}: 极端下跌 (Bottom 5%) 共现率")
        save_artifact(fig, self.out_root / view, "extreme_down_cooccurrence", summary, "极端下跌共现率柱状图")

        # F1/F2: Amount/Turnover Shock
        fig, ax = plt.subplots(figsize=(8, 5))
        summary.plot(x="rank_band_exclusive", y=["corr_amount_z", "corr_turnover_z"], kind="bar", ax=ax)
        ax.set_title(f"视图 {view}: 成交额与换手率 Shock 相关性")
        save_artifact(fig, self.out_root / view, "amount_shock_cooccurrence", summary, "成交额/换手率相关性柱状图")

if __name__ == "__main__":
    engine = ResonanceShockEngine("configs/phase2_1_multi_view_research.yaml")
    engine.run()
