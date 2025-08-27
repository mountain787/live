const fetch = require('node-fetch');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

module.exports = async (req, res) => {
  const rid = req.query.rid || req.headers.rid || (req.url && (req.url.match(/\/douyu\/([^?\/]+)/) || [])[1]);
  console.log('REQ.URL', req.url, 'QUERY', req.query, 'HEADERS', req.headers);
  if (!rid) return res.status(400).send('房间号缺失');
  try {
    const resp = await fetch(`https://www.douyu.com/${rid}`, { headers: { 'User-Agent': 'Mozilla/5.0' } });
    const text = await resp.text();

    const dom = new JSDOM(text);
    const scripts = Array.from(dom.window.document.querySelectorAll('script')).map(s => s.textContent).join('\n');
    const funcMatch = scripts.match(/(vdwdae325w_64we[\s\S]*function ub98484234[\s\S]*?)function/);
    if (!funcMatch) return res.status(500).send('未能提取签名JS');
    const funcStr = funcMatch[1].replace(/eval.*?;}/, 'strc;}');

    const vm = require('vm');
    const crypto = require('crypto');
    const CryptoJS = require('crypto-js');
    const sandbox = {
      window: {},
      document: {},
      console,
      atob: (s) => Buffer.from(s, 'base64').toString('binary'),
      btoa: (s) => Buffer.from(String(s), 'binary').toString('base64'),
      location: { href: `https://www.douyu.com/${rid}` },
      navigator: { userAgent: req.headers['user-agent'] || '' },
      CryptoJS
    };
    vm.createContext(sandbox);
    try {
      vm.runInContext(funcStr + '\n;result = typeof ub98484234 === "function" ? ub98484234() : null;', sandbox, { timeout: 2000 });
    } catch (e) {
      console.error('VM_ERROR_FUNCSTR', e && e.stack || String(e));
      return res.status(500).send('执行签名JS失败: ' + (e && e.message || String(e)));
    }
    const result = sandbox.result;
    if (!result) {
      console.error('VM_NO_RESULT', { funcStrSnippet: funcStr.slice(0,1000) });
      return res.status(500).send('签名JS返回空');
    }

    const vMatch = result.match(/v=(\d+)/);
    const v = vMatch ? vMatch[1] : null;
    const did = '10000000000000000000000000001501';
    const t10 = String(Math.floor(Date.now() / 1000));
    const crypto = require('crypto');
    const rb = crypto.createHash('md5').update(rid + did + t10 + v).digest('hex');

    let func_sign = result.replace(/return rt;}\)\;?/, 'return rt;}');
    func_sign = func_sign.replace('(function (', 'function sign(').replace('CryptoJS.MD5(cb).toString()', '"' + rb + '"');

    try {
      vm.runInContext(func_sign + '\n;params = typeof sign === "function" ? sign("' + rid + '","' + did + '","' + t10 + '") : null;', sandbox, { timeout: 2000 });
    } catch (e) {
      return res.status(500).send('生成参数失败');
    }
    const params = sandbox.params + `&cdn=ws-h5&rate=0`;

    const apiResp = await fetch(`https://playweb.douyu.com/lapi/live/getH5Play/${rid}`, { method: 'POST', body: params, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
    const json = await apiResp.json();
    if (json.error !== 0) return res.status(500).send('获取直播源失败');
    const data = json.data || {};
    const cdns = data.cdnsWithName || [];
    if (!cdns.length) return res.status(500).send('未获取到CDN线路');
    const cdn = cdns[0].cdn;
    const url = `${data.rtmp_url || ''}/${data.rtmp_live || ''}?cdn=${cdn}`;
    return res.redirect(url);
  } catch (e) {
    return res.status(500).send(String(e));
  }
};
