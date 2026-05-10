import os
import json
import time
from pathlib import Path

def check_function_exists(file_path: str, func_name: str) -> bool:
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r") as f:
        content = f.read()
    return f"def {func_name}" in content

def check_pattern_exists(file_path: str, pattern: str) -> bool:
    if not os.path.exists(file_path):
        return False
    with open(file_path, "r") as f:
        content = f.read()
    return pattern in content

def run_audit():
    start_time = time.time()
    print("Starting T2.2.0 Code Consistency Audit...")
    
    required_functions = {
        "src/semantic_graph_research/graph_builder.py": ["derive_mutual_edges_fast"],
        "src/semantic_graph_research/phase2_graph_layers.py": [
            "prepare_nodes_index",
            "assign_rank_band_exclusive",
            "build_edge_candidates_fixed"
        ]
    }
    
    audit_results = {
        "task_id": "T2.2.0",
        "status": "success",
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "required_functions": {},
        "forbidden_patterns": {
            "score_dict_integer_key_reverse_score": False,
            "legacy_rank_band_names_in_main_path": False
        },
        "blocking_errors": []
    }
    
    # 1. Check required functions
    for file_path, funcs in required_functions.items():
        for func in funcs:
            exists = check_function_exists(file_path, func)
            audit_results["required_functions"][func] = exists
            if not exists:
                audit_results["blocking_errors"].append(f"Function {func} not found in {file_path}")
                audit_results["status"] = "failed"

    # 2. Check forbidden patterns
    # Pattern 1: score_dict = {i: edges.iloc[i]["score"] for i in range(len(edges))}
    # Pattern 2: "core", "strong", "stable" in assign_rank_band
    
    files_to_check = [
        "src/semantic_graph_research/phase2_graph_layers.py",
        "src/semantic_graph_research/graph_builder.py",
        "scripts/17_phase2_1_multi_view_graph.py"
    ]
    
    legacy_pattern_1 = 'score_dict = {i: edges.iloc[i]["score"]'
    legacy_pattern_2 = 'return "core"'
    
    for f in files_to_check:
        if check_pattern_exists(f, legacy_pattern_1):
            audit_results["forbidden_patterns"]["score_dict_integer_key_reverse_score"] = True
            audit_results["blocking_errors"].append(f"Legacy score_dict pattern found in {f}")
            audit_results["status"] = "failed"
        
        if check_pattern_exists(f, legacy_pattern_2):
            # Check if it's inside a legacy function that is not used
            # But the spec says "in main path"
            audit_results["forbidden_patterns"]["legacy_rank_band_names_in_main_path"] = True
            audit_results["blocking_errors"].append(f"Legacy rank band names found in {f}")
            audit_results["status"] = "failed"

    # 3. Save report
    report_dir = Path("outputs/reports/phase2_2")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    with open(report_dir / "T2_2_0_CODE_CONSISTENCY_AUDIT.json", "w") as f:
        json.dump(audit_results, f, indent=2)
        
    report_md = f"""# T2.2.0 Code Consistency Audit Report

- **Status**: {"✅ SUCCESS" if audit_results["status"] == "success" else "❌ FAILED"}
- **Timestamp**: {audit_results["checked_at"]}

## 1. Required Functions
| Function | Status |
|---|---|
"""
    for func, exists in audit_results["required_functions"].items():
        report_md += f"| `{func}` | {'✅ Found' if exists else '❌ Missing'} |\n"
        
    report_md += """
## 2. Forbidden Patterns
| Pattern | Found |
|---|---|
"""
    for pattern, found in audit_results["forbidden_patterns"].items():
        report_md += f"| `{pattern}` | {'❌ Found (Bad)' if found else '✅ Not Found'} |\n"
        
    if audit_results["blocking_errors"]:
        report_md += "\n## 3. Blocking Errors\n"
        for err in audit_results["blocking_errors"]:
            report_md += f"- {err}\n"
            
    with open(report_dir / "T2_2_0_CODE_CONSISTENCY_AUDIT.md", "w") as f:
        f.write(report_md)
        
    print(f"Audit finished with status: {audit_results['status']}")
    return audit_results

if __name__ == "__main__":
    run_audit()
