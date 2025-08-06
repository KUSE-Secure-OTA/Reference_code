import os
import time
import json
import hashlib
import ssl
import base64
from ecdsa import SigningKey
import paho.mqtt.client as mqtt
from utils.json_handler import JsonHandler
from utils.signature.pub_signature import make_payload_with_signature
from utils.signature.sub_signature import verify_signature

class DirectorRepoHandler:
    def __init__(self, broker, port):
        self.MQTT_BROKER = broker
        self.MQTT_PORT = port

        self.update_meta_topic = "director/updateMeta"
        self.notify_version_topic = "primary/version"

        self.update_json = "../data/update.json"
        self.target_meta = "../data/target_new.json"

        self.ca_cert = "./utils/certs/ca.crt"
        self.client_cert = "./utils/certs/mqtt_client.crt"
        self.client_key = "./utils/certs/mqtt_client.key"

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        configure_tls(self.client, self.ca_cert, self.client_cert, self.client_key)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.json_handler = JsonHandler()

    def connect_mqtt(self):
        self.client.connect(self.MQTT_BROKER, self.MQTT_PORT, 60)

    def loop_mqtt(self):
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[DirectorRepo] Connected: {rc}")
        client.subscribe(self.notify_version_topic)

    def on_message(self, client, userdata, msg):
        if verify_signature(msg.payload):
            payload = json.loads(msg.payload.decode())

            if msg.topic == self.notify_version_topic:
                print("\nReceive Version List from Primary ECU\n")

                version_path = "./versionList.json"
                with open(version_path, "w") as f:
                    json.dump(payload, f, indent=4)

                print("\nSave the version list\n")

                try:
                    keys = list(payload.keys())
                    update_num = 0
                    all_result = {}
                    max_version = "0.0.0"

                    if len(keys) >= 2:
                        for i in range(2,len(keys)-2):
                            target_dir = keys[i]
                            tmp_num = update_num
                            update_num += self.json_handler.compare_and_update_json(self.target_meta, version_path, target_dir, self.update_json)
                            
                            if update_num != tmp_num:
                                with open(self.update_json, "rb") as f:
                                    data = json.load(f)

                                for folder_name, files in data.items():
                                    if folder_name == "version":
                                        continue

                                    for file_name, file_info in files.items():
                                        file_hash = file_info.get("sha256", "")
                                        if not file_hash:
                                            print(f"{file_name} - No signature")
                                            continue

                                        try:
                                            message_bytes = base64.b64decode(file_hash)
                                            sk = SigningKey.from_pem(open("./utils/signature/director_private.pem").read())
                                            signature = sk.sign(message_bytes)

                                            file_info["signature"] = base64.b64encode(signature).decode("utf-8")
                                            print(f"Success sign:   {file_name}")

                                        except Exception as e:
                                            print(f"Fail to sign {file_name}:   {e}")

                                version = data["version"]
                                if self.json_handler.compare_versions(version, max_version):
                                    max_version = version

                                for k, v in data.items():
                                    if k!= "version":
                                        all_result[k] = v

                            else:
                                print(f"\n{target_dir} don't need to updtae\n")

                        with open(self.update_json, "w", encoding="utf-8") as f:
                            json.dump({"version": max_version, **all_result}, f, indent=4, ensure_ascii=False)            

                        with open(self.update_json, "r") as f:
                            update_data = json.load(f)
                        update_meta_payload = make_payload_with_signature(update_data)
                        client.publish(self.update_meta_topic, update_meta_payload, qos=1)
                        print("\nPublish update meta data\n")
                except Exception as e:
                    print(f"Fail to make update metadata:   {e}")
        else:
            print("\n##### Verification Fail #####")

def configure_tls(client, ca_cert, client_cert, client_key):
    client.tls_set(
        ca_certs= ca_cert,
        certfile= client_cert,
        keyfile= client_key,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    client.tls_insecure_set(False)

if __name__ == "__main__":
    handler = DirectorRepoHandler("192.168.86.37", 8883)
    handler.connect_mqtt()
    handler.loop_mqtt()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler.client.loop_stop()
