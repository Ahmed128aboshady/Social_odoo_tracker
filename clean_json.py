import json
import math

def clean_nans(obj):
    if isinstance(obj, list):
        return [clean_nans(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

try:
    with open("leads.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    clean_data = clean_nans(data)
    
    with open("leads.json", "w", encoding="utf-8") as f:
        json.dump(clean_data, f, ensure_ascii=False, indent=2)
    
    print("leads.json successfully cleaned and rewritten with valid JSON nulls.")
except Exception as e:
    print(f"Error cleaning JSON: {e}")
