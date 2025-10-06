import json

import os

def extract_final_content(json_path):
    # Print the resolved absolute path for debugging
    abs_path = os.path.abspath(json_path)
    print(f"[DEBUG] Attempting to open: {abs_path}")

    if not os.path.exists(json_path):
        print(f"[ERROR] File does not exist: {abs_path}")
        return None

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Try the top-level "content" field first
    if "content" in data and isinstance(data["content"], str):
        return data["content"]

    # If not found, search for the deepest "content" field in nested dicts
    def find_deepest_content(obj):
        if isinstance(obj, dict):
            if "content" in obj and isinstance(obj["content"], str):
                return obj["content"]
            for v in obj.values():
                result = find_deepest_content(v)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = find_deepest_content(item)
                if result:
                    return result
        return None

    return find_deepest_content(data)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python extract_content.py <path_to_json>")
        sys.exit(1)
    content = extract_final_content(sys.argv[1])
    if content:
        print(content)
    else:
        print("No content found.")