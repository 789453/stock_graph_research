#!/usr/bin/env python3
"""
T2.2.7: 稳健统计检验 (Refactored)
使用 Permutation Test 和 Bootstrap 验证语义边的超额共振显著性。
彻底废弃基于独立样本假设的伪 P 值。
"""
import os
import json
import time
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

sys_path = str(Path(__file__).parent.parent / "src")
import sys
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)

from semantic_graph_research import load_config

def run_statistical_tests(args):
    start_time = time.time()
    
    config_path = Path(__file__).parent.parent / args.config
    config = load_config(config_path)

    print("=" * 60)
    print("T2.2.7: 稳健统计检验 (Refactored)")
    print(f"Config: {args.config}")
    print("=" * 60)

    cache_root = Path(config["cache"]["root"]) / "semantic_graph"
    if args.cache_key:
        cache_dir = cache_root / args.cache_key
    else:
        cache_dirs = [d for d in cache_root.iterdir() if d.is_dir() and d.name != "LATEST"]
        cache_dir = sorted(cache_dirs)[-1]

    phase2_cache = cache_dir / "phase2"
    resonance_cache = phase2_cache / "resonance"
    manifests_dir = phase2_cache / "manifests"

    # 1. 加载数据
    sem_path = resonance_cache / "edge_resonance_metrics_k20.parquet"
    rnd_path = resonance_cache / "matched_random_resonance_k20.parquet"
    
    if not sem_path.exists() or not rnd_path.exists():
        print(f"[FAIL] 缺少相关性数据，请先运行 T2.2.6")
        sys.exit(1)
        
    sem_df = pd.read_parquet(sem_path)
    rnd_df = pd.read_parquet(rnd_path)
    
    x_sem = sem_df["resid_corr"].dropna().values
    x_rnd = rnd_df["resid_corr"].dropna().values
    
    print(f"[OK] 加载 {len(x_sem)} 条语义边和 {len(x_rnd)} 条随机边")

    # 2. Permutation Test (置换检验)
    print("\n[Step 1] 执行 Permutation Test (H0: Semantic == Random)...")
    observed_diff = np.mean(x_sem) - np.mean(x_rnd)
    
    combined = np.concatenate([x_sem, x_rnd])
    n_sem = len(x_sem)
    n_rnd = len(x_rnd)
    
    n_permutations = 1000
    perm_diffs = []
    for _ in range(n_permutations):
        np.random.shuffle(combined)
        perm_sem = combined[:n_sem]
        perm_rnd = combined[n_sem:]
        perm_diffs.append(np.mean(perm_sem) - np.mean(perm_rnd))
    
    perm_diffs = np.array(perm_diffs)
    p_value = (np.abs(perm_diffs) >= np.abs(observed_diff)).mean()
    
    # 3. Bootstrap Confidence Interval (置信区间)
    print("[Step 2] 执行 Bootstrap 计算置信区间...")
    n_boot = 1000
    boot_diffs = []
    for _ in range(n_boot):
        b_sem = np.random.choice(x_sem, size=len(x_sem), replace=True)
        b_rnd = np.random.choice(x_rnd, size=len(x_rnd), replace=True)
        boot_diffs.append(np.mean(b_sem) - np.mean(b_rnd))
    
    ci_low, ci_high = np.percentile(boot_diffs, [2.5, 97.5])

    # 4. 生成结论
    print("\n[Step 3] 统计结论摘要:")
    print(f"  Observed Lift: {observed_diff:.6f}")
    print(f"  95% CI: [{ci_low:.6f}, {ci_high:.6f}]")
    print(f"  Permutation P-value: {p_value:.4g}")
    
    is_significant = p_value < 0.01 and ci_low > 0
    decision = "SUPPORTED" if is_significant else "REJECTED"
    print(f"  Decision: {decision}")

    # 5. 保存结果
    test_results = {
        "metric": "resid_corr_lift",
        "observed_lift": float(observed_diff),
        "ci_95": [float(ci_low), float(ci_high)],
        "p_value": float(p_value),
        "n_permutations": n_permutations,
        "n_bootstrap": n_boot,
        "status": decision,
        "created_at": datetime.now().isoformat()
    }
    
    with open(resonance_cache / "h5_statistical_tests.json", "w") as f:
        json.dump(test_results, f, indent=2)

    # 6. Manifest
    elapsed = time.time() - start_time
    manifest = {
        "task_id": "T2.2.7",
        "task_name": "statistical_tests",
        "status": "success",
        "cache_key": cache_dir.name,
        "summary": test_results
    }
    
    with open(manifests_dir / "t27_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"T2.2.7 完成. Elapsed: {elapsed:.1f}s")

def main():
    parser = argparse.ArgumentParser(description="T2.2.7: 稳健统计检验")
    parser.add_argument("--config", default="configs/phase2_semantic_graph_research.yaml", help="配置文件路径")
    parser.add_argument("--cache-key", help="指定缓存的 cache_key")
    args = parser.parse_args()
    run_statistical_tests(args)

if __name__ == "__main__":
    main()
