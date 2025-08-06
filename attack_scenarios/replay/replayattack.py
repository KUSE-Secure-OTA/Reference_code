import paho.mqtt.client as mqtt
import csv, time, os, sys

BROKER_IP = "192.168.86.206"
PORT      = 1883
CSV_FILE  = "mqtt_messages31.csv"
DELAY_SEC = 1

# CSV 체크
if not os.path.isfile(CSV_FILE):
    print(f"ERROR: 파일을 찾을 수 없습니다 → {CSV_FILE}")
    sys.exit(1)
print(f"✔ CSV 로드: {CSV_FILE}, 총 줄수 = {sum(1 for _ in open(CSV_FILE))}")

# 1) 연결 준비
connected = False

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        print("✔ MQTT 브로커 연결 성공")
    else:
        print(f"❌ MQTT 연결 실패, rc={rc}")

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_connect = on_connect

# 2) 네트워크 루프 & 접속
client.loop_start()
client.connect(BROKER_IP, PORT, keepalive=60)

# 3) 연결 완료 대기
start = time.time()
while not connected and time.time() - start < 5:
    time.sleep(0.1)
if not connected:
    print("ERROR: MQTT 연결 타임아웃")
    client.loop_stop()
    client.disconnect()
    sys.exit(1)

# 4) publish (헥스 디코딩 후 JSON payload로 전송)
with open(CSV_FILE, newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    for idx, line in enumerate(reader, 1):
        if len(line) < 2:
            continue
        topic = line[0].strip()
        raw_hex = line[1].strip()

        # 헥스 문자열을 JSON 문자열로 디코딩
        try:
            json_payload = bytes.fromhex(raw_hex).decode('utf-8')
        except Exception as e:
            print(f"❌ 디코딩 실패 at line {idx}: {e}")
            continue

        # 전송 로그
        print(f"[{time.strftime('%H:%M:%S')}] PUBLISH → {topic} | {json_payload}")
        client.publish(topic, json_payload, qos=1)
        time.sleep(DELAY_SEC)

# 5) 마무리
time.sleep(1)           # 전송 대기
client.loop_stop()
client.disconnect()
print(">> 전송 완료")

