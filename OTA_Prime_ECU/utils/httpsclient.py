# file_receiver.py
import requests
import os

# 서버에서 전달받은 다운로드 URL
download_url = "http://192.168.86.182:5000/download/update.tar.xz"
save_path = "./downloaded_update.tar.gz"

try:
    response = requests.get(download_url, stream=True)
    response.raise_for_status() 

    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"✅ File downloaded successfully and saved to: {save_path}")
    print(f"📦 Size: {os.path.getsize(save_path)} bytes")

except Exception as e:
    print(f"❌ Download failed: {e}")





