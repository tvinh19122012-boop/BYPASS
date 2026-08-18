from flask import Flask, request, jsonify
from flask_cors import CORS
import re, time, json
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)  # Giúp trang HTML của bạn gọi được API này mà không bị chặn

BASE = "https://keycheater.site"
API = f"{BASE}/getkey"
UA = "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"

@app.route('/run-tool', methods=['POST'])
def run_tool():
    # Nhận dữ liệu từ trang HTML gửi lên
    req_data = request.json
    seller = req_data.get('seller', 'zennymod1')
    game = req_data.get('game', 'noroot')

    cfg = {"seller": seller, "game": game}
    
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
    })

    try:
        # ---- STEP 1: GET CSRF ----
        r = s.get(f"{API}/{cfg['seller']}")
        r.raise_for_status()
        html = r.text

        csrf_m = re.search(r'csrf_test_name" value="([^"]+)"', html)
        if not csrf_m: 
            return jsonify({"status": "error", "message": "FAIL: No CSRF"})
        csrf = csrf_m.group(1)

        # Config from debug toolbar
        wait = 100
        wm = re.search(r'wait_time["\:]\s*(\d+)', html)
        if wm: wait = int(wm.group(1))

        # ---- STEP 2: SUBMIT ----
        r2 = s.post(f"{BASE}/getkey-process",
                    data={"csrf_test_name": csrf, "seller": cfg["seller"], "game": cfg["game"]},
                    allow_redirects=False)
        if r2.status_code not in (302, 303):
            return jsonify({"status": "error", "message": f"FAIL: HTTP {r2.status_code}"})

        token = None
        for k, v in r2.headers.items():
            if k.lower() == "set-cookie":
                mt = re.search(r'getkey_token=([^;]+)', v)
                if mt: token = mt.group(1)
        if not token: 
            return jsonify({"status": "error", "message": "FAIL: No token"})

        s.cookies.set("getkey_token", token, domain="keycheater.site", path="/")
        s.cookies.set("getkey_game", cfg["game"], domain="keycheater.site", path="/")

        # ---- STEP 3: WAIT COUNTER ----
        time.sleep(wait)

        # ---- STEP 4: CALLBACK ----
        r3 = s.get(f"{BASE}/getkey-callback/{cfg['seller']}")
        text = r3.text

        if "PHAT HIEN" in text.upper() or "GIAN LAN" in text.upper():
            return jsonify({"status": "error", "message": "BLOCKED! Server detected bypass."})

        # ---- EXTRACT KEY ----
        key = None
        m = re.search(r'class="[^"]*key[-_]?box[^"]*"[^>]*>([^<]+)<', text, re.I)
        if m: key = m.group(1).strip()

        if not key:
            m = re.search(r'>([Vv]ip[A-Za-z0-9_-]+)<', text)
            if m: key = m.group(1)

        if not key:
            m = re.search(r'(Getkey-[A-F0-9]+)', text)
            if m: key = m.group(1)

        if not key:
            m = re.search(r"user_key['\"]?\s*[,)]\s*'([^']+)'", text)
            if m: key = m.group(1)

        if not key:
            for pat in [r'([A-Za-z0-9]{10,})', r'([A-Z][a-z]+[A-Z][a-zA-Z0-9]{6,})']:
                m = re.search(pat, text)
                if m:
                    key = m.group(1)
                    break

        if not key:
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    for k in ("key", "key_code", "user_key", "data", "code", "token"):
                        if k in data:
                            key = data[k]
                            break
            except:
                pass

        if key:
            return jsonify({"status": "success", "key": key})
        else:
            return jsonify({"status": "error", "message": "FAILED: No key found"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
