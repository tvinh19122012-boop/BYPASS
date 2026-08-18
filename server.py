from flask import Flask, request, jsonify
from flask_cors import CORS
import re, json, time
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
            return jsonify({"status": "error", "message": "FAIL: No CSRF"}), 400
        csrf = csrf_m.group(1)

        wait = 100
        wm = re.search(r'wait_time["\:]\s*(\d+)', html)
        if wm: 
            wait = int(wm.group(1))

        # ---- STEP 2: SUBMIT ----
        r2 = s.post(f"{BASE}/getkey-process",
                    data={"csrf_test_name": csrf, "seller": seller, "game": game},
                    allow_redirects=False, timeout=15)
        
        if r2.status_code not in (302, 303):
            return jsonify({"status": "error", "message": f"FAIL: HTTP {r2.status_code}"}), 400

        token = None
        for k, v in r2.headers.items():
            if k.lower() == "set-cookie":
                mt = re.search(r'getkey_token=([^;]+)', v)
                if mt: 
                    token = mt.group(1)
        
        if not token:
            return jsonify({"status": "error", "message": "FAIL: No token"}), 400

        s.cookies.set("getkey_token", token, domain="keycheater.site", path="/")
        s.cookies.set("getkey_game", game, domain="keycheater.site", path="/")

        # ---- STEP 3: WAIT COUNTER ----
        time.sleep(wait)

        # ---- STEP 4: CALLBACK ----
        r3 = s.get(f"{BASE}/getkey-callback/{seller}", timeout=15)
        text = r3.text

        if "PHAT HIEN" in text.upper() or "GIAN LAN" in text.upper():
            return jsonify({"status": "error", "message": "BLOCKED! Server detected bypass."}), 400

        # ---- EXTRACT KEY (Full 6 methods từ crack.py) ----
        key = None
        methods = []

        m = re.search(r'class="[^"]*key[-_]?box[^"]*"[^>]*>([^<]+)<', text, re.I)
        if m:
            key = m.group(1).strip()
            methods.append("key-box")

        if not key:
            m = re.search(r'>([Vv]ip[A-Za-z0-9_-]+)<', text)
            if m:
                key = m.group(1)
                methods.append("Vip pattern")

        if not key:
            m = re.search(r'(Getkey-[A-F0-9]+)', text)
            if m:
                key = m.group(1)
                methods.append("Getkey pattern")

        if not key:
            m = re.search(r"user_key['\"]?\s*[,)]\s*'([^']+)'", text)
            if m:
                key = m.group(1)
                methods.append("SQL INSERT query")

        if not key:
            for pat in [r'([A-Za-z0-9]{10,})', r'([A-Z][a-z]+[A-Z][a-zA-Z0-9]{6,})']:
                m = re.search(pat, text)
                if m:
                    key = m.group(1)
                    methods.append("generic pattern")
                    break

        if not key:
            try:
                jdata = json.loads(text)
                if isinstance(jdata, dict):
                    for k in ("key", "key_code", "user_key", "data", "code", "token"):
                        if k in jdata:
                            key = jdata[k]
                            methods.append("JSON")
                            break
            except:
                pass

        if key:
            return jsonify({
                "status": "success",
                "key": key,
                "message": f"Thành công! Lấy qua: {methods[0] if methods else 'unknown'}"
            })
        else:
            return jsonify({"status": "error", "message": "FAIL: No key found"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
