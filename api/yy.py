from flask import Flask, redirect, request
import requests
import re
import json

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def yy():
    rid = request.args.get('rid') or request.headers.get('rid')
    if not rid or not rid.isdigit():
        return ('房间号非法', 400)
    try:
        headers = {
            'referer': f'https://wap.yy.com/mobileweb/{rid}',
            'user-agent': 'Mozilla/5.0'
        }
        room_url = f'https://interface.yy.com/hls/new/get/{rid}/{rid}/1200?source=wapyy&callback='
        res = requests.get(room_url, headers=headers, timeout=2)
        if res.status_code != 200:
            return ('直播间不存在', 404)
        data = json.loads(res.text[1:-1])
        if data.get('hls', 0):
            xa = data['audio']
            xv = data['video']
            xv = re.sub(r'_0_\d+_0', '_0_0_0', xv)
            url = f'https://interface.yy.com/hls/get/stream/15013/{xv}/15013/{xa}?source=h5player&type=m3u8'
            real = requests.get(url, timeout=2).json().get('hls')
            return redirect(real)
        return ('未开播', 404)
    except Exception as e:
        return (str(e), 500)
