import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_score_distribution_from_cache(cache_dir: Path, out_dir: Path) -> None:
    k = 20
    edges_path = cache_dir / f"edges_directed_k{k}.parquet"
    if not edges_path.exists():
        return

    edges = pd.read_parquet(edges_path)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].hist(edges["score"], bins=50, alpha=0.7, edgecolor="black")
    axes[0].set_xlabel("Score")
    axes[0].set_ylabel("Count")
    axes[0].set_title(f"All Directed Edge Scores (k={k})")
    axes[0].axvline(edges["score"].mean(), color="red", linestyle="--", label=f"mean={edges['score'].mean():.3f}")
    axes[0].legend()

    rank_stats = edges.groupby("rank")["score"].agg(["mean", "median", "std", "count"])
    rank_stats = rank_stats[rank_stats["count"] > 0]

    axes[1].plot(rank_stats.index, rank_stats["mean"], marker="o", label="mean")
    axes[1].fill_between(rank_stats.index, rank_stats["mean"] - rank_stats["std"], rank_stats["mean"] + rank_stats["std"], alpha=0.3)
    axes[1].set_xlabel("Rank")
    axes[1].set_ylabel("Score")
    axes[1].set_title(f"Score by Rank (k={k})")
    axes[1].legend()

    fig.suptitle(f"True Score Distribution from edges_directed_k{k}.parquet\nview=application_scenarios_json", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_dir / f"score_distribution_k{k}_true.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

def plot_score_by_rank_from_cache(cache_dir: Path, out_dir: Path) -> None:
    k = 20
    edges_path = cache_dir / f"edges_directed_k{k}.parquet"
    if not edges_path.exists():
        return

    edges = pd.read_parquet(edges_path)

    fig, ax = plt.subplots(figsize=(10, 6))

    rank_groups = edges.groupby("rank")["score"]
    rank_means = rank_groups.mean()
    rank_q25 = rank_groups.quantile(0.25)
    rank_q75 = rank_groups.quantile(0.75)

    ax.plot(rank_means.index, rank_means.values, marker="o", label="mean", linewidth=2)
    ax.fill_between(rank_means.index, rank_q25.values, rank_q75.values, alpha=0.3, label="Q25-Q75")
    ax.set_xlabel("Rank")
    ax.set_ylabel("Score")
    ax.set_title(f"Score by Rank with IQR (k={k})\nview=application_scenarios_json")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.savefig(out_dir / f"score_by_rank_k{k}.png", dpi=150, bbox_inches="tight")
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