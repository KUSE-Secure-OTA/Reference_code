# director_repo.py

import os
import time
import json
import hashlib
import paho.mqtt.client as mqtt
from utils.json_handler import JsonHandler
from utils.signature.pub_signature import make_payload_with_signature
from utils.signature.sub_signature import verify_signature

class DirectorRepoHandler:
    def __init__(self, broker, port):
        self.MQTT_BROKER = broker
        self.MQTT_PORT = port

        self.notify_director_topic = "notify/director"
        self.received_topic = "file/current_json"
        self.update_publish_topic = "director/updateList"
        self.notify_client_topic = "file/added"

        self.output_json = "../data/output.json"
        self.received_json = "../data/received.json"
        self.update_json = "../data/update.json"

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.json_handler = JsonHandler()

    def connect_mqtt(self):
        self.client.connect(self.MQTT_BROKER, self.MQTT_PORT, 60)

    def loop_mqtt(self):
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print(f"[DirectorRepo] Connected: {rc}")
        client.subscribe(self.notify_director_topic)
        client.subscribe(self.received_topic)

    def on_message(self, client, userdata, msg):
        if not verify_signature(msg.payload):
            print("[DirectorRepo] ❌ Signature verification failed.")
            return

        payload = json.loads(msg.payload.decode())

        if msg.topic == self.notify_director_topic:
            print("[DirectorRepo] Received notify from image repo.")
            with open(self.output_json, "w", encoding="utf-8") as f:
                json.dump(payload["file"], f, indent=4)
            print("[DirectorRepo] output.json saved.")
            # notify_msg = {"event": "update_available"}
            message = {"event": "directory_added", "directory": payload["directory"]}

            notify_payload = make_payload_with_signature(message)
            client.publish(self.notify_client_topic, notify_payload)

        elif msg.topic == self.received_topic:
            print("[DirectorRepo] Received received.json from client.")
            with open(self.received_json, "w") as f:
                json.dump(payload, f, indent=4)

            print("[DirectorRepo] received.json saved.")
            try:
                keys = list(payload.keys())
                if len(keys) >= 1:
                    target_dir = keys[1]
                    self.json_handler.compare_and_update_json(
                        self.output_json,
                        self.received_json,
                        target_dir,
                        self.update_json
                    )
                    with open(self.update_json, "r") as f:
                        update_data = json.load(f)
                    update_payload = make_payload_with_signature(update_data)
                    client.publish(self.update_publish_topic, update_payload)
                    print("[DirectorRepo] update.json sent to image repo.")

            except Exception as e:
                print(f"[DirectorRepo] Failed to create/send update.json: {e}")

if __name__ == "__main__":
    handler = DirectorRepoHandler("192.168.86.182", 1883)
    handler.connect_mqtt()
    handler.loop_mqtt()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler.client.loop_stop()
