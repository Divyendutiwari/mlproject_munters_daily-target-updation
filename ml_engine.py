"""
ML Module - Production Time Prediction & Optimization
======================================================
Uses XGBoost + GridSearchCV for optimal production predictions.
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor
import joblib
import warnings
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

warnings.filterwarnings("ignore")


class ProductionMLEngine:
    """ML engine for production time prediction and optimization."""
    
    def __init__(self):
        self.models = {}
        self.best_model = None
        self.best_model_name = None
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_cols = None
        self.metrics = {}
    
    def prepare_features(self, df):
        """Prepare feature matrix for ML training."""
        df_ml = df.copy()
        
        # Encode categorical variables
        cat_cols = ["Panel_Type", "Area_Group", "Length_Group", "Production_Class", "Product_Family"]
        for col in cat_cols:
            if col in df_ml.columns:
                le = LabelEncoder()
                df_ml[f"{col}_encoded"] = le.fit_transform(df_ml[col].astype(str))
                self.label_encoders[col] = le
        
        # Feature columns
        self.feature_cols = [
            "Length_mm", "Breadth_mm", "Area_mm2", "Is_Thermal",
            "Aspect_Ratio", "Perimeter_mm",
            "Panel_Type_encoded", "Area_Group_encoded", "Length_Group_encoded",
            "Product_Family_encoded",
        ]
        
        # Only use columns that exist
        self.feature_cols = [c for c in self.feature_cols if c in df_ml.columns]
        
        X = df_ml[self.feature_cols].values
        y = df_ml["Production_Time_Sec"].values
        
        return X, y, df_ml
    
    def train_and_optimize(self, df, use_fast_grid=True):
        """Train multiple models with GridSearchCV and select the best."""
        print("\n" + "="*60)
        print("  ML TRAINING PIPELINE - Production Time Prediction")
        print("="*60)
        
        X, y, df_ml = self.prepare_features(df)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=config.TEST_SIZE, random_state=config.RANDOM_STATE
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        print(f"\n[ML] Training set: {X_train.shape[0]} samples")
        print(f"[ML] Test set: {X_test.shape[0]} samples")
        print(f"[ML] Features: {len(self.feature_cols)}")
        
        # --- Model 1: XGBoost with GridSearchCV ---
        print("\n>> Training XGBoost with GridSearchCV...")
        param_grid = config.XGBOOST_FAST_GRID if use_fast_grid else config.XGBOOST_PARAM_GRID
        
        xgb = XGBRegressor(random_state=config.RANDOM_STATE, verbosity=0)
        grid_xgb = GridSearchCV(
            xgb, param_grid, cv=config.CV_FOLDS,
            scoring="r2", n_jobs=-1, verbose=0
        )
        grid_xgb.fit(X_train_scaled, y_train)
        
        xgb_best = grid_xgb.best_estimator_
        xgb_pred = xgb_best.predict(X_test_scaled)
        xgb_r2 = r2_score(y_test, xgb_pred)
        xgb_mae = mean_absolute_error(y_test, xgb_pred)
        xgb_rmse = np.sqrt(mean_squared_error(y_test, xgb_pred))
        
        print(f"  Best params: {grid_xgb.best_params_}")
        print(f"  R² Score: {xgb_r2:.4f}")
        print(f"  MAE: {xgb_mae:.2f} sec")
        print(f"  RMSE: {xgb_rmse:.2f} sec")
        
        self.models["XGBoost"] = xgb_best
        self.metrics["XGBoost"] = {"r2": xgb_r2, "mae": xgb_mae, "rmse": xgb_rmse, "best_params": grid_xgb.best_params_}
        
        # --- Model 2: Random Forest with GridSearchCV ---
        print("\n>> Training Random Forest with GridSearchCV...")
        rf = RandomForestRegressor(random_state=config.RANDOM_STATE)
        grid_rf = GridSearchCV(
            rf, config.RF_PARAM_GRID, cv=config.CV_FOLDS,
            scoring="r2", n_jobs=-1, verbose=0
        )
        grid_rf.fit(X_train_scaled, y_train)
        
        rf_best = grid_rf.best_estimator_
        rf_pred = rf_best.predict(X_test_scaled)
        rf_r2 = r2_score(y_test, rf_pred)
        rf_mae = mean_absolute_error(y_test, rf_pred)
        rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
        
        print(f"  Best params: {grid_rf.best_params_}")
        print(f"  R² Score: {rf_r2:.4f}")
        print(f"  MAE: {rf_mae:.2f} sec")
        print(f"  RMSE: {rf_rmse:.2f} sec")
        
        self.models["RandomForest"] = rf_best
        self.metrics["RandomForest"] = {"r2": rf_r2, "mae": rf_mae, "rmse": rf_rmse, "best_params": grid_rf.best_params_}
        
        # --- Model 3: Gradient Boosting ---
        print("\n>> Training Gradient Boosting...")
        gb = GradientBoostingRegressor(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            random_state=config.RANDOM_STATE
        )
        gb.fit(X_train_scaled, y_train)
        gb_pred = gb.predict(X_test_scaled)
        gb_r2 = r2_score(y_test, gb_pred)
        gb_mae = mean_absolute_error(y_test, gb_pred)
        gb_rmse = np.sqrt(mean_squared_error(y_test, gb_pred))
        
        print(f"  R² Score: {gb_r2:.4f}")
        print(f"  MAE: {gb_mae:.2f} sec")
        print(f"  RMSE: {gb_rmse:.2f} sec")
        
        self.models["GradientBoosting"] = gb
        self.metrics["GradientBoosting"] = {"r2": gb_r2, "mae": gb_mae, "rmse": gb_rmse}
        
        # --- Select Best Model ---
        best_name = max(self.metrics, key=lambda k: self.metrics[k]["r2"])
        self.best_model = self.models[best_name]
        self.best_model_name = best_name
        
        print(f"\n{'='*60}")
        print(f"  * BEST MODEL: {best_name}")
        print(f"    R² = {self.metrics[best_name]['r2']:.4f}")
        print(f"    MAE = {self.metrics[best_name]['mae']:.2f} sec")
        print(f"    RMSE = {self.metrics[best_name]['rmse']:.2f} sec")
        print(f"{'='*60}")
        
        # Cross-validation on best model
        cv_scores = cross_val_score(self.best_model, X_train_scaled, y_train, cv=5, scoring="r2")
        print(f"\n[CV] 5-Fold Cross-Validation R2: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")
        self.metrics[best_name]["cv_mean"] = cv_scores.mean()
        self.metrics[best_name]["cv_std"] = cv_scores.std()
        
        # Feature importance
        if hasattr(self.best_model, "feature_importances_"):
            importances = self.best_model.feature_importances_
            feat_imp = sorted(
                zip(self.feature_cols, importances),
                key=lambda x: x[1], reverse=True
            )
            print("\n[ML] Feature Importance:")
            for feat, imp in feat_imp:
                print(f"  {feat}: {imp:.4f}")
            self.metrics[best_name]["feature_importance"] = dict(feat_imp)
        
        # Save models
        self.save_models()
        
        return self.metrics
    
    def predict(self, df):
        """Predict production times for new data."""
        X, _, _ = self.prepare_features(df)
        X_scaled = self.scaler.transform(X)
        predictions = self.best_model.predict(X_scaled)
        return predictions
    
    def save_models(self):
        """Save trained models to disk."""
        os.makedirs(config.MODELS_DIR, exist_ok=True)
        for name, model in self.models.items():
            path = os.path.join(config.MODELS_DIR, f"{name}_model.pkl")
            joblib.dump(model, path)
        joblib.dump(self.scaler, os.path.join(config.MODELS_DIR, "scaler.pkl"))
        joblib.dump(self.label_encoders, os.path.join(config.MODELS_DIR, "label_encoders.pkl"))
        joblib.dump(self.feature_cols, os.path.join(config.MODELS_DIR, "feature_cols.pkl"))
        joblib.dump(self.metrics, os.path.join(config.MODELS_DIR, "metrics.pkl"))
        print(f"\n[ML] Models saved to {config.MODELS_DIR}")
        
    def load_models(self):
        """Load trained models from disk."""
        print(f"\n[ML] Loading models from {config.MODELS_DIR}...")
        try:
            self.scaler = joblib.load(os.path.join(config.MODELS_DIR, "scaler.pkl"))
            self.label_encoders = joblib.load(os.path.join(config.MODELS_DIR, "label_encoders.pkl"))
            self.feature_cols = joblib.load(os.path.join(config.MODELS_DIR, "feature_cols.pkl"))
            self.metrics = joblib.load(os.path.join(config.MODELS_DIR, "metrics.pkl"))
            
            for name in ["XGBoost", "RandomForest", "GradientBoosting"]:
                path = os.path.join(config.MODELS_DIR, f"{name}_model.pkl")
                if os.path.exists(path):
                    self.models[name] = joblib.load(path)
            
            self.best_model_name = max(self.metrics, key=lambda k: self.metrics[k]["r2"])
            self.best_model = self.models[self.best_model_name]
            print(f"[ML] Successfully loaded {len(self.models)} models. Best: {self.best_model_name}")
            return self.metrics
        except Exception as e:
            print(f"[ML] Error loading models: {e}")
            return None
    
    def get_model_comparison(self):
        """Return model comparison data for dashboard."""
        return {
            name: {
                "r2": round(m["r2"] * 100, 2),
                "mae": round(m["mae"], 2),
                "rmse": round(m["rmse"], 2),
            }
            for name, m in self.metrics.items()
        }
