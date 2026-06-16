"""
Database Module
================
SQLite database for persisting production data and schedules.
"""
import sqlite3
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def get_connection():
    os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
    return sqlite3.connect(config.DATABASE_PATH)


def init_database():
    """Create all required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fg_design_code TEXT,
            length_mm REAL,
            breadth_mm REAL,
            area_mm2 REAL,
            panel_type TEXT,
            area_group TEXT,
            length_group TEXT,
            production_class TEXT,
            production_time_sec REAL,
            product_family TEXT,
            machine_group TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine TEXT,
            entry_type TEXT,
            start_time TEXT,
            end_time TEXT,
            production_class TEXT,
            fg_code TEXT,
            duration_min REAL,
            schedule_date DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS machine_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine TEXT,
            total_time_used REAL,
            production_time REAL,
            tool_change_time REAL,
            idle_time REAL,
            panels_produced INTEGER,
            tool_changes INTEGER,
            utilization_pct REAL,
            schedule_date DATE DEFAULT CURRENT_DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT,
            r2_score REAL,
            mae REAL,
            rmse REAL,
            best_params TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("[DB] Database initialized successfully")


def save_panels(df):
    conn = get_connection()
    cols = ["FG_Design_Code", "Length_mm", "Breadth_mm", "Area_mm2", "Panel_Type",
            "Area_Group", "Length_Group", "Production_Class", "Production_Time_Sec",
            "Product_Family", "Machine_Group"]
    existing = [c for c in cols if c in df.columns]
    df_save = df[existing].copy()
    df_save.columns = [c.lower() for c in df_save.columns]
    
    cursor = conn.cursor()
    cursor.execute("DELETE FROM panels")
    df_save.to_sql("panels", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    print(f"[DB] Saved {len(df)} panels to database")


def save_schedule(schedule_results):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedules")
    cursor.execute("DELETE FROM machine_stats")
    
    for machine, data in schedule_results.items():
        for entry in data["schedule"]:
            cursor.execute("""
                INSERT INTO schedules (machine, entry_type, start_time, end_time,
                    production_class, fg_code, duration_min)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (machine, entry["type"], entry["start_time"], entry["end_time"],
                  entry["class"], entry["fg_code"], entry["duration_min"]))
        
        cursor.execute("""
            INSERT INTO machine_stats (machine, total_time_used, production_time,
                tool_change_time, idle_time, panels_produced, tool_changes, utilization_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (machine, data["total_time_used"], data["production_time"],
              data["tool_change_time"], data["idle_time"], data["panels_produced"],
              data["tool_changes"], data["utilization_pct"]))
    
    conn.commit()
    conn.close()
    print("[DB] Schedule saved to database")


def save_ml_metrics(metrics):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ml_metrics")
    for name, m in metrics.items():
        params = str(m.get("best_params", ""))
        cursor.execute("""
            INSERT INTO ml_metrics (model_name, r2_score, mae, rmse, best_params)
            VALUES (?, ?, ?, ?, ?)
        """, (name, m["r2"], m["mae"], m["rmse"], params))
    conn.commit()
    conn.close()


def load_panels():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM panels", conn)
    conn.close()
    return df


def load_schedule():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM schedules ORDER BY machine, id", conn)
    conn.close()
    return df


def load_machine_stats():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM machine_stats", conn)
    conn.close()
    return df
