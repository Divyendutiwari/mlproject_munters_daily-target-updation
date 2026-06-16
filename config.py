"""
Munters Panel Production Planning System - Configuration
=========================================================
Central configuration for all system parameters.
"""

import os

# ─────────────────────────────────────────────────────────────
# FILE PATHS
# ─────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Input Excel paths (override via environment variables)
PANEL_DATASET_PATH = os.environ.get(
    "MUNTERS_PANEL_DATA",
    r"C:\Users\divye\Downloads\Munters_Panel_Dataset_500.xlsx"
)
THERMAL_TIMING_PATH = os.environ.get(
    "MUNTERS_THERMAL_TIMING",
    r"C:\Users\divye\Downloads\Thermal_Plate_FINAL .xlsx"
)
NON_THERMAL_TIMING_PATH = os.environ.get(
    "MUNTERS_NON_THERMAL_TIMING",
    r"C:\Users\divye\Downloads\NON-THERMAL_Cycle_Study.xlsx"
)

# Database
DATABASE_PATH = os.path.join(DATA_DIR, "munters_production.db")

# ─────────────────────────────────────────────────────────────
# PRODUCTION PARAMETERS
# ─────────────────────────────────────────────────────────────
SHIFT_DURATION_MINUTES = 450          # Total shift duration
UTILIZATION_FACTOR = 0.90             # 90% productive utilization
EFFECTIVE_CAPACITY_MINUTES = SHIFT_DURATION_MINUTES * UTILIZATION_FACTOR  # 405 min
TOOL_CHANGE_TIME_MINUTES = 17        # Minutes per tool change

# ─────────────────────────────────────────────────────────────
# MACHINE CONFIGURATION
# ─────────────────────────────────────────────────────────────
MACHINES = ["BM1", "BM2", "BM3"]
SHIFT_START_TIME = "08:00"

# ─────────────────────────────────────────────────────────────
# CLASSIFICATION PARAMETERS
# ─────────────────────────────────────────────────────────────
AREA_GROUPS = ["XS", "S", "M", "L", "XL", "XXL"]
LENGTH_GROUPS = ["Short", "Medium", "Long"]

# Area group percentile boundaries (6 bins)
AREA_PERCENTILES = [0, 16.67, 33.33, 50.0, 66.67, 83.33, 100.0]

# Length group percentile boundaries (3 bins)
LENGTH_PERCENTILES = [0, 33.33, 66.67, 100.0]

# ─────────────────────────────────────────────────────────────
# PRODUCTION TIMING (seconds) - From actual study data
# ─────────────────────────────────────────────────────────────
# Thermal panels: 8-bend + 4-bend combined timing by size
THERMAL_TIMING_BY_SIZE = {
    "Small": 99.0,       # 1:39
    "Medium": 117.44,    # 1:57
    "YLarge": 163.0,     # 2:43 (¥Large)
    "Large": 157.75,     # 2:38
    "XLarge": 206.0,     # 3:26
}
THERMAL_MEAN_TIME_SEC = 134.06  # Overall mean

# Non-Thermal panels: Net bend time
NON_THERMAL_MEAN_TIME_SEC = 33.38       # Mean net bend time
NON_THERMAL_WITH_FITMENT_SEC = 48.38    # Mean with fitment
NON_THERMAL_XXL_TIME_SEC = 75.0         # Assumed: 1 min 15 sec

# ─────────────────────────────────────────────────────────────
# ML PARAMETERS
# ─────────────────────────────────────────────────────────────
RANDOM_STATE = 42
TEST_SIZE = 0.2
CV_FOLDS = 5

# GridSearchCV parameters for XGBoost
XGBOOST_PARAM_GRID = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7, 9],
    'learning_rate': [0.01, 0.05, 0.1, 0.2],
    'subsample': [0.8, 0.9, 1.0],
    'colsample_bytree': [0.8, 0.9, 1.0],
    'min_child_weight': [1, 3, 5],
    'gamma': [0, 0.1, 0.2],
}

# Lighter grid for faster training (used when time is limited)
XGBOOST_FAST_GRID = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.05, 0.1, 0.2],
    'subsample': [0.8, 1.0],
    'colsample_bytree': [0.8, 1.0],
    'min_child_weight': [1, 3],
}

# Random Forest parameters
RF_PARAM_GRID = {
    'n_estimators': [100, 200, 300],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
}

# ─────────────────────────────────────────────────────────────
# FLASK CONFIGURATION
# ─────────────────────────────────────────────────────────────
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = True
