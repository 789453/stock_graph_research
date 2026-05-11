#!/usr/bin/env python3
"""
T1 - 真实语义数据审计
验证 NPY/Meta/Records 数据契约
"""
import sys
import json
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, audit_semantic_bundle
from semantic_graph_research.cache_io import save_semantic_audit, make_cache_key

def main():
    parser = argparse.ArgumentParser(description="T1: 真实语义数据审计")
    parser.add_argument("--view", required=False, default=None, help="语义视图名称")
    parser.add_argument("--config", default="configs/phase1_semantic_graph.yaml", help="配置文件路径")
    parser.add_argument("--out-root", default=None, help="输出根目录，默认为 config 中的 cache.root")
    parser.add_argument("--strict", action="store_true", help="是否启用严格审计模式")
    args = parser.parse_args()

    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    # 如果 CLI 指定了 view，覆盖 config 中的 view
    if args.view:
        config["semantic"]["view"] = args.view
        # 这里可能需要根据 view 更新路径，但通常 view 决定了文件名
        print(f"[INFO] 使用指定的 view: {args.view}")

    print("=" * 60)
    print("T1: 真实语义数据审计")
    print(f"Config: {args.config}")
    print(f"Strict: {args.strict}")
    print("=" * 60)

    try:
        bundle = load_semantic_view(config)
        print(f"[OK] 语义数据加载成功")
        print(f"     view: {bundle.view}")
        print(f"     rows: {bundle.rows}")
        print(f"     dim: {bundle.dim}")
    except Exception as e:
        print(f"[FAIL] 语义数据加载失败: {e}")
        sys.exit(1)

    # 强断言：meta["row_ids"] 与 records["record_id"] 的顺序完全一致
    print("[INFO] 正在执行节点顺序审计...")
    records_path = Path(config["semantic"]["records_path"])
    records_df = pd.read_parquet(records_path)
    
    # 集合一致性检查已经在 load_semantic_view 中做了，这里加顺序一致性
    if len(bundle.row_ids) != len(records_df):
        print(f"[FAIL] 行数不匹配: meta.row_ids={len(bundle.row_ids)}, records={len(records_df)}")
        if args.strict: sys.exit(1)
    
    # 快速检查顺序
    order_ok = (np.array(bundle.row_ids) == records_df["record_id"].values).all()
    if not order_ok:
        print(f"[FAIL] 节点顺序不匹配！meta['row_ids'] 与 records['record_id'] 顺序不一致。")
        print(f"       这会导致后续 node_id 和向量行号错位。")
        if args.strict: sys.exit(1)
    else:
        print(f"[OK] 节点顺序对齐审计通过")

    try:
        audit = audit_semantic_bundle(bundle, config)
        print(f"[OK] 语义数据审计通过")
        print(f"     rows: {audit.rows}")
        print(f"     dim: {audit.dim}")
        print(f"     dtype: {audit.dtype}")
        print(f"     non_finite_count: {audit.non_finite_count}")
        print(f"     zero_norm_count: {audit.zero_norm_count}")
        print(f"     l2_min: {audit.l2_min:.4f}")
        print(f"     l2_mean: {audit.l2_mean:.4f}")
        print(f"     l2_max: {audit.l2_max:.4f}")
        print(f"     row_id_unique_count: {audit.row_id_unique_count}")
        print(f"     alignment_ok: {audit.alignment_ok}")
        print(f"     view: {audit.view}")
    except Exception as e:
        print(f"[FAIL] 语义数据审计失败: {e}")
        sys.exit(1)

    # 确定输出目录
    cache_root = Path(args.out_root) if args.out_root else Path(config["cache"]["root"]) / "semantic_graph"
    cache_key = make_cache_key(bundle.input_fingerprints, config)
    cache_dir = cache_root / cache_key
    cache_dir.mkdir(parents=True, exist_ok=True)

    audit_dict = {
        "view": audit.view,
        "records_path": str(records_path),
        "npy_path": config["semantic"]["vectors_path"],
        "meta_path": config["semantic"]["meta_path"],
        "records_sha256": bundle.input_fingerprints["records"]["sha256"],
        "npy_sha256": bundle.input_fingerprints["vectors"]["sha256"],
        "meta_sha256": bundle.input_fingerprints["meta"]["sha256"],
        "rows": audit.rows,
        "dim": audit.dim,
        "dtype": audit.dtype,
        "non_finite_count": audit.non_finite_count,
        "zero_norm_count": audit.zero_norm_count,
        "l2_min": audit.l2_min,
        "l2_mean": audit.l2_mean,
        "l2_max": audit.l2_max,
        "row_id_unique_count": audit.row_id_unique_count,
        "row_id_alignment_ok": audit.alignment_ok,
        "stock_code_unique_ok": records_df["stock_code"].is_unique,
        "finite_ok": audit.non_finite_count == 0,
        "order_ok": order_ok,
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "script": "00_audit_semantic_data.py",
        "fingerprints": bundle.input_fingerprints,
    }
    save_semantic_audit(cache_dir, audit_dict)

    manifest = {
        "task": "T1",
        "cache_key": cache_key,
        "view": bundle.view,
        "audit": audit_dict,
        "config_path": str(config_path),
        "strict_mode": args.strict,
    }
    with open(cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] 审计结果已保存至: {cache_dir}")
    print("=" * 60)
    print("T1 完成 - 审计通过")
    print("=" * 60)

if __name__ == "__main__":
    main()