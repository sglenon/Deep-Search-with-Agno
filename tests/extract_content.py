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

    if len(sys.argv) != 4:
        print("Usage: uv run extract_content.py <json_file> <output_dir> <output_file_name>")
        sys.exit(1)

    json_file = sys.argv[1]
    output_dir = sys.argv[2]
    output_file_name = sys.argv[3]

    content = extract_final_content(json_file)
    if content:
        # Ensure output_dir exists
        os.makedirs(output_dir, exist_ok=True)
        # Ensure .md extension
        if not output_file_name.lower().endswith(".md"):
            output_file_name += ".md"
        output_path = os.path.join(output_dir, output_file_name)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[INFO] Markdown file saved to: {output_path}")
    else:
        print("No content found.")