import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_score_distribution_from_cache(cache_dir: Path, out_dir: Path) -> None:
    import json
    k = 20
    stats_path = cache_dir / f"graph_stats_k{k}.json"
    if not stats_path.exists():
        return

    with open(stats_path) as f:
        stats = json.load(f)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist([stats["top1_score_mean"]], bins=20, alpha=0.7, label="Top1")
    ax.hist([stats["top20_score_mean"]], bins=20, alpha=0.7, label="Top20")
    ax.set_xlabel("Score")
    ax.set_ylabel("Count")
    ax.set_title(f"Score Distribution (k={k})\nview=application_scenarios_json\nPCA only for visualization")
    ax.legend()
    fig.savefig(out_dir / f"score_distribution_k{k}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def plot_degree_distribution_from_cache(cache_dir: Path, out_dir: Path) -> None:
    edges_path = list(cache_dir.glob("edges_directed_k20*.parquet"))
    if not edges_path:
        return

    edges = pd.read_parquet(edges_path[0])
    k = 20
    n_nodes = 5502

    in_degrees = edges.groupby("dst_node_id").size().reindex(range(n_nodes), fill_value=0)
    out_degrees = edges.groupby("src_node_id").size().reindex(range(n_nodes), fill_value=0)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(in_degrees, bins=50, alpha=0.7)
    axes[0].set_xlabel("In-Degree")
    axes[0].set_ylabel("Count")
    axes[0].set_title("In-Degree Distribution (k=20)")

    axes[1].hist(out_degrees, bins=50, alpha=0.7)
    axes[1].set_xlabel("Out-Degree")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Out-Degree Distribution (k=20)")

    fig.suptitle("Degree Distribution\nview=application_scenarios_json, k=20\nPCA only for visualization")
    fig.savefig(out_dir / "degree_distribution_k20.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def plot_pca2_scatter_from_cache(cache_dir: Path, out_dir: Path, nodes: pd.DataFrame, sw_member_current: pd.DataFrame) -> None:
    layout_path = cache_dir / "layout_pca2.parquet"
    if not layout_path.exists():
        return

    layout = pd.read_parquet(layout_path)
    nodes_with_industry = nodes.merge(
        sw_member_current[["ts_code", "l1_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )
    layout = layout.merge(nodes_with_industry[["node_id", "l1_name"]], on="node_id", how="left")

    fig, ax = plt.subplots(figsize=(10, 8))
    for l1, color in zip(layout["l1_name"].dropna().unique(), plt.cm.tab20.colors):
        mask = layout["l1_name"] == l1
        ax.scatter(layout.loc[mask, "x"], layout.loc[mask, "y"], label=l1, alpha=0.6, s=10)

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("PCA2 Scatter by Current SW L1\nWARNING: Current SW membership only, not historical\nview=application_scenarios_json\nPCA only for visualization (not for graph construction)")
    ax.legend(loc="upper right", fontsize=6, ncol=2)
    fig.savefig(out_dir / "pca2_scatter_by_current_sw_l1.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def plot_ego_neighbors_from_cache(cache_dir: Path, out_dir: Path, stock_codes: list[str] = None) -> None:
    examples_path = cache_dir / "neighbor_examples_k20.parquet"
    if not examples_path.exists():
        return

    examples = pd.read_parquet(examples_path)

    if stock_codes is None:
        stock_codes = examples["src_stock_code"].unique()[:12].tolist()

    n = len(stock_codes)
    cols = 4
    rows = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(16, rows * 4))
    axes = axes.flatten() if n > 1 else [axes]

    for idx, code in enumerate(stock_codes):
        stock_examples = examples[examples["src_stock_code"] == code].head(10)
        if len(stock_examples) == 0:
            continue

        ax = axes[idx]
        y_pos = range(len(stock_examples))
        ax.barh(y_pos, stock_examples["score"].values)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"{r['dst_stock_name']}({r['dst_l1']})" for _, r in stock_examples.iterrows()], fontsize=6)
        ax.set_xlabel("Score")
        ax.set_title(f"{code}\nview=application_scenarios_json")

    for ax in axes[n:]:
        ax.axis("off")

    fig.suptitle("Ego Neighbor Examples (k=20)\nview=application_scenarios_json\nPCA only for visualization")
    fig.savefig(out_dir / "ego_neighbors_examples_k20.png", dpi=150, bbox_inches="tight")
    plt.close(fig)