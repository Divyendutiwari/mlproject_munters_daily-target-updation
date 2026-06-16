"""
Munters Panel Production Planning - Flask Application
======================================================
Main web application serving the dashboard.
"""
import sys, os, json, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify, request, send_file
import pandas as pd
import numpy as np
from datetime import datetime

import config
from data_loader import load_panel_dataset, load_machine_uptime, load_thermal_timing, load_non_thermal_timing, enrich_dataset
from classifier import classify_panels, assign_production_time, get_class_timing_map
from scheduler import create_schedule, get_schedule_summary, schedule_to_dataframe
from ml_engine import ProductionMLEngine

from database import init_database, save_panels, save_schedule, save_ml_metrics

app = Flask(__name__)

# Global data store
APP_DATA = {}

def initialize_system(data_path=None):
    """Run the full pipeline: load, classify, ML, schedule, save."""
    print("\n" + "="*60)
    print("  MUNTERS PRODUCTION PLANNING SYSTEM - INITIALIZING")
    print("="*60)
    
    # 1. Initialize database
    init_database()
    
    # 2. Load data
    print("\n--- STEP 1: Loading Data ---")
    df = load_panel_dataset(data_path)
    machines = load_machine_uptime(data_path)
    thermal_timing = load_thermal_timing()
    non_thermal_timing = load_non_thermal_timing()
    
    # 3. Enrich dataset
    print("\n--- STEP 2: Enriching Dataset ---")
    df = enrich_dataset(df)
    
    # 4. Classify panels
    print("\n--- STEP 3: Classifying Panels ---")
    df, area_bounds, length_bounds = classify_panels(df)
    
    # 5. Assign production times
    print("\n--- STEP 4: Assigning Production Times ---")
    df = assign_production_time(df, thermal_timing, non_thermal_timing)
    
    # Initialize live status tracking
    df["Status"] = "Pending"
    
    # 6. Train or Load ML models
    print("\n--- STEP 5: ML Models ---")
    ml_engine = ProductionMLEngine()
    ml_metrics = None
    if os.path.exists(os.path.join(config.MODELS_DIR, "metrics.pkl")):
        ml_metrics = ml_engine.load_models()
        
    if not ml_metrics:
        print("  [ML] Training new models...")
        ml_metrics = ml_engine.train_and_optimize(df, use_fast_grid=True)
    
    # 7. Generate schedule
    print("\n--- STEP 6: Generating Machine Schedule ---")
    schedule_results = create_schedule(df)
    schedule_summary = get_schedule_summary(schedule_results)
    
    # 8. Save to database
    print("\n--- STEP 7: Saving to Database ---")
    save_panels(df)
    save_schedule(schedule_results)
    save_ml_metrics(ml_metrics)
    
    # 9. Store in memory
    APP_DATA["df"] = df
    APP_DATA["machines"] = machines
    APP_DATA["area_bounds"] = area_bounds
    APP_DATA["length_bounds"] = length_bounds
    APP_DATA["schedule"] = schedule_results
    APP_DATA["schedule_summary"] = schedule_summary
    APP_DATA["ml_metrics"] = ml_metrics
    APP_DATA["ml_engine"] = ml_engine
    APP_DATA["thermal_timing"] = thermal_timing
    APP_DATA["non_thermal_timing"] = non_thermal_timing
    APP_DATA["class_timing"] = get_class_timing_map(df)
    
    print("\n" + "="*60)
    print("  [OK] SYSTEM INITIALIZED SUCCESSFULLY")
    print(f"  Panels: {len(df)} | Classes: {df['Production_Class'].nunique()}")
    print(f"  Scheduled: {schedule_summary['total_panels_scheduled']} panels")
    print(f"  Tool Changes: {schedule_summary['total_tool_changes']}")
    print(f"  Avg Utilization: {schedule_summary['avg_utilization_pct']}%")
    print("="*60 + "\n")


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/kpis")
def api_kpis():
    df = APP_DATA["df"]
    ss = APP_DATA["schedule_summary"]
    ml = APP_DATA["ml_metrics"]
    best_model = APP_DATA["ml_engine"].best_model_name
    
    return jsonify({
        "total_orders": len(df),
        "thermal_panels": int((df["Panel_Type"] == "Thermal").sum()),
        "non_thermal_panels": int((df["Panel_Type"] == "Non-Thermal").sum()),
        "total_classes": int(df["Production_Class"].nunique()),
        "total_scheduled": ss["total_panels_scheduled"],
        "total_tool_changes": ss["total_tool_changes"],
        "avg_utilization": ss["avg_utilization_pct"],
        "total_idle_min": ss["total_idle_minutes"],
        "best_model": best_model,
        "best_r2": round(ml[best_model]["r2"] * 100, 2),
        "best_mae": round(ml[best_model]["mae"], 2),
        "shift_capacity": config.EFFECTIVE_CAPACITY_MINUTES,
    })


@app.route("/api/class_distribution")
def api_class_distribution():
    df = APP_DATA["df"]
    class_stats = df.groupby("Production_Class").agg(
        count=("FG_Design_Code", "count"),
        avg_area=("Area_mm2", "mean"),
        avg_length=("Length_mm", "mean"),
        avg_time=("Production_Time_Sec", "mean"),
        total_time=("Production_Time_Sec", "sum"),
    ).reset_index()
    class_stats.columns = ["class_name", "panel_count", "avg_area", "avg_length", "avg_time_sec", "total_time_sec"]
    class_stats["avg_area"] = class_stats["avg_area"].round(0).astype(int)
    class_stats["avg_time_sec"] = class_stats["avg_time_sec"].round(1)
    class_stats["total_time_min"] = (class_stats["total_time_sec"] / 60).round(1)
    return jsonify(class_stats.to_dict(orient="records"))


@app.route("/api/schedule")
def api_schedule():
    schedule = APP_DATA["schedule"]
    result = {}
    for machine, data in schedule.items():
        result[machine] = {
            "schedule": data["schedule"],
            "stats": {
                "total_time_used": data["total_time_used"],
                "production_time": data["production_time"],
                "tool_change_time": data["tool_change_time"],
                "idle_time": data["idle_time"],
                "panels_produced": data["panels_produced"],
                "tool_changes": data["tool_changes"],
                "utilization_pct": data["utilization_pct"],
                "capacity_min": data["capacity_min"],
            }
        }
    return jsonify(result)


@app.route("/api/charts/area_distribution")
def api_area_dist():
    df = APP_DATA["df"]
    thermal = df[df["Panel_Type"] == "Thermal"]["Area_mm2"].tolist()
    non_thermal = df[df["Panel_Type"] == "Non-Thermal"]["Area_mm2"].tolist()
    return jsonify({"thermal": thermal, "non_thermal": non_thermal})


@app.route("/api/charts/panel_type_split")
def api_panel_split():
    df = APP_DATA["df"]
    counts = df["Panel_Type"].value_counts().to_dict()
    return jsonify(counts)


@app.route("/api/charts/class_counts")
def api_class_counts():
    df = APP_DATA["df"]
    counts = df["Production_Class"].value_counts().to_dict()
    return jsonify(counts)


@app.route("/api/charts/machine_utilization")
def api_machine_util():
    schedule = APP_DATA["schedule"]
    result = {}
    for machine, data in schedule.items():
        result[machine] = {
            "production": data["production_time"],
            "tool_change": data["tool_change_time"],
            "idle": data["idle_time"],
            "utilization": data["utilization_pct"],
        }
    return jsonify(result)


@app.route("/api/charts/gantt")
def api_gantt():
    schedule = APP_DATA["schedule"]
    df = APP_DATA["df"]
    gantt_data = []
    for machine, data in schedule.items():
        for entry in data["schedule"]:
            status = "Pending"
            if entry["type"] == "production":
                match = df.loc[df["Panel_ID"] == entry["panel_id"], "Status"]
                if len(match) > 0:
                    status = match.iloc[0]
            gantt_data.append({
                "machine": machine,
                "type": entry["type"],
                "start": entry["start_min"],
                "end": entry["end_min"],
                "class": entry["class"],
                "fg_code": entry["fg_code"],
                "panel_id": entry.get("panel_id", ""),
                "duration": entry["duration_min"],
                "status": status,
            })
    return jsonify(gantt_data)


@app.route("/api/gantt_classes")
def api_gantt_classes():
    """Return class-level info with completion status for the Gantt controls."""
    df = APP_DATA["df"]
    schedule = APP_DATA["schedule"]
    scheduled_classes = set()
    for machine, data in schedule.items():
        for entry in data["schedule"]:
            if entry["type"] == "production":
                scheduled_classes.add(entry["class"])
    class_info = []
    for cls in sorted(scheduled_classes):
        cls_df = df[df["Production_Class"] == cls]
        total = len(cls_df)
        completed = int((cls_df["Status"] == "Completed").sum())
        class_info.append({
            "class_name": cls,
            "total_panels": int(total),
            "completed": completed,
            "pending": int(total - completed),
            "is_completed": completed == total,
            "avg_time_sec": round(cls_df["Production_Time_Sec"].mean(), 1),
            "total_time_min": round(cls_df["Production_Time_Sec"].sum() / 60, 1),
            "panel_type": "Thermal" if cls.startswith("Thermal") else "Non-Thermal",
        })
    return jsonify(class_info)


@app.route("/api/mark_class_completed", methods=["POST"])
def api_mark_class_completed():
    """Mark ALL panels of a given production class as Completed."""
    data = request.json
    class_name = data.get("class_name")
    if not class_name:
        return jsonify({"success": False, "message": "Missing class_name"}), 400
    df = APP_DATA["df"]
    mask = df["Production_Class"] == class_name
    count = int(mask.sum())
    if count == 0:
        return jsonify({"success": False, "message": f"No panels found for class {class_name}"}), 404
    df.loc[mask, "Status"] = "Completed"
    APP_DATA["df"] = df
    return jsonify({"success": True, "count": count, "message": f"{count} panels of class '{class_name}' marked completed"})


@app.route("/api/download_class_excel/<path:class_name>")
def api_download_class_excel(class_name):
    """Download an Excel file containing all panels of a specific class."""
    df = APP_DATA["df"]
    class_df = df[df["Production_Class"] == class_name].copy()
    if class_df.empty:
        return jsonify({"error": f"No panels found for class '{class_name}'"}), 404
    export_cols = ["Panel_ID", "FG_Design_Code", "Panel_Type", "Length_mm", "Breadth_mm",
                   "Area_mm2", "Area_Group", "Length_Group", "Production_Class",
                   "Production_Time_Sec", "Production_Time_Min", "Status"]
    existing = [c for c in export_cols if c in class_df.columns]
    class_df = class_df[existing]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        class_df.to_excel(writer, index=False, sheet_name=class_name[:31])
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True, download_name=f"{class_name}_panels.xlsx")


@app.route("/api/ml_metrics")
def api_ml_metrics():
    ml = APP_DATA["ml_engine"]
    return jsonify({
        "comparison": ml.get_model_comparison(),
        "best_model": ml.best_model_name,
        "metrics": {
            name: {
                "r2": round(m["r2"], 4),
                "mae": round(m["mae"], 2),
                "rmse": round(m["rmse"], 2),
            }
            for name, m in ml.metrics.items()
        }
    })


@app.route("/api/box_simulation")
def api_box_simulation():
    df = APP_DATA["df"]
    ab = APP_DATA["area_bounds"]
    
    boxes = []
    for ag in config.AREA_GROUPS:
        lo, hi = ab[ag]
        avg_area = (lo + hi) / 2
        # Scale box size proportionally
        max_area = ab["XXL"][1]
        scale = (avg_area / max_area) ** 0.5  # sqrt for visual proportionality
        
        thermal_count = len(df[(df["Area_Group"] == ag) & (df["Panel_Type"] == "Thermal")])
        non_thermal_count = len(df[(df["Area_Group"] == ag) & (df["Panel_Type"] == "Non-Thermal")])
        
        boxes.append({
            "group": ag,
            "scale": round(scale, 3),
            "area_range": f"{lo:,.0f} - {hi:,.0f}",
            "thermal_count": thermal_count,
            "non_thermal_count": non_thermal_count,
            "total": thermal_count + non_thermal_count,
        })
    
    return jsonify(boxes)


@app.route("/api/mark_completed", methods=["POST"])
def api_mark_completed():
    data = request.json
    panel_id = data.get("panel_id")
    if panel_id:
        df = APP_DATA["df"]
        df.loc[df["Panel_ID"] == panel_id, "Status"] = "Completed"
        APP_DATA["df"] = df
        return jsonify({"success": True, "message": f"Panel {panel_id} marked completed"})
    return jsonify({"success": False, "message": "Missing panel_id"}), 400


@app.route("/api/reschedule", methods=["POST"])
def api_reschedule():
    df = APP_DATA["df"]
    pending_df = df[df["Status"] == "Pending"].copy()
    if pending_df.empty:
        return jsonify({"success": False, "message": "No pending panels to reschedule"}), 400
    print(f"\n[LIVE] Rescheduling {len(pending_df)} pending panels...")
    schedule_results = create_schedule(pending_df)
    schedule_summary = get_schedule_summary(schedule_results)
    APP_DATA["schedule"] = schedule_results
    APP_DATA["schedule_summary"] = schedule_summary
    save_schedule(schedule_results)
    return jsonify({"success": True, "summary": schedule_summary})


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part in the request"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400
        
    if file and (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        filepath = os.path.join(config.UPLOAD_FOLDER, filename)
        
        try:
            file.save(filepath)
            print(f"\n[UPLOAD] New data file uploaded: {filepath}")
            # Reinitialize the system with the new data
            initialize_system(data_path=filepath)
            return jsonify({"success": True, "message": "File uploaded and system successfully re-initialized."})
        except Exception as e:
            print(f"[UPLOAD ERROR] {str(e)}")
            return jsonify({"success": False, "message": f"Error processing file: {str(e)}"}), 500
    else:
        return jsonify({"success": False, "message": "Invalid file format. Please upload an Excel file (.xlsx)"}), 400


if __name__ == "__main__":
    initialize_system()
    print(f"\n>> Dashboard running at http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=False)
