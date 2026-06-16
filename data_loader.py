"""
Data Loading Module
====================
Reads panel data from Excel files and prepares for processing.
"""

import pandas as pd
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def load_panel_dataset():
    """Load the main panel dataset from Excel."""
    if not os.path.exists(config.PANEL_DATASET_PATH):
        raise FileNotFoundError(
            f"Panel dataset not found at: {config.PANEL_DATASET_PATH}\n"
            f"Set the MUNTERS_PANEL_DATA environment variable to the correct path."
        )
    df = pd.read_excel(config.PANEL_DATASET_PATH, sheet_name="Munters_Panel_Dataset")
    df.columns = df.columns.str.strip()
    
    # Ensure correct types
    df["Length_mm"] = pd.to_numeric(df["Length_mm"], errors="coerce")
    df["Breadth_mm"] = pd.to_numeric(df["Breadth_mm"], errors="coerce")
    df["Area_mm2"] = pd.to_numeric(df["Area_mm2"], errors="coerce")
    df["Panel_Type"] = df["Panel_Type"].str.strip()
    df["FG_Design_Code"] = df["FG_Design_Code"].str.strip()
    
    # Drop rows with missing critical values
    df.dropna(subset=["Length_mm", "Breadth_mm", "Area_mm2", "Panel_Type"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # FG_Design_Code is not perfectly unique, so we create a guaranteed unique Panel_ID
    df["Panel_ID"] = "PID-" + df.index.astype(str)
    
    print(f"[DATA] Loaded {len(df)} panels | Thermal: {(df['Panel_Type']=='Thermal').sum()} | Non-Thermal: {(df['Panel_Type']=='Non-Thermal').sum()}")
    return df


def load_machine_uptime():
    """Load machine uptime data from Sheet2."""
    df = pd.read_excel(config.PANEL_DATASET_PATH, sheet_name="Sheet1")
    df.columns = df.columns.str.strip()
    machines = {}
    for _, row in df.iterrows():
        machine = str(row.iloc[0]).strip()
        uptime_str = str(row.iloc[1]).strip()
        # Extract numeric value
        uptime = int(''.join(filter(str.isdigit, uptime_str)))
        machines[machine] = uptime
    print(f"[DATA] Machine uptimes: {machines}")
    return machines


def load_thermal_timing():
    """Load thermal plate timing from the study file."""
    timing = {
        "XS": config.THERMAL_TIMING_BY_SIZE["Small"],        # 99 sec
        "S": config.THERMAL_TIMING_BY_SIZE["Small"],          # 99 sec
        "M": config.THERMAL_TIMING_BY_SIZE["Medium"],         # 117.44 sec
        "L": config.THERMAL_TIMING_BY_SIZE["Large"],          # 157.75 sec
        "XL": config.THERMAL_TIMING_BY_SIZE["XLarge"],        # 206 sec
        "XXL": config.THERMAL_TIMING_BY_SIZE["XLarge"] * 1.15, # Extrapolated ~237 sec
    }
    print(f"[DATA] Thermal timing loaded: {timing}")
    return timing


def load_non_thermal_timing():
    """Load non-thermal plate timing from the study file."""
    # Non-thermal panels have simpler bending - based on study data
    base_time = config.NON_THERMAL_MEAN_TIME_SEC  # 33.38 sec mean
    timing = {
        "XS": base_time * 0.75,          # ~25 sec
        "S": base_time * 0.85,           # ~28 sec
        "M": base_time,                  # ~33 sec
        "L": base_time * 1.15,           # ~38 sec
        "XL": base_time * 1.40,          # ~47 sec
        "XXL": config.NON_THERMAL_XXL_TIME_SEC,  # 75 sec (specified)
    }
    print(f"[DATA] Non-Thermal timing loaded: {timing}")
    return timing


def parse_fg_code(fg_code):
    """Parse FG Design Code into components.
    
    Format: FG-001-009-14
    FG-001 = Product Family
    009 = Machine/manufacturing group
    14 = Panel number within order
    """
    parts = fg_code.split("-")
    if len(parts) == 4:
        return {
            "prefix": parts[0],
            "family": parts[1],
            "machine_group": parts[2],
            "panel_number": parts[3],
        }
    return {"prefix": "", "family": "", "machine_group": "", "panel_number": ""}


def enrich_dataset(df):
    """Add derived features to the dataset."""
    # Parse FG codes
    parsed = df["FG_Design_Code"].apply(parse_fg_code)
    df["Product_Family"] = parsed.apply(lambda x: x["family"])
    df["Machine_Group"] = parsed.apply(lambda x: x["machine_group"])
    df["Panel_Number"] = parsed.apply(lambda x: x["panel_number"])
    
    # Aspect ratio
    df["Aspect_Ratio"] = df["Length_mm"] / df["Breadth_mm"].replace(0, 1)
    
    # Perimeter
    df["Perimeter_mm"] = 2 * (df["Length_mm"] + df["Breadth_mm"])
    
    # Is thermal flag
    df["Is_Thermal"] = (df["Panel_Type"] == "Thermal").astype(int)
    
    return df


if __name__ == "__main__":
    df = load_panel_dataset()
    machines = load_machine_uptime()
    t_timing = load_thermal_timing()
    nt_timing = load_non_thermal_timing()
    df = enrich_dataset(df)
    print(df.head())
    print(f"\nDataset shape: {df.shape}")
