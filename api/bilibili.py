from flask import Flask, redirect, request
import requests

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def bilibili():
    rid = request.args.get('rid') or request.headers.get('rid')
    if not rid or not rid.isdigit():
        return ('房间号非法', 400)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        status_resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/room_init?id={rid}", headers=headers, timeout=2)
        status_json = status_resp.json()
        if status_json.get('code') != 0 or status_json.get('data', {}).get('live_status', 0) != 1:
            return ('未开播', 404)
        url = f"https://api.live.bilibili.com/xlive/play-gateway/master/url?cid={rid}&mid=17335468&pt=h5"
        return redirect(url)
    except Exception as e:
        return (str(e), 500)
