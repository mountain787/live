import re
import time
import hashlib
import requests
from http.server import BaseHTTPRequestHandler


def handler(request):
    query = request.query
    rid = query.get('rid') or request.headers.get('rid')
    if not rid:
        return (400, '房间号缺失')
    try:
        # Minimal extraction of room id from page
        s = requests.Session()
        res = s.get(f'https://www.douyu.com/{rid}').text
        match = re.search(r'ROOM\.room_id\s*=\s*(\d+);', res)
        if not match:
            return (404, '房间号错误')
        real_rid = match.group(1)
        # Return redirect to playweb endpoint as a placeholder
        url = f'https://playweb.douyu.com/lapi/live/getH5Play/{real_rid}'
        return {'statusCode': 302, 'headers': {'Location': url}}
    except Exception as e:
        return (500, str(e))
