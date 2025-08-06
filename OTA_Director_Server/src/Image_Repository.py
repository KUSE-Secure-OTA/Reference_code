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
from ecdsa import SigningKey
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

        self.MQTT_REQUEST_TOPIC = "primary/requestMeta"
        self.MQTT_META_TOPIC = "image/metaData"

        self.ca_cert = "./utils/certs/ca.crt"
        self.client_cert = "./utils/certs/mqtt_client.crt"
        self.client_key = "./utils/certs/mqtt_client.key"

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        configure_tls(self.client, self.ca_cert, self.client_cert, self.client_key)
        
        # MQTT 설정
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # 파일 감시 설정
        self.observer = Observer()
        self.event_handler = FileChangeHandler(self.client, self.WATCH_DIR)
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
        client.subscribe(self.MQTT_REQUEST_TOPIC)

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
            
            if msg.topic == self.MQTT_REQUEST_TOPIC:
                print("\nRequest Meta Data from Primary ECU\n")

                with open("./data/target_image.json", "r", encoding="utf-8") as f:
                    data = json.load(f)

                upload_url = "https://localhost:443/upload"
                with open(self.files_path, 'rb') as f:
                    files = {'file': ('update_image.tar.xz', f)}
                    res = requests.post(upload_url, files=files, verify="./utils/certs/https_server.crt")
                download_url = res.json()['url']
                print("📡 Upload complete, download URL:", download_url)
                data["url"] = download_url
                
                meta_payload = make_payload_with_signature(data)
                client.publish(self.MQTT_META_TOPIC, meta_payload, qos=2)

        else:
            print("\n##### Verification Fail #####")

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, client, watch_dir):
        self.client = client
        self.watch_dir = watch_dir
        self.json_handler = JsonHandler()

    def on_created(self, event):
        if event.is_directory:  # 디렉토리가 생성될 때만 처리
            TARGET_PATH =  "../data/target_new.json"
            PRIVATE_KEY_PATH = "./utils/signature/private.pem"

            with open(TARGET_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            for folder_name, files in data.items():
                if folder_name == "version":
                    continue

                folder_path = os.path.join(self.watch_dir, folder_name)

                for file_name, file_info in files.items():
                    relative_path = file_info.get("path")
                    full_path = os.path.join(folder_path, relative_path)

                    if not os.path.exists(full_path):
                        print(f"No file:    {full_path}")
                        continue

                    try:
                        with open(full_path, "rb") as f:
                            content = f.read()

                        file_hash = hashlib.sha256(content).digest()
                        hash_data = base64.b64encode(file_hash).decode('utf-8')
                        file_info["sha256"] = hash_data
                        sk = SigningKey.from_pem(open("./utils/signature/image_private.pem").read())
                        signature = sk.sign(file_hash)
                        sign_data = base64.b64encode(signature).decode('utf-8')
                        file_info["signature"] = sign_data
                        print(f"Signature:  {file_name}")

                    except Exception as e:
                        print(f"Error in {file_name}:   {e}")

                print("\nSuccess Sign all files")

            with open("./data/target_image.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            created_dir = self.watch_dir #event.src_path
            output_tar_path = "./data/update_image.tar.xz"

            #compress_dir_path = os.path.join("../Image_Repo/", )
            self.json_handler.create_new_update_tarball("./data/target_image.json", created_dir, output_tar_path)

            

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
        return {"url": f"https://192.168.86.115:443/download/{file.filename}"}, 200

    @app.route('/download/<filename>', methods=['GET'])
    def download_file(filename):
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    # ===== Flask 서버를 백그라운드 스레드로 실행 =====
    def run_server():
        context = ('./utils/certs/https_server.crt', './utils/certs/https_server.key')
        app.run(host="0.0.0.0", port=443, ssl_context=context)
    # ================================= Flask 서버 설정 끝 =================================

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # MQTT 설정
    MQTT_BROKER = "192.168.86.37"  # 또는 MQTT 서버 IP
    MQTT_PORT = 8883

    # 감시할 디렉토리 설정
    WATCH_DIR = "../Image_Repo"  # 감시할 폴더 경로 변경 필요

    # 파일 경로 및 MQTT 클라이언트 설정
    files_path = "./data/update_image.tar.xz"
    
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
