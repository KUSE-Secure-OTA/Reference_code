import sys
import threading
import time
import base64
import json
import tarfile
import ssl
import hashlib
from ecdsa import VerifyingKey, BadSignatureError
import paho.mqtt.client as mqtt
from utils.OTA_GUI import show_update_gui
from utils.signature.sub_signature import verify_signature
from utils.signature.pub_signature import make_payload_with_signature
from json_manage import JSON_manager
import requests
import os

brokerIp = "192.168.86.22"
port = 8883
topic_from_server_notify = "file/added"
topic_from_server_files = "file/files"
topic_to_server = "file/current_json"
topic_permission_client = "permission/client"
topic_permission_server = "permission/server"
topic_versionList = "primary/version"
topic_requestImage = "primary/requestMeta"
topic_updateList = "director/updateMeta"
topic_imageMeta = "image/metaData"
unzip_path = "updateFiles"
json_manager = JSON_manager()

event = threading.Event()


def load_updateList():
    print("load_updateList")
    with tarfile.open("received_update.tar.gz", "r:xz") as tar:
        tar.extractall(path=unzip_path)
    json_manager.updateList = json_manager._load_json(unzip_path + "/update.json")
    print("load_updateList success")



def check_and_build_function(event):
    while True:
        event.wait()
        print("\n##### Load Update List #####")
        if json_manager.move_original_file_to_tmp():
            print("\n##### Move Original Files to Tmp Success #####")
            if json_manager.move_update_file_to_ws():
                print("\n##### Move Update Files to Workspace Success #####")
                if json_manager.build_update_file(rollback=False):
                    print("\n##### Build Success #####")
                else:
                    print("\n%%%%% Build Failed, Try Roll Back %%%%%")
                    lastVersion = list(json_manager.historyList.keys())[-1]
                    print(f"\n##### Latest Version Found, Latest Version: {lastVersion}")
                    if json_manager.roll_back(lastVersion):
                        print(f"\n##### Roll Back Success, Roll Back to {lastVersion} Version #####")
                        if json_manager.build_update_file(rollback=True):
                            print("\n##### Roll Back Build Success #####")
                        else:
                            print("\n%%%%% Roll Back Build Failed %%%%%")
                    else:
                        print("\n%%%%% Roll Back Failed %%%%%")
            else:
                print("\n%%%%% Move Update Files to Workspace Failed %%%%%")
        else:
            print("\n%%%%% Move Original Files to Tmp Failed %%%%%")
        time.sleep(5)
        event.clear()


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")

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

    client.subscribe(topic_from_server_notify)
    client.subscribe(topic_from_server_files)
    client.subscribe(topic_permission_client)
    client.subscribe(topic_updateList)
    client.subscribe(topic_imageMeta)


def on_message(client, userdata, msg):
    if verify_signature(msg.payload):
        payload = json.loads(msg.payload.decode())

        if msg.topic == topic_updateList:
            print("\nReceive Update List from Director Repo\n")

            update_path = "./update_target.json"
            with open(update_path, "w") as f:
                json.dump(payload, f, indent=4)

            print("\nSave the update list\n")

            request_payload = make_payload_with_signature({"request": True})
            client.publish(topic_requestImage, request_payload, qos=1)

        elif msg.topic == topic_imageMeta:
            print("\nReceive Metadata from Image Repo\n")

            meta_path = "./image_target.json"
            with open(meta_path, "w") as f:
                json.dump(payload, f, indent=4)

            print("\nSave the meta data\n")

            with open("./update_target.json", "r", encoding="utf-8") as f:
                director_data = json.load(f)

            with open("./image_target.json", "r", encoding="utf-8") as f:
                image_data = json.load(f)


            for directory, files in director_data.items():
                if directory in ["version", "url", "timestamp", "signature"]:
                    continue

                print(f"\nUpdate Directory: {directory}")
                image_files = image_data.get(directory, {})
                director_hash = None
                image_hash = None
                print(f"\nFiles:    {files}")

                for filename, info in files.items():
                    with open("./utils/signature/director_public.pem", "rb") as f:
                        vk = VerifyingKey.from_pem(f.read())

                    hash_bytes = base64.b64decode(info["sha256"])
                    signature_bytes = base64.b64decode(info["signature"])
                    
                    try:
                        vk.verify(signature_bytes, hash_bytes)
                        director_hash = hash_bytes
                        print("\n##### Director Signature verified successfully. #####")
                    except BadSignatureError:
                        print("\n%%%%%% Director Signature verification failed: Bad signature. %%%%%")   

                    image_file = image_files.get(filename)

                    if image_file:
                        with open("./utils/signature/image_public.pem", "rb") as f:
                            vk = VerifyingKey.from_pem(f.read())

                        hash_bytes = base64.b64decode(image_file["sha256"])
                        signature_bytes = base64.b64decode(image_file["signature"])
                        
                        try:
                            vk.verify(signature_bytes, hash_bytes)
                            image_hash = hash_bytes
                            print("\n##### Image Signature verified successfully. #####")
                        except BadSignatureError:
                            print("\n%%%%%% Image Signature verification failed: Bad signature. %%%%%")

                        if director_hash == image_hash:
                            print("\nIntegrity is right\n")
                        else:
                            print(f"\nFail to integrity test: {filename}\n")

                    else:
                        print(f"\nThis file is not in Image Repo: {filename}")

    else:
        print("\n##### Verification Fail #####\n")



def ask_update_permission(client):
    def yes_callback():
        print("Permission granted. Start update now.")
        callback_payload = make_payload_with_signature({"update": True})
        client.publish(topic_permission_server, callback_payload, qos=2)

    def no_callback(wait_time):
        print(f"Permission denied. Will ask again in {wait_time} sec.")
        timer = threading.Timer(wait_time, lambda: ask_update_permission(client))
        timer.start()

    show_update_gui(yes_callback, no_callback)

# 브로커에 남아있는 retained 메시지를 초기화하는 함수
def clear_retained_message(client, topic):
    client.publish(topic, payload="", qos=0, retain=True)
    print(f"Cleared retained message on topic: {topic}")

def configure_tls(client):
    client.tls_set(
        ca_certs="./utils/certs/ca.crt",
        certfile="./utils/certs/mqtt_client.crt",
        keyfile="./utils/certs/mqtt_client.key",
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    client.tls_insecure_set(False)

if __name__ == "__main__":
    # OTA Build Thread
    build_thread = threading.Thread(target=check_and_build_function, args=(event,), daemon=True)
    build_thread.start()

    # MQTT Client
    client = mqtt.Client()
    configure_tls(client)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(brokerIp, port, 60)
    clear_retained_message(client, topic_permission_client)
    client.loop_start()

    try:
        with open("./versionList.json", "r") as f:
            data = json.load(f)
        print(f"Version List load OK")
    except Exception as e:
        print(f"Version List load Error:    {e}")
    
    verList_payload = make_payload_with_signature(data)
    client.publish(topic_versionList, verList_payload, qos=1)
    print("\nSend Current Version\n")

    # Main thread 유지용 (대기)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()

