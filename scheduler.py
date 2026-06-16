"""
Scheduling Engine
==================
Generates optimized machine schedules using greedy bin-packing with tool-change minimization.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def create_schedule(df, machines=None, start_offset_min=0):
    """Create optimized schedule for all machines.
    
    Strategy: Group by Production_Class first, then distribute to machines
    to minimize tool changes while balancing load.
    
    Args:
        start_offset_min: minutes elapsed since shift start (for mid-shift rescheduling)
    """
    if machines is None:
        machines = config.MACHINES
    
    capacity_min = config.EFFECTIVE_CAPACITY_MINUTES  # 450 min per machine
    tool_change_min = config.TOOL_CHANGE_TIME_MINUTES  # 17 min
    shift_start = datetime.strptime(config.SHIFT_START_TIME, "%H:%M")
    
    # For mid-shift rescheduling, reduce available capacity
    available_capacity = capacity_min - start_offset_min
    if available_capacity <= 0:
        available_capacity = 0
    
    # Sort panels: group by class to minimize tool changes
    df_sorted = df.sort_values(
        by=["Production_Class", "Production_Time_Sec"], 
        ascending=[True, False]
    ).reset_index(drop=True)
    
    # Initialize machine states — start from offset
    machine_state = {}
    for m in machines:
        machine_state[m] = {
            "current_time_min": start_offset_min,
            "current_class": None,
            "schedule": [],
            "tool_changes": 0,
            "panels_produced": 0,
            "total_prod_time": 0,
            "total_tool_time": 0,
        }
    
    # Group panels by class
    class_groups = {}
    for cls in df_sorted["Production_Class"].unique():
        class_panels = df_sorted[df_sorted["Production_Class"] == cls].to_dict("records")
        class_groups[cls] = class_panels
    
    # Sort classes by total time (largest first for better packing)
    class_order = sorted(
        class_groups.keys(),
        key=lambda c: sum(p["Production_Time_Sec"] for p in class_groups[c]),
        reverse=True
    )
    
    # Assign classes to machines using greedy load balancing
    for cls in class_order:
        panels = class_groups[cls]
        total_class_time = sum(p["Production_Time_Sec"] for p in panels) / 60  # to minutes
        
        # Find the machine with least load that can take this class
        # Prefer machines already running this class (no tool change needed)
        best_machine = None
        best_cost = float("inf")
        
        for m in machines:
            ms = machine_state[m]
            remaining = capacity_min - ms["current_time_min"]
            
            # Calculate cost: tool change + production time
            needs_tool_change = (ms["current_class"] != cls)
            tc_cost = tool_change_min if needs_tool_change else 0
            total_needed = total_class_time + tc_cost
            
            if total_needed <= remaining:
                # Prioritize: same class (0 penalty) > empty machine > different class
                if ms["current_class"] == cls:
                    cost = ms["current_time_min"]  # Lowest priority - same class
                elif ms["current_class"] is None:
                    cost = ms["current_time_min"] + 1000
                else:
                    cost = ms["current_time_min"] + 2000 + tc_cost
                
                if cost < best_cost:
                    best_cost = cost
                    best_machine = m
        
        if best_machine is None:
            # Find machine with most remaining capacity
            best_machine = min(machines, key=lambda m: machine_state[m]["current_time_min"])
        
        # We will add tool changes only when we actually place the first panel of the class
        
        # Add panels
        for panel in panels:
            prod_time_min = panel["Production_Time_Sec"] / 60
            ms = machine_state[best_machine]
            tc_needed = tool_change_min if (ms["current_class"] != cls) else 0
            
            if ms["current_time_min"] + tc_needed + prod_time_min <= capacity_min:
                # Panel fits on best_machine
                if tc_needed > 0:
                    tc_start = ms["current_time_min"]
                    ms["current_time_min"] += tool_change_min
                    ms["tool_changes"] += 1
                    ms["total_tool_time"] += tool_change_min
                    ms["schedule"].append({
                        "type": "tool_change",
                        "start_min": tc_start,
                        "end_min": ms["current_time_min"],
                        "start_time": (shift_start + timedelta(minutes=tc_start)).strftime("%H:%M"),
                        "end_time": (shift_start + timedelta(minutes=ms["current_time_min"])).strftime("%H:%M"),
                        "class": f"{ms['current_class'] if ms['current_class'] else 'Initial Setup'} → {cls}",
                        "fg_code": "—",
                        "duration_min": tool_change_min,
                    })
                
                ms["current_class"] = cls
                start = ms["current_time_min"]
                ms["current_time_min"] += prod_time_min
                ms["panels_produced"] += 1
                ms["total_prod_time"] += prod_time_min
                ms["schedule"].append({
                    "type": "production",
                    "start_min": start,
                    "end_min": ms["current_time_min"],
                    "start_time": (shift_start + timedelta(minutes=start)).strftime("%H:%M"),
                    "end_time": (shift_start + timedelta(minutes=ms["current_time_min"])).strftime("%H:%M"),
                    "class": cls,
                    "fg_code": panel["FG_Design_Code"],
                    "panel_id": panel["Panel_ID"],
                    "duration_min": round(prod_time_min, 2),
                })
            else:
                # Try to fit on another machine
                overflow = True
                for m2 in machines:
                    if m2 == best_machine:
                        continue
                    ms2 = machine_state[m2]
                    tc2 = tool_change_min if (ms2["current_class"] != cls) else 0
                    if ms2["current_time_min"] + tc2 + prod_time_min <= capacity_min:
                        if tc2 > 0:
                            tc_s = ms2["current_time_min"]
                            ms2["current_time_min"] += tool_change_min
                            ms2["tool_changes"] += 1
                            ms2["total_tool_time"] += tool_change_min
                            ms2["schedule"].append({
                                "type": "tool_change",
                                "start_min": tc_s,
                                "end_min": ms2["current_time_min"],
                                "start_time": (shift_start + timedelta(minutes=tc_s)).strftime("%H:%M"),
                                "end_time": (shift_start + timedelta(minutes=ms2["current_time_min"])).strftime("%H:%M"),
                                "class": f"{ms2['current_class'] if ms2['current_class'] else 'Initial Setup'} → {cls}",
                                "fg_code": "—",
                                "duration_min": tool_change_min,
                            })
                        ms2["current_class"] = cls
                        start = ms2["current_time_min"]
                        ms2["current_time_min"] += prod_time_min
                        ms2["panels_produced"] += 1
                        ms2["total_prod_time"] += prod_time_min
                        ms2["schedule"].append({
                            "type": "production",
                            "start_min": start,
                            "end_min": ms2["current_time_min"],
                            "start_time": (shift_start + timedelta(minutes=start)).strftime("%H:%M"),
                            "end_time": (shift_start + timedelta(minutes=ms2["current_time_min"])).strftime("%H:%M"),
                            "class": cls,
                            "fg_code": panel["FG_Design_Code"],
                            "panel_id": panel["Panel_ID"],
                            "duration_min": round(prod_time_min, 2),
                        })
                        overflow = False
                        break
                if overflow:
                    continue  # Skip panel if no machine can fit it
    
    # Calculate utilization
    results = {}
    for m in machines:
        ms = machine_state[m]
        utilization = (ms["total_prod_time"] / capacity_min * 100) if capacity_min > 0 else 0
        results[m] = {
            "schedule": ms["schedule"],
            "total_time_used": round(ms["current_time_min"], 2),
            "production_time": round(ms["total_prod_time"], 2),
            "tool_change_time": round(ms["total_tool_time"], 2),
            "idle_time": round(capacity_min - ms["current_time_min"], 2),
            "panels_produced": ms["panels_produced"],
            "tool_changes": ms["tool_changes"],
            "utilization_pct": round(utilization, 1),
            "capacity_min": capacity_min,
        }
    
    return results


def get_schedule_summary(schedule_results):
    """Get high-level summary of the schedule."""
    total_panels = sum(r["panels_produced"] for r in schedule_results.values())
    total_tool_changes = sum(r["tool_changes"] for r in schedule_results.values())
    avg_utilization = np.mean([r["utilization_pct"] for r in schedule_results.values()])
    total_idle = sum(r["idle_time"] for r in schedule_results.values())
    
    return {
        "total_panels_scheduled": total_panels,
        "total_tool_changes": total_tool_changes,
        "avg_utilization_pct": round(avg_utilization, 1),
        "total_idle_minutes": round(total_idle, 1),
        "machines_used": len(schedule_results),
    }


def schedule_to_dataframe(schedule_results):
    """Convert schedule to a flat DataFrame for export."""
    rows = []
    for machine, data in schedule_results.items():
        for entry in data["schedule"]:
            rows.append({
                "Machine": machine,
                "Type": entry["type"],
                "Start_Time": entry["start_time"],
                "End_Time": entry["end_time"],
                "Class": entry["class"],
                "FG_Code": entry["fg_code"],
                "Panel_ID": entry.get("panel_id", ""),
                "Duration_Min": entry["duration_min"],
            })
    return pd.DataFrame(rows)
