from flask import Flask, redirect, request, jsonify
import requests

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET','POST'])
@app.route('/<path:path>', methods=['GET','POST'])
def bilibili(path):
    rid = request.args.get('rid') or request.headers.get('rid')
    if not rid:
        import re
        m = re.search(r'/bilibili/(\d+)', request.path)
        if m:
            rid = m.group(1)
    if not rid:
        return ('房间号非法', 400)
    try:
        print('PATH:', request.path, 'ARGS:', dict(request.args))
        headers = {"User-Agent": "Mozilla/5.0"}
        status_resp = requests.get(f"https://api.live.bilibili.com/room/v1/Room/room_init?id={rid}", headers=headers, timeout=5)
        try:
            status_json = status_resp.json()
        except Exception as e:
            print('BILIBILI_API_INVALID_JSON', status_resp.text)
            return (str(e), 500)
        print('BILIBILI_RESP:', status_json)
        if request.args.get('debug') == '1':
            return jsonify(status_json)
        data = status_json.get('data', {})
        if status_json.get('code') != 0:
            return ('Bilibili 接口返回错误', 500)
        if data.get('room_shield') == 1:
            if request.args.get('debug') == '1':
                return jsonify({'error': 'room_shield', 'status': status_json})
            return ('房间被屏蔽', 403)
        if data.get('live_status', 0) != 1:
            return ('未开播或直播间不存在', 404)
        url = f"https://api.live.bilibili.com/xlive/play-gateway/master/url?cid={rid}&mid=17335468&pt=h5"
        return redirect(url)
    except Exception as e:
        return (str(e), 500)
