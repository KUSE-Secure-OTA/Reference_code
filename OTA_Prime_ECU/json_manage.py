#define VERSON 1.0
import json
import os
import shutil
import subprocess
from datetime import datetime
class JSON_manager():
    def __init__(self):
        self.path_versionList = None
        self.path_path_dict = "path_dict.json"
        self.path_historyList = "history/history.json"
        self.versionList = None #= self._load_json(self.path_versionList)
        self.path_dict = self._load_json(self.path_path_dict)
        self.updateList = None
        self.tmp_path = "history"
        self.path_updateFiles = "updateFiles/update_files"
        self.path_updateList = "updateFiles/update.json"
        self.historyList = self._load_json(self.path_historyList)

    def _load_json(self, json_path):
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            print(f"json file load ok: {json_path}")
            return data
        except FileNotFoundError:
            print(f"file not found : {json_path}")
            return {}
        except json.JSONDecodeError:
            print(f"json decode error : {json_path}")
            return {}

    def update_versionList(self):
        print(f"\n##### Update VersionList #####")
        '''
        versionList 업데이트, 없는건 추가
        '''

        for target in self.updateList:
            if target == "version":
                self.versionList["version"] = self.updateList[target]
                continue
            for file_name in self.updateList[target]:
                if file_name in self.versionList[target]:
                    self.versionList[target][file_name]["version"] = self.updateList[target][file_name]["version"]
                else:
                    self.versionList[target][file_name] = self.updateList[target][file_name]
        with open(self.path_versionList, "w", encoding="utf=8") as file:
            json.dump(self.versionList, file, indent=4, ensure_ascii=False)

    def check_target_is_new(self, directory):
        print(f"\n##### Check if Target '{directory}' is New #####")
        if directory in self.path_dict:
            print(f"\n##### Target '{directory}' already exists in path_dict #####")
            version_file_path = os.path.join(os.getcwd(),"files",directory,"versionList.json")
            self.versionList = self._load_json(version_file_path)
            self.path_versionList = version_file_path
            return
        print(f"##### Target '{directory}' not found. #####\n ##### Creating new directory and update #####")
        new_path = os.path.join(os.getcwd(),"files", directory)
        try:
            os.makedirs(new_path, exist_ok=True)
            self.path_dict[directory] = new_path
            with open(self.path_path_dict, "w", encoding="utf-8") as f:
                json.dump(self.path_dict, f, indent=4, ensure_ascii=False)
            print(f"##### Created directory at {new_path} #####")
            print(f"##### Updated path_dict.json with: {directory}")
            version_data = {
                "version": "0.0.0",
                directory: {}
            }
            version_file_path = os.path.join(new_path,"versionList.json")
            with open(version_file_path,"w", encoding="utf-8") as f:
                json.dump(version_data, f, indent=4, ensure_ascii=False)
            print(f"##### Created VersionList at {new_path} #####")
            print(f"##### Updated VersionList.json with: {directory}")
        except Exception as e:
            print(f"Failed to create new directory or update json : {e}")
        self.versionList = self._load_json(version_file_path)
        self.path_versionList = version_file_path

    def move_original_file_to_tmp(self):
        print(f"\n##### Move Original Files to Tmp #####")
        '''
        기존 파일들 tmp폴더로 이동, 이때tmp폴더의 이름은 기존 버전의 이름
        예, history/0.0.1
        참고로 저 폴더에 backup_list.json도 포함, 이는 변경점을 저장
        '''
        tmp_path = os.path.join(self.tmp_path, self.versionList["version"])
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        path_backup_version_list = os.path.join(tmp_path, "backup_list.json") 
        shutil.copy2(self.path_updateList, path_backup_version_list)
        backup_version_list = self._load_json(path_backup_version_list)
        for target in self.updateList:
            if target == "version":
                pass
            else:
                # move original file to tmp dir
                for file_name in self.updateList[target]:
                    if file_name not in self.versionList[target]:
                        continue
                    relative_path = self.updateList[target][file_name]["path"]
                    file_path = os.path.join(self.path_dict[target], relative_path)
                    target_path = os.path.join(tmp_path, file_name)
                    try:
                        shutil.copy2(file_path, target_path)
                        print(f"#### move file \t{file_path}->{target_path}")
                        backup_version_list[target][file_name]["version"] = self.versionList[target][file_name]["version"]
                    except:
                        print("\n%%%%% Move Original Files to Tmp %%%%%")
                        return False
        backup_version_list["version"] = self.versionList["version"]
        self.historyList[self.versionList["version"]] = {"changed2" : self.updateList["version"], "date" : datetime.now().isoformat()}
        with open(path_backup_version_list, "w", encoding = "utf-8") as file:
            json.dump(backup_version_list, file, indent=4, ensure_ascii=False)
        with open(self.path_historyList, "w", encoding = "utf-8") as file:
            json.dump(self.historyList, file, indent = 4, ensure_ascii=False)
        return True
                    
    def move_update_file_to_ws(self):
        print(f"\n##### Move Update Files to Workspace #####")
        '''
        업데이트 파일들을 경로에 맞게 ws로 이동
        '''
        for target in self.updateList:
            if target == "version":
                pass
            else:
                for file_name in self.updateList[target]:
                    relative_path = self.updateList[target][file_name]["path"]
                    target_path = os.path.join(self.path_dict[target],relative_path)
                    file_path = os.path.join(self.path_updateFiles, file_name)
                    os.makedirs(os.path.dirname(target_path),exist_ok=True)
                    print(f"try move {file_path} to {target_path}")
                    try:
                        shutil.copy2(file_path, target_path)
                    except:
                        print("\n%%%%% Move Update Files to Workspace Error %%%%%")
                        return False
        return True
    
    def build_update_file(self, rollback):
        print(f"\n##### Build Update Files #####")
        for target in self.updateList:
            if target == "version":
                continue
            build_dir = os.path.join(self.path_dict[target],"build")
            if os.path.exists(build_dir):
                shutil.rmtree(build_dir)    
            os.makedirs(build_dir)
            subprocess.run(["cmake", ".."], cwd=build_dir, check=False)
            result = subprocess.run(["make", "-j4"], cwd=build_dir, capture_output=True, text=True)
            if result.returncode == 0:
                print("result code ok")
                if not rollback:
                    self.update_versionList()
                    so_file = self.find_so_file(build_dir)
                    handler_update_list = {
                        "IC_files": [
                            {
                                "name": target,
                                "type": "exec"
                            },
                            {
                                "name": os.path.basename(so_file),
                                "type": "lib"
                            }
                        ]
                    }
                    path_handler_update_list = os.path.join(build_dir, "list.json")
                    with open(path_handler_update_list,"w", encoding="utf-8") as f:
                        json.dump(handler_update_list, f, indent=4, ensure_ascii=False)
                    try:
                        shutil.copy2(os.path.join(build_dir, target), "/home/ota/Documents/handler_tcp_client/update")
                        shutil.copy2(so_file, "/home/ota/Documents/handler_tcp_client/update")
                        shutil.copy2(path_handler_update_list, "/home/ota/Documents/handler_tcp_client/update")
                        print(f"Move file Success {path_handler_update_list} ->")
                        pass
                    except:
                        print(f"File Move Failed")
                        pass
                return True
            else:
                print("result code false")
                return False


    def roll_back(self, version):
        print(f"\n##### Roll Back ####")
        path_backup_version_list = os.path.join(self.tmp_path, version,"backup_list.json")
        backup_version_list = self._load_json(path_backup_version_list)
        for target in backup_version_list:
            if target == "version":
                pass
            else:
                for file_name in backup_version_list[target]:
                    relative_path = backup_version_list[target][file_name]["path"]
                    target_path = os.path.join(self.path_dict[target], relative_path)
                    file_path = os.path.join(self.tmp_path, version, file_name)
                    try:
                        shutil.copy2(file_path, target_path)
                        print(f"{file_path} -> {target_path}")
                    except:
                        print("\n%%%%% Roll Back Error %%%%%")
                        return False
        self.historyList[self.updateList["version"]] = {"changed2" : backup_version_list["version"], "date" : datetime.now().isoformat()}
        with open(path_backup_version_list, "w", encoding = "utf-8") as file:
            json.dump(backup_version_list, file, indent=4, ensure_ascii=False)
        with open(self.path_historyList, "w", encoding = "utf-8") as file:
            json.dump(self.historyList, file, indent = 4, ensure_ascii=False)

        return True

    def find_so_file(self, directory):
        for filename in os.listdir(directory):
            if filename.endswith(".so") or ".so." in filename:
                return os.path.join(directory, filename)
