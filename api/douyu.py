from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlparse, parse_qs
from DouYu import DouYu

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        rid = query.get("rid", [None])[0]

        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()

        if not rid:
            self.wfile.write(json.dumps({"error": "缺少 rid 参数"}).encode("utf-8"))
            return

        try:
            douyu = DouYu(rid)
            url = douyu.get_real_url()
            self.wfile.write(json.dumps(url, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
