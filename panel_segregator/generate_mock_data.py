import pandas as pd
import random
import json
import os

def generate_mock_data(num_sheets=80):
    sheet_data = []
    
    # We define a few "standard" panel sizes to create a realistic mix
    # We want sheets dedicated to large, medium, and small panels so the sorting works beautifully
    size_categories = [
        {"name": "Extra Large", "l_range": (2000, 2400), "w_range": (1000, 1200)},
        {"name": "Large", "l_range": (1500, 1900), "w_range": (800, 950)},
        {"name": "Medium", "l_range": (1000, 1400), "w_range": (500, 750)},
        {"name": "Small", "l_range": (400, 900), "w_range": (200, 450)},
    ]
    
    types = ["Thermal", "Non-Thermal"]
    
    for i in range(1, num_sheets + 1):
        sheet_id = f"SHT-{i:03d}"
        
        # Pick a dominant size category for this sheet
        cat = random.choice(size_categories)
        num_panels = random.randint(2, 6) # panels per sheet
        
        panels_on_sheet = []
        max_area = 0
        
        for p in range(num_panels):
            # 80% chance to be the dominant size, 20% to be slightly smaller
            if random.random() < 0.8:
                length = random.randint(cat["l_range"][0], cat["l_range"][1])
                width = random.randint(cat["w_range"][0], cat["w_range"][1])
            else:
                # Pick a random smaller category
                smaller_cats = [c for c in size_categories if c["l_range"][0] < cat["l_range"][0]]
                if smaller_cats:
                    scat = random.choice(smaller_cats)
                    length = random.randint(scat["l_range"][0], scat["l_range"][1])
                    width = random.randint(scat["w_range"][0], scat["w_range"][1])
                else:
                    length = random.randint(cat["l_range"][0], cat["l_range"][1])
                    width = random.randint(cat["w_range"][0], cat["w_range"][1])
            
            p_type = random.choice(types)
            part_name = f"PN-{length}x{width}-{p_type[0]}"
            area = (length * width) / 1000000.0 # sqm
            
            if area > max_area:
                max_area = area
                
            panels_on_sheet.append({
                "Part Name": part_name,
                "Length": length,
                "Width": width,
                "Type": p_type,
                "Area": round(area, 3)
            })
            
        sheet_data.append({
            "Sheet ID": sheet_id,
            "Total Panels": num_panels,
            "Dominant Size": cat["name"],
            "Max Panel Area": round(max_area, 3),
            "Panels JSON": json.dumps(panels_on_sheet)
        })
        
    df = pd.DataFrame(sheet_data)
    
    output_path = os.path.join(os.path.dirname(__file__), "sample_sheets_3d.xlsx")
    df.to_excel(output_path, index=False)
    print(f"Successfully generated {num_sheets} mock nested sheets for 3D stacking to {output_path}")

if __name__ == "__main__":
    generate_mock_data()
