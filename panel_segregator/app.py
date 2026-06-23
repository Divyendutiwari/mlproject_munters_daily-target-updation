from flask import Flask, render_template, jsonify
import pandas as pd
import json
import os

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "sample_sheets_3d.xlsx")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/optimize-sequence", methods=["GET"])
def optimize_sequence():
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "Data file not found"}), 404
        
    try:
        df = pd.read_excel(DATA_PATH)
        
        # Original Unoptimized Sequence
        original_queue = df.to_dict(orient="records")
        for row in original_queue:
            row["Panels"] = json.loads(row.pop("Panels JSON"))
        
        # Optimized Sequence: Sort by Max Panel Area descending
        # This guarantees largest panels get processed first, building a stable stacked pyramid.
        df_optimized = df.sort_values(by=["Max Panel Area"], ascending=[False])
        optimized_queue = df_optimized.to_dict(orient="records")
        for row in optimized_queue:
            row["Panels"] = json.loads(row.pop("Panels JSON"))
            
        return jsonify({
            "status": "success",
            "original_queue": original_queue,
            "optimized_queue": optimized_queue
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5001)
