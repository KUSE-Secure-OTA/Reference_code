# server_with_upload.py
from flask import Flask, request, send_from_directory
import threading
import os
import time
import requests

# ===== Flask 서버 설정 =====
app = Flask(__name__)
UPLOAD_FOLDER = "./uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    print(f"✅ File saved at: {filepath} ({os.path.getsize(filepath)} bytes)")
    return {"url": f"https://10.888.22.12:443/download/{file.filename}"}, 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ===== Flask 서버를 백그라운드 스레드로 실행 =====
def run_server():
    context = ('./certs/https_server.crt', './certs/https_server.key')
    app.run(host='0.0.0.0', port=443, ssl_context=context)

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# ===== 업로드 클라이언트 코드 =====
time.sleep(1)  # 서버가 뜰 시간을 약간 줌 (중요!)

file_path = "../data/update.tar.xz"
upload_url = "http://localhost:443/upload"

with open(file_path, 'rb') as f:
    files = {'file': ('update.tar.xz', f)}
    res = requests.post(upload_url, files=files)

download_url = res.json()['url']
print("📡 Upload complete, download URL:", download_url)

# ===== 서버 계속 살려두기 (CTRL+C로 종료) =====
while True:
    time.sleep(1)
