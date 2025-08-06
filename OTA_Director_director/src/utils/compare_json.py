import json

def compare_and_update_json(output_json, received_json, update_json):
    # output.json을 읽어들입니다
    with open(output_json, "r", encoding="utf-8") as f:
        output_data = json.load(f)

    # received_data.json을 읽어들입니다
    with open(received_json, "r", encoding="utf-8") as f:
        received_data = json.load(f)

    # output_data와 received_data 비교하여 변경된 항목만 남깁니다.
    update_data = {
        "version": output_data["version"],  # output.json의 version을 그대로 유지
        "TestABC": {}
    }

    # 'TestABC' 항목 비교
    for filename, output_file_info in output_data["TestABC"].items():
        if filename in received_data["TestABC"]:
            received_file_info = received_data["TestABC"][filename]
            
            # 버전이 다르거나 경로가 다른 경우에만 update_data에 저장
            if output_file_info["version"] != received_file_info["version"] or output_file_info["path"] != received_file_info["path"]:
                update_data["TestABC"][filename] = output_file_info

    # 변경된 항목만 포함된 update_data를 update.json에 저장
    with open(update_json, "w", encoding="utf-8") as f:
        json.dump(update_data, f, indent=4, ensure_ascii=False)

    print(f"Comparison completed. Changes have been saved to '{update_json}'.")

# 사용 예시
if __name__ == "__main__":
    output_json = "/home/seame/ota_publisher/publisher/output.json"  # output.json 파일 경로
    received_json = "/home/seame/ota_publisher/publisher/received.json"  # received_data.json 파일 경로
    update_json = "/home/seame/ota_publisher/publisher/update.json"  # 결과를 저장할 update.json 파일 경로

    compare_and_update_json(output_json, received_json, update_json)
