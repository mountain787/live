const fetch = require('node-fetch');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;
const vm = require('vm');
const CryptoJS = require('crypto-js');
const crypto = require('crypto');

// Simple in-memory caches (process-lifetime)
const pageCache = new Map(); // rid -> { scripts, ts }
const paramsCache = new Map(); // rid -> { params, ts }
const PAGE_TTL = 30 * 1000; // 30s
const PARAM_TTL = 15 * 1000; // 15s

module.exports = async (req, res) => {
  const rid = req.query.rid || req.headers.rid || (req.url && (req.url.match(/\/douyu\/([^?\/]+)/) || [])[1]);
  console.log('REQ.URL', req.url, 'QUERY', req.query, 'HEADERS', req.headers && req.headers['user-agent']);
  if (!rid) return res.status(400).send('房间号缺失');

  try {
    // Try cached params
    const now = Date.now();
    const cached = paramsCache.get(rid);
    if (cached && (now - cached.ts) < PARAM_TTL) {
      console.log('USING_CACHED_PARAMS', rid);
      return await doPostAndRedirect(rid, cached.params, res, req.query && req.query.debug=='1');
    }

    // Fetch page scripts (with small cache)
    let scripts;
    const pc = pageCache.get(rid);
    if (pc && (now - pc.ts) < PAGE_TTL) {
      scripts = pc.scripts;
    } else {
      const resp = await fetch(`https://www.douyu.com/${rid}`, { headers: { 'User-Agent': req.headers['user-agent'] || 'Mozilla/5.0' }, timeout: 10000 });
      const text = await resp.text();
      const dom = new JSDOM(text);
      scripts = Array.from(dom.window.document.querySelectorAll('script')).map(s => s.textContent).join('\n');
      pageCache.set(rid, { scripts, ts: now });
    }

    const funcMatch = scripts.match(/(vdwdae325w_64we[\s\S]*function ub98484234[\s\S]*?)function/);
    if (!funcMatch) return res.status(500).send('未能提取签名JS');
    const funcStr = funcMatch[1].replace(/eval.*?;}/, 'strc;}');

    // Create sandbox with shims
    const sandbox = {
      window: {},
      document: {},
      console,
      atob: (s) => Buffer.from(s, 'base64').toString('binary'),
      btoa: (s) => Buffer.from(String(s), 'binary').toString('base64'),
      location: { href: `https://www.douyu.com/${rid}` },
      navigator: { userAgent: req.headers['user-agent'] || '' },
      CryptoJS,
      Date,
      Math
    };
    vm.createContext(sandbox);

    // Prefer using Puppeteer to run the page JS in a real browser context to obtain reliable params
    try {
      const puppeteer = require('puppeteer');
      const browser = await puppeteer.launch({args:['--no-sandbox','--disable-setuid-sandbox']});
      const page = await browser.newPage();
      await page.setUserAgent(req.headers['user-agent'] || 'Mozilla/5.0');
      await page.goto(`https://www.douyu.com/${rid}`, { waitUntil: 'networkidle2', timeout: 15000 });
      // Evaluate ub98484234 in browser context
      const pResult = await page.evaluate(() => {
        try { return typeof ub98484234 === 'function' ? ub98484234() : null; } catch(e) { return {error: String(e)} }
      });
      await browser.close();
      if (!pResult) return res.status(500).send('签名JS返回空');
      if (pResult && pResult.error) return res.status(500).send('Puppeteer eval error: ' + pResult.error);
      console.log('PUPPETEER_RESULT', String(pResult).slice(0,1000));
      // use result below (assign to resultStr to keep rest of code compatible)
      resultStr = String(pResult);
    } catch (e) {
      console.error('PUPPETEER_ERROR', e && e.stack || String(e));
      return res.status(500).send('Puppeteer执行失败: ' + (e && e.message || String(e)));
    }

    const did = '10000000000000000000000000001501';
    const t10 = String(Math.floor(Date.now() / 1000));

    // Prefer generating params by executing the sign function (more reliable)
    let params = null;
    let resultStr = String(result || '');

    const vMatch0 = resultStr.match(/v=(\d+)/);
    const v0 = vMatch0 ? vMatch0[1] : '';
    const rb0 = crypto.createHash('md5').update(rid + did + t10 + v0).digest('hex');

    let func_sign0 = resultStr.replace(/return rt;\}\)\;?/, 'return rt;}');
    func_sign0 = func_sign0.replace('(function (', 'function sign(').replace('CryptoJS.MD5(cb).toString()', '"' + rb0 + '"');

    try {
      vm.runInContext(func_sign0 + '\n;params = typeof sign === "function" ? sign("' + rid + '","' + did + '","' + t10 + '") : null;', sandbox, { timeout: 5000 });
      params = sandbox.params;
      console.log('VM_PARAMS', String(params || '').slice(0,500));
    } catch (e) {
      console.error('VM_ERROR_SIGN_PRIMARY', e && e.stack || String(e));
      // Fallback: if ub98484234 returned a direct params string, patch and use it
      if (resultStr.trim().startsWith('v=')) {
        params = resultStr.replace(/did=undefined/, 'did=' + did).replace(/tt=undefined/, 'tt=' + t10);
        console.log('FALLBACK_USING_RESULT_AS_PARAMS', params.slice(0,200));
      } else {
        return res.status(500).send('生成参数失败: ' + (e && e.message || String(e)));
      }
    }

    if (!params) {
      return res.status(500).send('签名参数为空');
    }

    paramsCache.set(rid, { params, ts: Date.now() });

    return await doPostAndRedirect(rid, params + `&cdn=ws-h5&rate=0`, res);

  } catch (e) {
    console.error('HANDLER_ERROR', e && e.stack || String(e));
    return res.status(500).send(String(e));
  }
};

async function doPostAndRedirect(rid, params, res, debug=false) {
  console.log('POST_PLAYWEB', rid, params.slice(0,200));
  const apiResp = await fetch(`https://playweb.douyu.com/lapi/live/getH5Play/${rid}`, { method: 'POST', body: params, headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, timeout: 10000 });
  const text = await apiResp.text();
  let json = null;
  try { json = JSON.parse(text); } catch(e) { console.error('PLAYWEB_INVALID_JSON', text); return res.status(500).send('Playweb返回非JSON'); }
  console.log('PLAYWEB_RESP', JSON.stringify(json).slice(0,500));
  if (debug) return res.json({playweb: json});
  if (json.error !== 0) return res.status(500).send('获取直播源失败: ' + JSON.stringify(json));
  const data = json.data || {};
  const cdns = data.cdnsWithName || [];
  if (!cdns.length) return res.status(500).send('未获取到CDN线路');
  const cdn = cdns[0].cdn;
  const url = `${data.rtmp_url || ''}/${data.rtmp_live || ''}?cdn=${cdn}`;
  return res.redirect(url);
}
