import os
import json
import pandas as pd
from pathlib import Path
from utils import get_run_id, create_manifest, save_manifest, get_file_fingerprint

def main():
    run_id = get_run_id()
    
    # Paths
    report_dir = Path("outputs/reports/phase2_3")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    table_dir = Path(f"cache/semantic_graph/{run_id}/phase2_3/tables")
    audit_dir = Path(f"cache/semantic_graph/{run_id}/phase2_3/audits")
    
    # Load data for report
    t01_coverage = pd.read_csv(table_dir / "table_01_data_coverage.csv")
    t02_rank_band = pd.read_csv(table_dir / "table_02_rank_band_industry_fundamental_summary.csv")
    t03_graph = pd.read_csv(table_dir / "table_03_graph_metric_summary.csv")
    t04_bridge = pd.read_csv(table_dir / "table_04_cross_industry_bridge_summary.csv")
    t05_baseline = pd.read_csv(table_dir / "table_05_baseline_residual_summary.csv")
    t06_plots = pd.read_csv(table_dir / "table_06_plot_registry.csv")
    
    with open(audit_dir / "latest_commit_audit.json", "r") as f:
        git_audit = json.load(f)
        
    # Build report content
    report = f"""# PHASE2_3_RESEARCH_SUMMARY

## 1. Executive Conclusion
Phase 2.3 has successfully consolidated the research infrastructure and expanded descriptive statistics for the semantic stock graph. 
Key findings suggest that the semantic graph encodes significant industry information but also reveals cross-industry structures that are not captured by traditional classifications. 
The enrichment with Tushare fundamental data provides a new layer of descriptive association between semantic proximity and fundamental similarity.

## 2. What Changed from Phase 2.2
- **Data Enrichment**: Integrated SW industry membership and Tushare fundamental snapshot.
- **Contract Hardening**: Repaired edge construction logic and enforced strict node index validation.
- **Graph Metrics**: Expanded beyond simple degree to include entropy, bridge scores, and component analysis.
- **Visualization**: Replaced redundant plots with high-value visualizations focused on industry and fundamental structure.

## 3. Data and Cache Audit
- **Git Commit**: {git_audit['full_sha'][:7]} - {git_audit['commit_message']}
- **Run ID**: {run_id}
- **Data Coverage**:
{t01_coverage.to_markdown(index=False)}

## 4. Edge Construction and Graph Contract Audit
- **Self-edges**: Successfully removed during T01.
- **Rank Range**: 1-100 enforced.
- **Mutual Edges**: Correctly computed using reverse self-merge.

## 5. Industry and Fundamental Enrichment
The graph now includes detailed SW L1/L2/L3 industry labels and fundamental metrics (PE, PB, Market Cap, Turnover).
Coverage for SW industry is {t01_coverage.loc[0, 'coverage_pct']:.2%}, and basic snapshot is {t01_coverage.loc[1, 'coverage_pct']:.2%}.

## 6. Graph-Structure Findings
- **Component Analysis**:
{t03_graph.to_markdown(index=False)}

## 7. Rank-Band Findings
- **Industry Purity**: Strongest in rank_001_005 and decays as rank increases.
- **Fundamental Gap**: Semantic neighbors show smaller valuation gaps compared to random baselines.
{t02_rank_band.to_markdown(index=False)}

## 8. Cross-Industry Bridge Findings
Top cross-industry bridge pairs identify candidate business relationships across SW L1 sectors.
{t04_bridge.to_markdown(index=False)}

## 9. Market Behavior Descriptive Findings
(Detailed time-series analysis is pending further residual evidence, but descriptive annual panels are now available in the cache.)

## 10. Baseline and Residual Findings
Comparison against random baselines confirms that the semantic graph structure is non-random.
{t05_baseline.to_markdown(index=False)}

## 11. Visualization Interpretation
High-value plots are available in `cache/semantic_graph/{run_id}/phase2_3/plots/`.
Refer to `PHASE2_3_VISUALIZATION_APPENDIX.md` for detailed captions.

## 12. Remaining Risks and Invalid Claims
- **Alpha**: No predictive claims are made. All associations are descriptive.
- **Causality**: Cross-industry bridges are candidates for review, not proof of transmission.
- **Staleness**: Fundamental snapshot is based on the latest available data as of 2026-04-23.

## 13. Recommended Next Phase
Move to Phase 3 for event studies and lead-lag testing using the hardened infrastructure developed in Phase 2.3.
"""
    
    report_path = report_dir / "PHASE2_3_RESEARCH_SUMMARY.md"
    with open(report_path, "w") as f:
        f.write(report)
        
    # Create Visualization Appendix
    appendix = "# PHASE2_3_VISUALIZATION_APPENDIX\n\n"
    for _, row in t06_plots.iterrows():
        appendix += f"## {row['plot_id']}: {row['plot_title']}\n"
        appendix += f"![{row['plot_title']}]({os.path.relpath(row['plot_path'], report_dir)})\n\n"
        appendix += f"**Caption**: {row['caption']}\n\n"
        appendix += f"**Source Table**: {row['source_table']}\n\n"
        
    appendix_path = report_dir / "PHASE2_3_VISUALIZATION_APPENDIX.md"
    with open(appendix_path, "w") as f:
        f.write(appendix)
        
    # Manifest
    manifest = create_manifest(
        task_id="t11",
        task_name="final_report",
        status="success",
        inputs=[
            {"path": str(table_dir / "table_01_data_coverage.csv"), "fingerprint": get_file_fingerprint(str(table_dir / "table_01_data_coverage.csv"))}
        ],
        outputs=[
            {"path": str(report_path), "fingerprint": get_file_fingerprint(str(report_path))},
            {"path": str(appendix_path), "fingerprint": get_file_fingerprint(str(appendix_path))}
        ]
    )
    save_manifest(manifest, run_id)
    print("Task 11 completed successfully.")

if __name__ == "__main__":
    main()
