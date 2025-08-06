import os
import time
import json
import paho.mqtt.client as mqtt
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import base64
import tarfile
import shutil
import ssl
import hashlib
from utils.json_handler import JsonHandler
from utils.signature.pub_signature import make_payload_with_signature
from utils.signature.sub_signature import verify_signature
from flask import Flask, request, send_from_directory
import threading
import requests

class FileHandler:
    def __init__(self, mqtt_broker, mqtt_port, watch_dir, files_path):
        self.MQTT_BROKER = mqtt_broker
        self.MQTT_PORT = mqtt_port
        self.WATCH_DIR = watch_dir
        self.files_path = files_path

        self.MQTT_NOTIFY_TOPIC = "notify/director"
        self.json_from_client = "file/current_json" #option/option
        self.MQTT_NOTIFY_DIRECTOR_TOPIC = "director/updateList"

        self.permission_to_client = "permission/client"
        self.permission_from_client = "permission/server"
        self.rollback_ropic = "rollback"
        self.MQTT_FILE_TOPIC = "file/files"

        self.output_json = "../data/output.json"  # output.json 파일 경로
        self.received_json = "../data/received.json"  # received_data.json 파일 경로
        self.update_json = "../data/update.json"
        self.target_path = "../src_add/"
        self.output_archive = "../data/update.tar.xz"

        self.ca_cert = "./utils/certs/ca.crt"
        self.client_cert = "./utils/certs/client.crt"
        self.client_key = "./utils/certs/client.key"

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        #configure_tls(self.client, self.ca_cert, self.client_cert, self.client_key)
        
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
        client.subscribe(self.json_from_client)
        client.subscribe(self.permission_from_client)
        client.subscribe(self.MQTT_NOTIFY_DIRECTOR_TOPIC)

        try:
            session = client._sock
            if session:
                tls_session = session.session
                session_id = client._sock.session.id  # type: bytes
                session_hash = hashlib.sha256(session_id).hexdigest()

                print(f"🔐 TLS Session ID: {tls_session.id.hex()}")
                print(f"🔐 TLS Session ID: {session_id}     ID Hash: {session_hash}")
        except Exception as e:
            print(f"⚠️ Failed to retrieve session ID: {e}")

    def on_message(self, client, userdata, msg):
        if verify_signature(msg.payload):
            payload_data = json.loads(msg.payload.decode('utf-8'))
            
            if msg.topic == self.MQTT_NOTIFY_DIRECTOR_TOPIC:
                print(f"file/current_json: {msg.payload.decode()}")
                try:
                    useful_data = {
                        k: v for k, v in payload_data.items()
                        if k not in ["timestamp", "signature"]
                    }
                    keys = list(useful_data.keys())
                    if len(keys) >= 2:
                        target_dir = keys[1]
                        final_target_path = os.path.join(self.target_path, target_dir)

                    # JSON 데이터를 파일로 저장
                    with open(self.update_json, "w", encoding="utf-8") as json_file:
                        json.dump(useful_data, json_file, indent=4, ensure_ascii=False)

                    print("✅ Data saved to '../data/received.json' (cleaned).")
                    self.json_handler.create_update_tarball(self.update_json, final_target_path, self.output_archive)

                except json.JSONDecodeError as e:
                    print(f"Failed to decode JSON: {e}")

                print("=" * 50, "\n\n", "Transfer Update List")
                #update_message = self.encode_files(self.update_json)

                with open(self.update_json, "r") as f:
                    message = json.load(f)

                message["reset"] = False
                update_payload = make_payload_with_signature(message)

                try:
                    result = client.publish(self.permission_to_client, update_payload, qos=1, retain=True)
                    print("Pulbilsh result:  ", result.rc)

                except:
                    print("PUB FAIL")
                print("permission to client sent")

            elif msg.topic =="permission/server":
                print("permission/client: ",payload_data["update"])
                if payload_data["update"]:
                    print("=" * 50, "\n\n", "Update New Files")

                    upload_url = "http://localhost:5000/upload"
                    with open(self.files_path, 'rb') as f:
                        files = {'file': ('update.tar.xz', f)}
                        res = requests.post(upload_url, files=files)
                    download_url = res.json()['url']
                    print("📡 Upload complete, download URL:", download_url)
                    message = {}
                    message["url"] = download_url
                    url_payload = make_payload_with_signature(message)
                    # encoded_files = self.encode_files(self.files_path)
                    # file_message = {"encoded_files": encoded_files.decode()}
                    #file_payload = make_payload_with_signature(file_message)
                    
                    client.publish(self.MQTT_FILE_TOPIC, url_payload, qos=2)
                    
                    print("=" * 50, "\n\n", "Reset the Broker")
                    message = {}
                    message["reset"] = True
                    reset_payload = make_payload_with_signature(message)
                    client.publish(self.permission_to_client, reset_payload, qos=1, retain=True)

                else:
                    pass

        else:
            print("\n##### Verification Fail #####")

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
            # message = json.dumps({"event": "directory_added", "directory": foldername})
            print("=" * 50, "\n\n", "Notify New Update")

            # 디렉토리 내부의 파일들을 JSON으로 저장
            print(f"Running directory_to_json for {event.src_path}")
            self.json_handler.target_to_json(event.src_path, "../data/output.json")
            with open("../data/output.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            message = {"event": "directory_added", "directory": foldername, "file": data}
            notify_payload = make_payload_with_signature(message)
            self.client.publish(self.MQTT_NOTIFY_TOPIC, notify_payload, qos=1)


            print("directory_to_json executed.")



            

def configure_tls(client, ca_cert, client_cert, client_key):
    client.tls_set(
        ca_certs= ca_cert,
        certfile= client_cert,
        keyfile= client_key,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    client.tls_insecure_set(False)

# 사용 예시
if __name__ == "__main__":
    # ================================= Flask 서버 설정 =================================
    app = Flask(__name__)
    UPLOAD_FOLDER = "./uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    @app.route('/upload', methods=['POST'])
    def upload_file():
        file = request.files['file']
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        print(f"✅ File saved at: {filepath} ({os.path.getsize(filepath)} bytes)")
        return {"url": f"http://192.168.86.182:5000/download/{file.filename}"}, 200

    @app.route('/download/<filename>', methods=['GET'])
    def download_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    # ===== Flask 서버를 백그라운드 스레드로 실행 =====
    def run_server():
        app.run(host="0.0.0.0", port=5000)
    # ================================= Flask 서버 설정 끝 =================================

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # MQTT 설정
    MQTT_BROKER = "192.168.86.182"  # 또는 MQTT 서버 IP
    MQTT_PORT = 1883

    # 감시할 디렉토리 설정
    WATCH_DIR = "../src_add"  # 감시할 폴더 경로 변경 필요

    # 파일 경로 및 MQTT 클라이언트 설정
    files_path = "../data/update.tar.xz"
    
    # 파일 처리 객체 생성 및 MQTT 연결
    file_handler = FileHandler(MQTT_BROKER, MQTT_PORT, WATCH_DIR, files_path)
    file_handler.connect_mqtt()
    
    # MQTT 및 파일 감시 시작
    file_handler.start_watching()
    file_handler.loop_mqtt()

    try:
        while True:
            print("-")
            time.sleep(1)
    except KeyboardInterrupt:
        file_handler.stop_watching()
        file_handler.client.loop_stop()
    file_handler.observer.join()
