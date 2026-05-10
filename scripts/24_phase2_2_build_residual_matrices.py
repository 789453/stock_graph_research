import os
import json
import time
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
from typing import Any
from sklearn.linear_model import LinearRegression

def build_residual_matrices(global_config: dict[str, Any]):
    start_time = time.time()
    print("Starting T2.2.4: Building Residual Matrices...")
    
    panel_path = Path("cache/semantic_graph/phase2_2/market_panel/node_monthly_panel.parquet")
    profile_path = Path("cache/semantic_graph/multi_view/baselines/node_size_liquidity_profile.parquet")
    sw_path = global_config["market_data"]["stock_sw_member_path"]
    
    panel = pd.read_parquet(panel_path)
    profile = pd.read_parquet(profile_path)
    sw_df = pd.read_parquet(sw_path)
    sw_latest = sw_df.sort_values("in_date").groupby("ts_code").last().reset_index()
    
    # Merge industry and profile info into panel
    panel = panel.merge(sw_latest[["ts_code", "l1_name", "l3_name"]], left_on="stock_code", right_on="ts_code", how="left")
    panel = panel.merge(profile[["stock_code", "log_total_mv", "log_amount", "median_turnover_rate"]], on="stock_code", how="left")
    
    # Fill missing values for regression
    panel["log_total_mv"] = panel["log_total_mv"].fillna(panel["log_total_mv"].median())
    panel["log_amount"] = panel["log_amount"].fillna(panel["log_amount"].median())
    panel["median_turnover_rate"] = panel["median_turnover_rate"].fillna(panel["median_turnover_rate"].median())
    
    months = sorted(panel["month"].unique())
    stock_codes = sorted(panel["stock_code"].unique())
    stock_to_idx = {code: i for i, code in enumerate(stock_codes)}
    
    n_stocks = len(stock_codes)
    n_months = len(months)
    
    # Initialize matrices
    matrix_names = [
        "monthly_return", "ret_resid_market", "ret_resid_l1", 
        "ret_resid_l3", "ret_resid_size_liquidity", "ret_resid_full_neutral",
        "volatility", "amount_z", "turnover_z", "extreme_up", "extreme_down"
    ]
    matrices = {name: np.full((n_stocks, n_months), np.nan, dtype=np.float32) for name in matrix_names}
    
    print("Performing monthly residual decomposition...")
    for m_idx, month in enumerate(months):
        m_data = panel[panel["month"] == month].copy()
        if m_data.empty: continue
        
        # 1. Raw return and other direct metrics
        for code, val in zip(m_data["stock_code"], m_data["monthly_return"]):
            matrices["monthly_return"][stock_to_idx[code], m_idx] = val
        for code, val in zip(m_data["stock_code"], m_data["monthly_volatility"]):
            matrices["volatility"][stock_to_idx[code], m_idx] = val
        for code, val in zip(m_data["stock_code"], m_data["monthly_amount_z"]):
            matrices["amount_z"][stock_to_idx[code], m_idx] = val
        for code, val in zip(m_data["stock_code"], m_data["monthly_turnover_z"]):
            matrices["turnover_z"][stock_to_idx[code], m_idx] = val
        for code, val in zip(m_data["stock_code"], m_data["extreme_up_flag"]):
            matrices["extreme_up"][stock_to_idx[code], m_idx] = float(val)
        for code, val in zip(m_data["stock_code"], m_data["extreme_down_flag"]):
            matrices["extreme_down"][stock_to_idx[code], m_idx] = float(val)
            
        # 2. Market Residual
        m_mean = m_data["monthly_return"].mean()
        m_data["resid_market"] = m_data["monthly_return"] - m_mean
        for code, val in zip(m_data["stock_code"], m_data["resid_market"]):
            matrices["ret_resid_market"][stock_to_idx[code], m_idx] = val
            
        # 3. L1 Residual
        m_data["resid_l1"] = m_data["monthly_return"] - m_data.groupby("l1_name")["monthly_return"].transform("mean")
        m_data["resid_l1"] = m_data["resid_l1"].fillna(m_data["resid_market"]) # Fallback if no L1
        for code, val in zip(m_data["stock_code"], m_data["resid_l1"]):
            matrices["ret_resid_l1"][stock_to_idx[code], m_idx] = val
            
        # 4. L3 Residual
        m_data["resid_l3"] = m_data["monthly_return"] - m_data.groupby("l3_name")["monthly_return"].transform("mean")
        m_data["resid_l3"] = m_data["resid_l3"].fillna(m_data["resid_l1"]) # Fallback if no L3
        for code, val in zip(m_data["stock_code"], m_data["resid_l3"]):
            matrices["ret_resid_l3"][stock_to_idx[code], m_idx] = val
            
        # 5. Size/Liquidity Residual (OLS)
        valid_mask = m_data["monthly_return"].notna()
        if valid_mask.sum() > 10:
            X = m_data.loc[valid_mask, ["log_total_mv", "log_amount", "median_turnover_rate"]].values
            y = m_data.loc[valid_mask, "monthly_return"].values
            reg = LinearRegression().fit(X, y)
            m_data.loc[valid_mask, "resid_size_liq"] = y - reg.predict(X)
            for code, val in zip(m_data.loc[valid_mask, "stock_code"], m_data.loc[valid_mask, "resid_size_liq"]):
                matrices["ret_resid_size_liquidity"][stock_to_idx[code], m_idx] = val
                
        # 6. Full Neutral (L1 + Size/Liq)
        # Using L1 dummies + Size/Liq features
        if valid_mask.sum() > 50:
            # Simple version: just L1 mean removal + Size/Liq regression on residuals
            y_l1 = m_data.loc[valid_mask, "resid_l1"].values
            X = m_data.loc[valid_mask, ["log_total_mv", "log_amount", "median_turnover_rate"]].values
            reg_full = LinearRegression().fit(X, y_l1)
            m_data.loc[valid_mask, "resid_full"] = y_l1 - reg_full.predict(X)
            for code, val in zip(m_data.loc[valid_mask, "stock_code"], m_data.loc[valid_mask, "resid_full"]):
                matrices["ret_resid_full_neutral"][stock_to_idx[code], m_idx] = val
                
    # Save matrices
    matrix_dir = Path("cache/semantic_graph/phase2_2/market_panel/matrices")
    matrix_dir.mkdir(parents=True, exist_ok=True)
    
    for name, mat in matrices.items():
        np.save(matrix_dir / f"{name}.npy", mat)
        
    with open(matrix_dir / "months.json", "w") as f:
        json.dump(months, f)
    with open(matrix_dir / "stock_codes.json", "w") as f:
        json.dump(stock_codes, f)
        
    # Manifest
    elapsed = time.time() - start_time
    manifest = {
        "phase": "phase2_2",
        "task_id": "T2.2.4",
        "task_name": "build_residual_matrices",
        "status": "success",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(start_time)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "elapsed_seconds": elapsed,
        "inputs": [str(panel_path)],
        "outputs": [str(matrix_dir / f"{name}.npy") for name in matrix_names],
        "row_counts": {"n_stocks": n_stocks, "n_months": n_months},
        "safe_to_continue": True
    }
    
    master_dir = Path("cache/semantic_graph/phase2_2/manifests")
    master_dir.mkdir(parents=True, exist_ok=True)
    with open(master_dir / "T2_2_4_matrix_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Residual matrices built: {len(matrices)} matrices saved.")
    return manifest

def main():
    config_path = "configs/phase2_1_multi_view_research.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    build_residual_matrices(config)

if __name__ == "__main__":
    main()
