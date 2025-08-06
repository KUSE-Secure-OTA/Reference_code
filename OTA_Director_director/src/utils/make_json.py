import os
import json
import re

def extract_version_from_text(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            match = re.search(r"v?(\d+\.\d+\.\d+)", first_line, re.IGNORECASE)
            return match.group(1) if match else "0.0.0"
    except Exception:
        return "0.0.0"

def compare_versions(v1, v2):
    return tuple(map(int, v1.split("."))) > tuple(map(int, v2.split(".")))

def target_to_json(root_dir, output_file):
    result = {}
    base_dir = os.path.basename(root_dir)
    max_version = "0.0.0"
    
    for dirpath, _, filenames in os.walk(root_dir):
        if "build" in dirpath.split(os.sep):
            continue
        
        for filename in filenames:
            if filename == "CMakeLists.txt.user":
                continue
            
            rel_path = os.path.relpath(os.path.join(dirpath, filename), root_dir)
            file_path = os.path.join(dirpath, filename)
            
            if filename.lower().endswith(".jpg"):
                version = "0.0.1"
            else:
                version = extract_version_from_text(file_path)
            
            result[filename] = {"path": rel_path, "version": version}
            
            if compare_versions(version, max_version):
                max_version = version

    final_result = {
        "version": max_version,
        base_dir: result
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_result, f, indent=4, ensure_ascii=False)




# 예제 실행
target_to_json("../../TestABC", "output.json")
