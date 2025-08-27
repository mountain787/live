from flask import Flask, redirect, request
import re
import time
import hashlib
import requests

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def douyu():
    rid = request.args.get('rid') or request.headers.get('rid')
    if not rid:
        return ('房间号缺失', 400)
    try:
        s = requests.Session()
        res = s.get(f'https://www.douyu.com/{rid}').text
        match = re.search(r'ROOM\.room_id\s*=\s*(\d+);', res)
        if not match:
            return ('房间号错误', 404)
        real_rid = match.group(1)
        url = f'https://playweb.douyu.com/lapi/live/getH5Play/{real_rid}'
        return redirect(url)
    except Exception as e:
        return (str(e), 500)
