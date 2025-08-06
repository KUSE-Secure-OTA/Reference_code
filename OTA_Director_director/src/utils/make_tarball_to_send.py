import json
import os
import tarfile
import shutil

def create_update_archive(update_json_path, source_dir, output_archive):
    # update.json 읽기
    with open(update_json_path, "r", encoding="utf-8") as f:
        update_data = json.load(f)
    
    # 업데이트할 파일 목록 가져오기
    base_dir = list(update_data.keys())[1]  # "TestABC" 같은 루트 키 가져오기
    file_entries = update_data[base_dir]  # 변경된 파일 정보
    
    # update_files 폴더 생성
    update_files_dir = "update_files"
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

# 사용 예시
update_json_path = "update.json"  # update.json 경로
source_dir = "src_add/TestABC"  # 기준 폴더 (update.json의 path 기준)
output_archive = "update.tar.xz"  # 출력 압축 파일명

create_update_archive(update_json_path, source_dir, output_archive)
