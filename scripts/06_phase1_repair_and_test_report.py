#!/usr/bin/env python3
"""
T2.0: Phase 1 修复与测试报告缓存
目标：修复 alignment、self-neighbor、mutual 命名、score distribution、PROJECT_STATE 测试状态
"""
import sys
import json
from datetime import datetime
from pathlib import Path
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def find_phase1_config(project_root: Path):
    candidates = [
        project_root / "configs" / "phase1_semantic_graph.yaml",
        project_root / "configs" / "phase2_semantic_graph_research.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("No Phase 1 or Phase 2 config found")

def load_config_with_semantic(config_path: Path) -> dict:
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if "semantic" not in config:
        semantic_config = {
            "semantic": {
                "vectors_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.npy",
                "meta_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/npy/application_scenarios_json/application_scenarios_json-all.meta.json",
                "records_path": "/home/purple_born/QuantSum/stock_graph_research/a_share_semantic_dataset/parquet/records-all.parquet",
                "expected_rows": 5502,
                "expected_dim": 1024,
                "expected_dtype": "float32",
                "allow_fallback": False,
            }
        }
        config = {**config, **semantic_config}
    return config

from semantic_graph_research import diagnose_alignment
from semantic_graph_research.plotting import plot_score_distribution_from_cache, plot_score_by_rank_from_cache

def run_pytest():
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }

def generate_pytest_summary(pytest_result: dict) -> str:
    lines = []
    lines.append("# Phase 1 Pytest Summary\n")
    lines.append(f"**Run Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Status**: {'PASSED' if pytest_result['returncode'] == 0 else 'FAILED'}\n")
    lines.append("\n## Output\n")
    lines.append("```\n")
    lines.append(pytest_result["stdout"])
    if pytest_result["stderr"]:
        lines.append(pytest_result["stderr"])
    lines.append("```\n")
    return "\n".join(lines)

def main():
    project_root = Path(__file__).parent.parent

    print("=" * 60)
    print("T2.0: Phase 1 修复与测试报告缓存")
    print("=" * 60)

    config_path = find_phase1_config(project_root)
    print(f"[OK] 找到配置: {config_path}")

    config = load_config_with_semantic(config_path)
    print(f"[OK] 配置加载完成")

    cache_dir = project_root / "cache" / "semantic_graph" / "2eebde04e582"
    phase2_cache = cache_dir / "phase2"
    phase2_cache.mkdir(parents=True, exist_ok=True)
    manifests_dir = phase2_cache / "manifests"
    manifests_dir.mkdir(parents=True, exist_ok=True)

    print("\n[Step 1] 加载语义数据...")
    try:
        from semantic_graph_research import load_semantic_view
        bundle = load_semantic_view(config)
        print(f"[OK] 语义数据加载: view={bundle.view}, rows={bundle.rows}, dim={bundle.dim}")
    except Exception as e:
        print(f"[FAIL] 语义数据加载失败: {e}")
        sys.exit(1)

    print("\n[Step 2] Alignment 诊断...")
    try:
        alignment = diagnose_alignment(bundle, config["semantic"]["records_path"])
        alignment_dict = {
            "row_ids_count": alignment.row_ids_count,
            "records_count": alignment.records_count,
            "row_ids_unique_count": alignment.row_ids_unique_count,
            "records_record_id_unique_count": alignment.records_record_id_unique_count,
            "stock_code_unique_count": alignment.stock_code_unique_count,
            "row_order_binding_ok": alignment.row_order_binding_ok,
            "missing_in_records_count": alignment.missing_in_records_count,
            "extra_in_records_count": alignment.extra_in_records_count,
            "duplicate_row_ids": alignment.duplicate_row_ids,
            "duplicate_record_ids": alignment.duplicate_record_ids,
            "duplicate_stock_codes": alignment.duplicate_stock_codes,
            "all_checks_passed": alignment.all_checks_passed,
        }
        alignment_path = manifests_dir / "alignment_diagnostics.json"
        with open(alignment_path, "w", encoding="utf-8") as f:
            json.dump(alignment_dict, f, indent=2, ensure_ascii=False)
        print(f"[OK] Alignment 诊断已保存: {alignment_path}")
        print(f"     all_checks_passed: {alignment.all_checks_passed}")
        if not alignment.all_checks_passed:
            print(f"[WARN] Alignment 检查未完全通过")
    except Exception as e:
        print(f"[FAIL] Alignment 诊断失败: {e}")
        alignment_dict = {"error": str(e)}
        alignment_path = manifests_dir / "alignment_diagnostics.json"
        with open(alignment_path, "w", encoding="utf-8") as f:
            json.dump(alignment_dict, f, indent=2)

    print("\n[Step 3] 重新生成 Score Distribution 图表...")
    try:
        import matplotlib
        matplotlib.use("Agg")
        output_dir = project_root / "outputs" / "plots" / "phase2"
        output_dir.mkdir(parents=True, exist_ok=True)

        plot_score_distribution_from_cache(cache_dir, output_dir)
        print(f"[OK] score_distribution_k20_true.png 已生成")

        plot_score_by_rank_from_cache(cache_dir, output_dir)
        print(f"[OK] score_by_rank_k20.png 已生成")
    except Exception as e:
        print(f"[WARN] 图表生成失败: {e}")

    print("\n[Step 4] 运行 pytest...")
    pytest_result = run_pytest()
    pytest_passed = pytest_result["returncode"] == 0
    print(f"[{'PASSED' if pytest_passed else 'FAILED'}] pytest returncode={pytest_result['returncode']}")

    print("\n[Step 5] 生成测试报告...")
    pytest_summary = generate_pytest_summary(pytest_result)
    summary_path = project_root / "outputs" / "reports" / "phase2" / "phase1_pytest_summary.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(pytest_summary)
    print(f"[OK] 测试报告已保存: {summary_path}")

    log_dir = project_root / "logs" / "phase2"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"phase1_pytest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(pytest_result["stdout"])
        if pytest_result["stderr"]:
            f.write(pytest_result["stderr"])
    print(f"[OK] Pytest log 已保存: {log_path}")

    manifest = {
        "task_id": "T2.0",
        "task_name": "Phase 1 repair and test report",
        "phase1_cache_key": "2eebde04e582",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "status": "success" if pytest_passed else "failed",
        "inputs": [
            "configs/phase1_semantic_graph.yaml",
            "src/semantic_graph_research/semantic_loader.py",
            "src/semantic_graph_research/graph_builder.py",
            "src/semantic_graph_research/plotting.py",
            "tests/*.py",
        ],
        "outputs": [
            str(alignment_path),
            str(summary_path),
            str(log_path),
        ],
        "parameters": {},
        "row_counts": {
            "alignment_checks_passed": alignment_dict.get("all_checks_passed", False),
            "pytest_passed": pytest_passed,
        },
        "warnings": [],
        "error": None if pytest_passed else "pytest failed",
    }

    manifest_path = manifests_dir / "phase1_repair_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[OK] Manifest 已保存: {manifest_path}")

    print("\n" + "=" * 60)
    print(f"T2.0 {'完成' if pytest_passed else '失败 (pytest 未通过)'}")
    print("=" * 60)

    return 0 if pytest_passed else 1

if __name__ == "__main__":
    sys.exit(main())