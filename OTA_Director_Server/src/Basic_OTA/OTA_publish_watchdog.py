import os
import time
import json
import paho.mqtt.client as mqtt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import base64
import tarfile
import shutil
from utils.json_handler import JsonHandler

class FileHandler:
    def __init__(self, mqtt_broker, mqtt_port, watch_dir, files_path, topic_from_client):
        self.MQTT_BROKER = mqtt_broker
        self.MQTT_PORT = mqtt_port
        self.WATCH_DIR = watch_dir
        self.files_path = files_path
        self.topic_from_client = topic_from_client
        self.MQTT_NOTIFY_TOPIC = "file/added"
        self.MQTT_FILE_TOPIC = "file/files"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        # MQTT 설정
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # 파일 감시 설정
        self.observer = Observer()
        self.event_handler = FileChangeHandler(self.client, self.MQTT_NOTIFY_TOPIC, self.WATCH_DIR)
        self.observer.schedule(self.event_handler, self.WATCH_DIR, recursive=False)

        # jsonmanager
        self.json_handler = JsonHandler()

    def connect_mqtt(self):
        self.client.connect(self.MQTT_BROKER, self.MQTT_PORT, 60)

    def start_watching(self):
        print(f"Watching directory: {self.WATCH_DIR}")
        self.observer.start()

    def stop_watching(self):
        self.observer.stop()

    def loop_mqtt(self):
        self.client.loop_start()


    def encode_files(self, json_path):
        with open(json_path, "rb") as files_file:
            encoded_files = base64.b64encode(files_file.read())
            return encoded_files

    def on_connect(self, client, userdata, flags, rc, topic):
        print(f"Connected: {rc}")
        client.subscribe(self.topic_from_client)

    def on_message(self, client, userdata, msg):
        output_json = "../data/output.json"  # output.json 파일 경로
        received_json = "../data/received.json"  # received_data.json 파일 경로
        update_json = "../data/update.json"
        src_path = "../src_add/TestABC"
        output_archive = "../data/update.tar.xz"
        # MQTT에서 받은 메시지를 출력
        print(f"Received message: {msg.payload.decode()}")
        
        # 받은 메시지를 JSON 형식으로 파싱
        try:
            json_data = json.loads(msg.payload.decode())
            # JSON 데이터를 파일로 저장
            with open("../data/received.json", "w", encoding="utf-8") as json_file:
                json.dump(json_data, json_file, indent=4, ensure_ascii=False)
            print("Data saved to '../data/received.json'.")

            self.json_handler.compare_and_update_json(output_json, received_json, update_json)
            self.json_handler.create_update_tarball(update_json, src_path, output_archive)


        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")

        encoded_files = self.encode_files(self.files_path)
        client.publish(self.MQTT_FILE_TOPIC, encoded_files)
        print("Image sent to MQTT broker.")



class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, client, mqtt_notify_topic, watch_dir):
        self.client = client
        self.MQTT_NOTIFY_TOPIC = mqtt_notify_topic
        self.watch_dir = watch_dir
        self.json_handler = JsonHandler()

    def on_created(self, event):
        if event.is_directory:  # 디렉토리가 생성될 때만 처리
            foldername = os.path.basename(event.src_path)
            print(f"New directory detected: {foldername}")

            # MQTT 메시지 전송
            message = json.dumps({"event": "directory_added", "directory": foldername})
            self.client.publish(self.MQTT_NOTIFY_TOPIC, message)

            # 디렉토리 내부의 파일들을 JSON으로 저장
            print(f"Running directory_to_json for {event.src_path}")
            self.json_handler.target_to_json(event.src_path, "../data/output.json")
            print("directory_to_json executed.")



# 사용 예시
if __name__ == "__main__":
    # MQTT 설정
    MQTT_BROKER = "192.168.86.67"  # 또는 MQTT 서버 IP
    MQTT_PORT = 1883

    # 감시할 디렉토리 설정
    WATCH_DIR = "../src_add"  # 감시할 폴더 경로 변경 필요

    # 파일 경로 및 MQTT 클라이언트 설정
    files_path = "../data/update.tar.xz"
    topic_from_client = "option/option"
    
    
    # 파일 처리 객체 생성 및 MQTT 연결
    file_handler = FileHandler(MQTT_BROKER, MQTT_PORT, WATCH_DIR, files_path, topic_from_client)
    file_handler.connect_mqtt()
    
    # MQTT 및 파일 감시 시작
    file_handler.start_watching()
    file_handler.loop_mqtt()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        file_handler.stop_watching()
        file_handler.client.loop_stop()
    file_handler.observer.join()
