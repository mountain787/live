from http.server import BaseHTTPRequestHandler
import re, time, hashlib, requests, execjs

# 确认 execjs 能找到 Node.js
try:
    execjs.get("Node")
except execjs.RuntimeUnavailableError:
    raise RuntimeError("没有检测到 Node.js，请确认 Vercel 环境支持 Node")

# ---------------- DouYu 类 ----------------
class DouYu:
    def __init__(self, rid):
        self.did = '10000000000000000000000000001501'
        self.t10 = str(int(time.time()))
        self. = requests.Session()

        res = self..get(f'https://www.douyu.com/{rid}').text
        match = re.search(r'ROOM\.room_id\s*=\s*(\d+);', res)
        if match:
            self.rid = match.group(1)
            self.res = res
        else:
            raise Exception('房间号错误')

    @staticmethod
    def md5(data):
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def get_pc_js(self, cdn='ws-h5', rate=0):
        func_str = re.search(
            r'(vdwdae325w_64we[\s\S]*function ub98484234[\s\S]*?)function',
            self.res
        ).group(1)
        func_ub9 = re.sub(r'eval.*?;}', 'strc;}', func_str)
        js = execjs.compile(func_ub9)
        res = js.call('ub98484234')

        v = re.search(r'v=(\d+)', res).group(1)
        rb = self.md5(self.rid + self.did + self.t10 + v)

        func_sign = re.sub(r'return rt;}\);?', 'return rt;}', res)
        func_sign = func_sign.replace('(function (', 'function sign(')
        func_sign = func_sign.replace('CryptoJS.MD5(cb).toString()', f'"{rb}"')

        js = execjs.compile(func_sign)
        params = js.call('sign', self.rid, self.did, self.t10) + f'&cdn={cdn}&rate={rate}'

        url = f'https://playweb.douyu.com/lapi/live/getH5Play/{self.rid}'
        return self..post(url, params=params).json()

    def get_real_url(self):
        res = self.get_pc_js()
        if res.get('error') != 0:
            code = res.get('error')
            raise Exception(
                '房间不存在' if code == 102 else
                '房间未开播' if code == 104 else
                f'获取直播源失败，错误码：{code}'
            )

        data = res.get('data', {})
        cdns = data.get('cdnsWithName', [])
        if not cdns:
            raise Exception("未获取到CDN线路")

        cdn = cdns[0].get('cdn')
        if not cdn:
            raise Exception("CDN数据异常")

        return f"{data.get('rtmp_url','')}/{data.get('rtmp_live','')}?cdn={cdn}"


# ---------------- Vercel handler ----------------
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        rid = self.path.strip("/").split("/")[-1]

        if not rid or not rid.isdigit():
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"缺少或非法 rid 参数")
            return

        try:
            douyu = DouYu(rid)
            real_url = douyu.get_real_url()

            # 302 重定向
            self.send_response(302)
            self.send_header("Location", real_url)
            self.end_headers()
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))
v
