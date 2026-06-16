"""
Panel Classification Module
============================
Classifies panels into production classes based on Panel Type, Area Group, and Length Group.
"""
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def compute_area_boundaries(df):
    area_values = df["Area_mm2"].values
    percentiles = np.percentile(area_values, config.AREA_PERCENTILES)
    boundaries = {}
    for i, label in enumerate(config.AREA_GROUPS):
        boundaries[label] = (percentiles[i], percentiles[i + 1])
    return boundaries

def compute_length_boundaries(df):
    length_values = df["Length_mm"].values
    percentiles = np.percentile(length_values, config.LENGTH_PERCENTILES)
    boundaries = {}
    for i, label in enumerate(config.LENGTH_GROUPS):
        boundaries[label] = (percentiles[i], percentiles[i + 1])
    return boundaries

def assign_area_group(area, boundaries):
    for i, label in enumerate(config.AREA_GROUPS):
        lo, hi = boundaries[label]
        if i == 0 and area <= hi: return label
        elif i == len(config.AREA_GROUPS) - 1 and area > lo: return label
        elif lo < area <= hi: return label
    return config.AREA_GROUPS[-1]

def assign_length_group(length, boundaries):
    for i, label in enumerate(config.LENGTH_GROUPS):
        lo, hi = boundaries[label]
        if i == 0 and length <= hi: return label
        elif i == len(config.LENGTH_GROUPS) - 1 and length > lo: return label
        elif lo < length <= hi: return label
    return config.LENGTH_GROUPS[-1]

def classify_panels(df):
    area_bounds = compute_area_boundaries(df)
    length_bounds = compute_length_boundaries(df)
    df["Area_Group"] = df["Area_mm2"].apply(lambda x: assign_area_group(x, area_bounds))
    df["Length_Group"] = df["Length_mm"].apply(lambda x: assign_length_group(x, length_bounds))
    df["Production_Class"] = (
        df["Panel_Type"].str.replace("-", "").str.replace(" ", "")
        + "_" + df["Area_Group"] + "_" + df["Length_Group"]
    )
    df.attrs["area_boundaries"] = area_bounds
    df.attrs["length_boundaries"] = length_bounds
    return df, area_bounds, length_bounds

def assign_production_time(df, thermal_timing, non_thermal_timing):
    production_times = []
    for _, row in df.iterrows():
        area_group = row["Area_Group"]
        panel_type = row["Panel_Type"]
        if panel_type == "Thermal":
            base_time = thermal_timing.get(area_group, config.THERMAL_MEAN_TIME_SEC)
        else:
            base_time = non_thermal_timing.get(area_group, config.NON_THERMAL_MEAN_TIME_SEC)
        length_group = row["Length_Group"]
        if length_group == "Short": time_factor = 0.92
        elif length_group == "Medium": time_factor = 1.0
        else: time_factor = 1.08
        production_times.append(round(base_time * time_factor, 2))
    df["Production_Time_Sec"] = production_times
    df["Production_Time_Min"] = (df["Production_Time_Sec"] / 60).round(3)
    return df

def get_class_timing_map(df):
    return df.groupby("Production_Class")["Production_Time_Sec"].mean().to_dict()
