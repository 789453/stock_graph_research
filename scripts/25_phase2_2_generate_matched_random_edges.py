import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any, List, Dict

try:
    from tqdm.auto import tqdm
except Exception:
    tqdm = None


def _progress(iterable, **kwargs):
    if tqdm is None:
        return iterable
    return tqdm(iterable, **kwargs)


def _sample_without_replacement_rows(
    pool: np.ndarray,
    n_rows: int,
    k: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Per row sample k items from pool without replacement.
    Output shape: (n_rows, k)

    Fast path:
    - when pool is much larger than k, use rejection sampling.
    - otherwise use random-key argpartition.
    """
    p = len(pool)

    if k <= 0:
        return np.empty((n_rows, 0), dtype=np.int32)

    if k == 1:
        idx = rng.integers(0, p, size=(n_rows, 1))
        return pool[idx]

    # Fast when k is small relative to pool.
    # This avoids building an n_rows x p random matrix.
    if p >= 4 * k:
        idx = np.empty((n_rows, k), dtype=np.int64)
        idx[:, 0] = rng.integers(0, p, size=n_rows)

        for col in range(1, k):
            draw = rng.integers(0, p, size=n_rows)
            dup = (draw[:, None] == idx[:, :col]).any(axis=1)

            while dup.any():
                draw[dup] = rng.integers(0, p, size=int(dup.sum()))
                dup = (draw[:, None] == idx[:, :col]).any(axis=1)

            idx[:, col] = draw

        return pool[idx]

    # Fallback for dense sampling where k is close to pool size.
    keys = rng.random((n_rows, p))
    idx = np.argpartition(keys, kth=k - 1, axis=1)[:, :k]

    # Randomize within selected k columns so column order is also random.
    order = np.argsort(rng.random((n_rows, k)), axis=1)
    idx = np.take_along_axis(idx, order, axis=1)

    return pool[idx]


def _sample_from_pool(
    pool: np.ndarray,
    n_rows: int,
    k: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Preserve original logic:
    - if len(pool) < k, sample with replacement.
    - else sample without replacement per repeat row.
    """
    pool = np.asarray(pool, dtype=np.int32)
    p = len(pool)

    if p == 0:
        raise ValueError("empty pool")

    if p < k:
        idx = rng.integers(0, p, size=(n_rows, k))
        return pool[idx]

    return _sample_without_replacement_rows(pool, n_rows, k, rng)


def _build_pool_getter(nodes: pd.DataFrame, baseline_type: str):
    """
    Build a callable get_pool(src) -> candidate node_id array.
    Candidate semantics match the original implementation.
    """
    empty = np.empty(0, dtype=np.int32)

    nodes = nodes.copy()
    nodes["node_id"] = nodes.index.astype(np.int32)
    node_ids = nodes["node_id"].to_numpy(dtype=np.int32, copy=False)

    if baseline_type == "global_random":
        all_nodes = node_ids

        def get_pool(src: int) -> np.ndarray:
            # Original code excludes self for non-cross baselines.
            return all_nodes[all_nodes != src]

        return get_pool

    if baseline_type == "same_l3_random":
        groups = {
            key: grp.to_numpy(dtype=np.int32, copy=False)
            for key, grp in nodes.groupby("l3_name", sort=False)["node_id"]
        }
        node_to_group = dict(zip(node_ids.tolist(), nodes["l3_name"].tolist()))

        def get_pool(src: int) -> np.ndarray:
            key = node_to_group.get(int(src))
            pool = groups.get(key)
            if pool is None:
                return empty
            return pool[pool != src]

        return get_pool

    if baseline_type == "same_l3_same_size_random":
        nodes["grp"] = (
            nodes["l3_name"].astype(str)
            + "_"
            + nodes["total_mv_bucket_10"].astype(str)
        )
        groups = {
            key: grp.to_numpy(dtype=np.int32, copy=False)
            for key, grp in nodes.groupby("grp", sort=False)["node_id"]
        }
        node_to_group = dict(zip(node_ids.tolist(), nodes["grp"].tolist()))

        def get_pool(src: int) -> np.ndarray:
            key = node_to_group.get(int(src))
            pool = groups.get(key)
            if pool is None:
                return empty
            return pool[pool != src]

        return get_pool

    if baseline_type == "same_l3_same_liquidity_random":
        nodes["grp"] = (
            nodes["l3_name"].astype(str)
            + "_"
            + nodes["turnover_rate_bucket_10"].astype(str)
        )
        groups = {
            key: grp.to_numpy(dtype=np.int32, copy=False)
            for key, grp in nodes.groupby("grp", sort=False)["node_id"]
        }
        node_to_group = dict(zip(node_ids.tolist(), nodes["grp"].tolist()))

        def get_pool(src: int) -> np.ndarray:
            key = node_to_group.get(int(src))
            pool = groups.get(key)
            if pool is None:
                return empty
            return pool[pool != src]

        return get_pool

    if baseline_type == "cross_l1_random":
        # Original logic:
        # candidates are nodes not in the same L1.
        # If src_l1 is missing / not found, fallback to all nodes.
        groups = {
            key: grp.to_numpy(dtype=np.int32, copy=False)
            for key, grp in nodes.groupby("l1_name", sort=False)["node_id"]
        }
        node_to_l1 = dict(zip(node_ids.tolist(), nodes["l1_name"].tolist()))
        l1_values = nodes["l1_name"].to_numpy()
        complement_cache: Dict[Any, np.ndarray] = {}

        def get_pool(src: int) -> np.ndarray:
            src_l1 = node_to_l1.get(int(src))

            if src_l1 in groups:
                if src_l1 not in complement_cache:
                    complement_cache[src_l1] = node_ids[l1_values != src_l1]
                return complement_cache[src_l1]

            # Preserve original fallback: all nodes, including possibly self.
            return node_ids

        return get_pool

    # Fallback to global_random semantics.
    all_nodes = node_ids

    def get_pool(src: int) -> np.ndarray:
        return all_nodes[all_nodes != src]

    return get_pool


def generate_random_edges(
    nodes_df: pd.DataFrame,
    src_node_ids: np.ndarray,
    baseline_type: str,
    n_repeats: int = 200,
    seed: int = 20260510
) -> np.ndarray:
    """
    Generate random dst_node_ids for each src_node_id, matched by criteria.
    Returns array of shape (n_repeats, len(src_node_ids))

    Optimized but interface-compatible version.
    """
    rng = np.random.default_rng(seed)
    src_node_ids = np.asarray(src_node_ids, dtype=np.int32)
    n_edges = len(src_node_ids)

    all_dst = np.empty((n_repeats, n_edges), dtype=np.int32)

    if n_edges == 0:
        return all_dst

    get_pool = _build_pool_getter(nodes_df, baseline_type)

    # Build src -> edge column positions via sorting.
    # Faster and lighter than np.where for every unique src.
    order = np.argsort(src_node_ids, kind="mergesort")
    sorted_src = src_node_ids[order]

    change_pos = np.flatnonzero(sorted_src[1:] != sorted_src[:-1]) + 1
    starts = np.r_[0, change_pos]
    ends = np.r_[change_pos, n_edges]

    print(
        f"  Generating {n_repeats} repeats for {baseline_type}: "
        f"edges={n_edges:,}, unique_src={len(starts):,}"
    )

    src_blocks = zip(starts, ends)
    src_blocks = _progress(
        src_blocks,
        total=len(starts),
        desc=f"{baseline_type} source blocks",
        leave=False,
        mininterval=1.0,
    )

    for start, end in src_blocks:
        src = int(sorted_src[start])
        edge_idxs = order[start:end]
        k_src = end - start

        pool = get_pool(src)

        if len(pool) == 0:
            # Preserve original fallback.
            all_dst[:, edge_idxs] = src
            continue

        sampled = _sample_from_pool(pool, n_repeats, k_src, rng)
        all_dst[:, edge_idxs] = sampled

    return all_dst


def run_baseline_generation(view_name: str, global_config: dict[str, Any]):
    start_time = time.time()
    print(f"Generating matched random baselines for view: {view_name}")

    # 1. Locate latest view_key
    view_dir_22 = Path(f"cache/semantic_graph/phase2_2/views/{view_name}")
    manifest_files = list(view_dir_22.glob("*/manifests/view_edge_freeze_manifest.json"))

    if not manifest_files:
        raise FileNotFoundError(f"No freeze manifest found for {view_name}")

    manifest_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    view_key = manifest_files[0].parent.parent.name

    # 2. Load edges and node data
    # Column pruning reduces parquet I/O.
    edges_path = view_dir_22 / view_key / "edge_layers/edge_candidates_k100_fixed.parquet"
    edges = pd.read_parquet(
        edges_path,
        columns=["rank_band_exclusive", "src_node_id"],
    )

    profile_path = Path("cache/semantic_graph/multi_view/baselines/node_size_liquidity_profile.parquet")
    profile = pd.read_parquet(
        profile_path,
        columns=["stock_code", "total_mv_bucket_10", "turnover_rate_bucket_10"],
    )

    sw_path = global_config["market_data"]["stock_sw_member_path"]
    sw_df = pd.read_parquet(
        sw_path,
        columns=["ts_code", "in_date", "l1_name", "l3_name"],
    )

    # Faster than sort + groupby.last for this use case.
    sw_latest = (
        sw_df.sort_values("in_date")
        .drop_duplicates("ts_code", keep="last")
        .reset_index(drop=True)
    )

    records = pd.read_parquet(
        global_config["records"]["records_path"],
        columns=["stock_code"],
    )

    nodes = records[["stock_code"]].copy()
    nodes = nodes.merge(
        sw_latest[["ts_code", "l1_name", "l3_name"]],
        left_on="stock_code",
        right_on="ts_code",
        how="left",
    )
    nodes = nodes.merge(profile, on="stock_code", how="left")

    # 3. Define bands to process
    bands = ["rank_001_005", "rank_006_010", "rank_011_020"]
    baseline_types = [
        "global_random",
        "same_l3_random",
        "same_l3_same_size_random",
        "cross_l1_random",
    ]

    # Keep current setting. Increase after speed is verified.
    n_repeats = 50

    base_cache_path = view_dir_22 / view_key / "phase2_2/baselines"
    base_cache_path.mkdir(parents=True, exist_ok=True)

    results_manifest = {}

    # Pre-split band src ids once.
    src_ids_by_band = {
        band: edges.loc[
            edges["rank_band_exclusive"].eq(band),
            "src_node_id",
        ].to_numpy(dtype=np.int32, copy=False)
        for band in bands
    }

    band_iter = _progress(
        bands,
        total=len(bands),
        desc=f"{view_name} bands",
        mininterval=1.0,
    )

    for band in band_iter:
        src_ids = src_ids_by_band[band]
        print(
            f" Processing band: {band}, "
            f"edges={len(src_ids):,}, unique_src={len(np.unique(src_ids)):,}"
        )

        band_results = {}

        baseline_iter = _progress(
            baseline_types,
            total=len(baseline_types),
            desc=f"{band} baselines",
            leave=False,
            mininterval=1.0,
        )

        for b_type in baseline_iter:
            t0 = time.time()

            dst_repeats = generate_random_edges(
                nodes,
                src_ids,
                b_type,
                n_repeats=n_repeats,
            )

            # Save immediately to avoid holding multiple baselines in memory.
            out_path = base_cache_path / f"random_dst_{band}_{b_type}.npy"
            np.save(out_path, dst_repeats)

            band_results[b_type] = str(out_path)

            print(
                f"  Saved {b_type} for {band}: "
                f"shape={dst_repeats.shape}, "
                f"elapsed={time.time() - t0:.1f}s"
            )

            del dst_repeats

        results_manifest[band] = band_results

    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.5",
        "task_name": "generate_matched_random_edges",
        "view_name": view_name,
        "view_key": view_key,
        "status": "success",
        "n_repeats": n_repeats,
        "bands": bands,
        "baseline_types": baseline_types,
        "outputs": results_manifest,
        "elapsed_seconds": elapsed,
        "safe_to_continue": True,
    }

    with open(
        view_dir_22 / view_key / "manifests/view_random_baselines_manifest.json",
        "w",
    ) as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    views = list(config["views"].keys())

    view_iter = _progress(
        views,
        total=len(views),
        desc="views",
        mininterval=1.0,
    )

    for view_name in view_iter:
        run_baseline_generation(view_name, config)


if __name__ == "__main__":
    main()
