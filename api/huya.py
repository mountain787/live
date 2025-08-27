from flask import Flask, redirect, request, jsonify
import requests
import hashlib
import time
import urllib.parse
import base64
import re

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET','POST'])
@app.route('/<path:path>', methods=['GET','POST'])
def huya(path):
    rid = request.args.get('rid') or request.headers.get('rid')
    if not rid:
        m = re.search(r'/huya/(\d+)', request.path)
        if m:
            rid = m.group(1)
    if not rid:
        return ('房间号缺失', 400)
    try:
        print('PATH:', request.path, 'ARGS:', dict(request.args))
        url = f"https://mp.huya.com/cache.php?m=Live&do=profileRoom&roomid={rid}"
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)"}
        resp = requests.get(url, headers=headers, timeout=5).json()
        print('HUYA_RESP:', resp)
        if request.args.get('debug') == '1':
            return jsonify(resp)
        data = resp.get("data", {})
        if not isinstance(data, dict):
            return ('未找到房间', 404)
        stream = data.get("stream", {})
        streams = stream.get("baseSteamInfoList", [])
        for item in streams:
            if isinstance(item, dict) and item.get("sCdnType") == "AL":
                base_url = item.get("sFlvUrl", "").replace("http://", "https://")
                suffix = item.get("sFlvUrlSuffix", "")
                stream_name = item.get("sStreamName", "")
                anti_code = item.get("sFlvAntiCode", "")
                if base_url and suffix and stream_name and anti_code:
                    params = dict(re.findall(r"([^=&]+)=([^&]*)", anti_code))
                    params["ctype"] = "huya_commserver"
                    params["fs"] = "gct"
                    params["t"] = "264"
                    if "fm" in params and "wsTime" in params:
                        fm = urllib.parse.unquote(params["fm"])
                        u = base64.b64decode(fm).decode("utf-8")
                        p = u.split('_')[0]
                        seqid = str(int(time.time() * 1e7))
                        wsTime = params["wsTime"]
                        h = "_".join([p, "0", stream_name, seqid, wsTime])
                        wsSecret = hashlib.md5(h.encode("utf-8")).hexdigest()
                        params["wsSecret"] = wsSecret
                        params["seqid"] = seqid
                        params["u"] = "0"
                    params.pop("fm", None)
                    new_anti_code = "&".join(f"{k}={v}" for k, v in params.items())
                    return redirect(f"{base_url}/{stream_name}.{suffix}?{new_anti_code}")
        return ('未找到合适的CDN', 404)
    except Exception as e:
        return (str(e), 500)
