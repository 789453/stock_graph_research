#!/usr/bin/env python3
"""
T1 - 真实语义数据审计
验证 NPY/Meta/Records 数据契约
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_graph_research import load_config, load_semantic_view, audit_semantic_bundle
from semantic_graph_research.cache_io import save_semantic_audit, make_cache_key

def main():
    config_path = Path(__file__).parent.parent / "configs" / "phase1_semantic_graph.yaml"
    config = load_config(config_path)

    print("=" * 60)
    print("T1: 真实语义数据审计")
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

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    cache_key = make_cache_key(bundle.input_fingerprints, config)
    cache_dir = cache_root / cache_key
    cache_dir.mkdir(parents=True, exist_ok=True)

    audit_dict = {
        "rows": audit.rows,
        "dim": audit.dim,
        "dtype": audit.dtype,
        "non_finite_count": audit.non_finite_count,
        "zero_norm_count": audit.zero_norm_count,
        "l2_min": audit.l2_min,
        "l2_mean": audit.l2_mean,
        "l2_max": audit.l2_max,
        "row_id_unique_count": audit.row_id_unique_count,
        "alignment_ok": audit.alignment_ok,
        "view": audit.view,
        "fingerprints": bundle.input_fingerprints,
    }
    save_semantic_audit(cache_dir, audit_dict)

    manifest = {
        "task": "T1",
        "cache_key": cache_key,
        "view": bundle.view,
        "audit": audit_dict,
    }
    with open(cache_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] 审计结果已保存至: {cache_dir}")
    print("=" * 60)
    print("T1 完成 - 审计通过")
    print("=" * 60)

if __name__ == "__main__":
    main()