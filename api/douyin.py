from flask import Flask, redirect, request
import requests
import re

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def douyin():
    room_id = request.args.get('room_id') or request.headers.get('room_id')
    if not room_id or not room_id.isdigit():
        return ('room_id 非法', 400)
    try:
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        url = f'https://webcast.amemv.com/webcast/room/reflow/info/?room_id={room_id}'
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json().get('data', {})
        stream_data = data.get('stream_url') or {}
        pull = stream_data.get('rtmp_pull_url') or stream_data.get('hls_pull_url')
        if not pull:
            return ('未找到拉流地址', 404)
        return redirect(pull)
    except Exception as e:
        return (str(e), 500)
