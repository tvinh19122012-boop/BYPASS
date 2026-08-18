from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import time
from datetime import datetime
import requests

app = Flask(__name__)
CORS(app)

BASE = "https://keycheater.site"
API = f"{BASE}/getkey"
UA = "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"

@app.route('/run-tool', methods=['POST'])
def run_tool():
    try:
        data = request.json or {}
        seller = data.get('seller', 'zennymod1')
        game = data.get('game', 'noroot')

        s = requests.Session()
        s.headers.update({
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        })

        # ---- STEP 1: GET CSRF ----
        r = s.get(f"{API}/{seller}", timeout=15)
        r.raise_for_status()
        html = r.text

        csrf_m = re.search(r'csrf_test_name" value="([^"]+)"', html)
        if not csrf_m:
            return jsonify({"status": "error", "message": "Không tìm thấy mã CSRF token."}), 400
        csrf = csrf_m.group(1)

        wait = 10
        wm = re.search(r'wait_time["\:]\s*(\d+)', html)
        if wm:
            wait = int(wm.group(1))

        # ---- STEP 2: SUBMIT ----
        r2 = s.post(f"{BASE}/getkey-process",
                    data={"csrf_test_name": csrf, "seller": seller, "game": game},
                    allow_redirects=False, timeout=15)
        
        if r2.status_code not in (302, 303):
            return jsonify({"status": "error", "message": f"Gửi request thất bại (HTTP {r2.status_code})"}), 400

        token = None
        for k, v in r2.headers.items():
            if k.lower() == "set-cookie":
                mt = re.search(r'getkey_token=([^;]+)', v)
                if mt:
                    token = mt.group(1)
        
        if not token:
            return jsonify({"status": "error", "message": "Không lấy được getkey_token."}), 400

        s.cookies.set("getkey_token", token, domain="keycheater.site", path="/")
        s.cookies.set("getkey_game", game, domain="keycheater.site", path="/")

        # ---- STEP 3: WAIT COUNTER ----
        # Tạm dừng thời gian theo yêu cầu của server target
        time.sleep(wait)

        # ---- STEP 4: CALLBACK ----
        r3 = s.get(f"{BASE}/getkey-callback/{seller}", timeout=15)
        text = r3.text

        if "PHAT HIEN" in text.upper() or "GIAN LAN" in text.upper():
            return jsonify({"status": "error", "message": "Server phát hiện thời gian bất thường hoặc lỗi bypass."}), 400

        # ---- EXTRACT KEY ----
        key = None
        
        # Thử tìm kiếm các dạng key khác nhau
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

        if key:
            return jsonify({
                "status": "success",
                "key": key,
                "message": f"Kích hoạt thành công cho seller: {seller}"
            })
        else:
            return jsonify({"status": "error", "message": "Không trích xuất được Key từ phản hồi server."}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
