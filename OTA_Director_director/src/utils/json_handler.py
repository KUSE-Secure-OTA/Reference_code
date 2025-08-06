import os
import time
import json
import base64
import tarfile
import shutil
import re
    
class JsonHandler:
    def __init__(self):
        pass

    def extract_version_from_text(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                match = re.search(r"v?(\d+\.\d+\.\d+)", first_line, re.IGNORECASE)
                return match.group(1) if match else "0.0.0"
        except Exception:
            return "0.0.0"

    def compare_versions(self, v1, v2):
        return tuple(map(int, v1.split("."))) > tuple(map(int, v2.split(".")))

    def target_to_json(self, root_dir, output_file):
        result = {}
        base_dir = os.path.basename(root_dir)
        max_version = "0.0.0"
        num_file = 0
        image_files = {}

        for dirpath, _, filenames in os.walk(root_dir):
            if "build" in dirpath.split(os.sep):
                continue
            
            for filename in filenames:
                if filename == "CMakeLists.txt.user":
                    continue
                
                rel_path = os.path.relpath(os.path.join(dirpath, filename), root_dir)
                file_path = os.path.join(dirpath, filename)
                
                if filename.lower().endswith((".jpg", ".png", ".svg")):
                    image_files[filename] = {"fpath": rel_path, "fname": filename}
                    
                else:
                    try:
                        version = self.extract_version_from_text(file_path)
                        num_file += 1
                    except:
                        print("extract version from text error : ", file_path)
                result[filename] = {"path": rel_path, "version": version}
                
                if self.compare_versions(version, max_version):
                    max_version = version

        for img in image_files:
            result[img] = {"path": image_files[img]["fpath"], "version": max_version}

        final_result = {
            "version": max_version,
            base_dir: result
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_result, f, indent=4, ensure_ascii=False)
        print("total number of files : ",num_file)

    def compare_and_update_json(self, output_json, received_json, target_dir, update_json):
        # output.json을 읽어들입니다
        with open(output_json, "r", encoding="utf-8") as f:
            output_data = json.load(f)

        # received_data.json을 읽어들입니다
        with open(received_json, "r", encoding="utf-8") as f:
            received_data = json.load(f)

        # output_data와 received_data 비교하여 변경된 항목만 남깁니다.
        update_data = {
            "version": output_data["version"],  # output.json의 version을 그대로 유지
            target_dir: {}
        }

        # 업데이트 디렉터리 항목 비교
        if target_dir not in output_data.keys():
            print(f"\nThis directory is not in update: {target_dir}")
            return 0

        for filename, output_file_info in output_data[target_dir].items():
            if filename in received_data[target_dir]:
                received_file_info = received_data[target_dir][filename]
                
                # 버전이 다르거나 경로가 다른 경우에만 update_data에 저장
                if output_file_info["version"] != received_file_info["version"] or output_file_info["path"] != received_file_info["path"]:
                    update_data[target_dir][filename] = output_file_info
            else:
                # output.json에 있고 received.json에 없는 새로운 파일 추가
                update_data[target_dir][filename] = output_file_info

        # 변경된 항목만 포함된 update_data를 update.json에 저장
        with open(update_json, "w", encoding="utf-8") as f:
            json.dump(update_data, f, indent=4, ensure_ascii=False)

        print(f"Comparison completed. Changes have been saved to '{update_json}'.")
        return 1


    def create_update_tarball(self, update_json_path, source_dir, output_archive):
        # update.json 읽기
        with open(update_json_path, "r", encoding="utf-8") as f:
            update_data = json.load(f)
        
        # 업데이트할 파일 목록 가져오기
        base_dir = list(update_data.keys())[1]  # "IC_someip" 같은 루트 키 가져오기
        file_entries = update_data[base_dir]  # 변경된 파일 정보
        
        # update_files 폴더 생성
        update_files_dir = "../data/update_files"
        if os.path.exists(update_files_dir):
            shutil.rmtree(update_files_dir)  # 기존 폴더 삭제
        os.makedirs(update_files_dir)
        
        # 파일을 update_files 폴더로 복사
        for file_info in file_entries.values():
            file_path = os.path.join(source_dir, file_info["path"])
            if os.path.exists(file_path):
                dest_path = os.path.join(update_files_dir,os.path.basename(file_info["path"]))
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(file_path, dest_path)  # 원본 속성 유지 복사
            else:
                print(f"경고: {file_path} 파일이 존재하지 않습니다.")
        
        # update.json도 복사
        # shutil.copy2(update_json_path, update_files_dir)
        
        # tar.xz 파일로 압축
        with tarfile.open(output_archive, "w:xz") as tar:
            tar.add(update_files_dir, arcname=os.path.basename(update_files_dir))
            tar.add(update_json_path, arcname=os.path.basename(update_json_path))
        
        print(f"{output_archive} 생성 완료!")


