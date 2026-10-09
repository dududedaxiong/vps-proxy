#!/usr/bin/env python3
"""轻量短链接 + Pastebin，二合一。纯标准库，零依赖。支持过期时间和密码保护。"""
import http.server, sqlite3, json, os, re, secrets, urllib.parse, time, hashlib

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "links.db")
PORT = int(os.environ.get("PORT", "18081"))

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS shorts(code TEXT PRIMARY KEY, url TEXT, expires_at REAL DEFAULT 0, password TEXT DEFAULT '', created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS pastes(pid TEXT PRIMARY KEY, content TEXT, expires_at REAL DEFAULT 0, password TEXT DEFAULT '', created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    for tbl in ("shorts", "pastes"):
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({tbl})").fetchall()]
        if "expires_at" not in cols: c.execute(f"ALTER TABLE {tbl} ADD COLUMN expires_at REAL DEFAULT 0")
        if "password" not in cols: c.execute(f"ALTER TABLE {tbl} ADD COLUMN password TEXT DEFAULT ''")
    return c

def new_code(n=6):
    return secrets.token_urlsafe(n)[:n]

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest() if pw else ""

def is_expired(expires_at):
    return expires_at and expires_at > 0 and time.time() > expires_at

INDEX = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>短链接 · Pastebin</title>
<style>body{font-family:system-ui;max-width:640px;margin:40px auto;padding:0 16px;background:#0f1115;color:#e6e6e6}h2{margin-top:32px}input,textarea,select{width:100%;padding:10px;margin:8px 0;background:#1a1d24;border:1px solid #333;color:#fff;border-radius:6px;box-sizing:border-box}button{padding:10px 24px;background:#2f81f7;border:0;color:#fff;border-radius:6px;cursor:pointer}#out{margin-top:12px;word-break:break-all;color:#7ee787}.row{display:flex;gap:8px}.row>*{flex:1}</style></head><body>
<h1>🔗 短链接 · 📋 Pastebin</h1>
<h2>短链接</h2><input id="u" placeholder="https://...">
<div class="row"><select id="ue"><option value="0">永不过期</option><option value="1">1小时</option><option value="24">1天</option><option value="168">7天</option><option value="720">30天</option></select><input id="up" type="password" placeholder="访问密码(可选)"></div>
<button onclick="go('shorten')">生成</button>
<h2>Pastebin</h2><textarea id="t" rows="6" placeholder="粘贴文本..."></textarea>
<div class="row"><select id="pe"><option value="0">永不过期</option><option value="1">1小时</option><option value="24">1天</option><option value="168">7天</option><option value="720">30天</option></select><input id="pp" type="password" placeholder="访问密码(可选)"></div>
<button onclick="go('paste')">发布</button>
<div id="out"></div>
<script>async function go(k){const out=document.getElementById('out');out.textContent='...';
const p=k=='shorten'?'u':'t', e=document.getElementById(k=='shorten'?'ue':'pe').value, pw=document.getElementById(k=='shorten'?'up':'pp').value;
const body=k=='shorten'?{url:document.getElementById('u').value}:{content:document.getElementById('t').value};
body.expires_in_hours=parseInt(e); if(pw) body.password=pw;
const r=await fetch('/api/'+k,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const j=await r.json();out.innerHTML=j.ok?('✅ <a href="'+j.link+'" style="color:#7ee787">'+j.link+'</a>'):('❌ '+j.err);}</script>
</body></html>"""

PWFORM = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>需要密码</title>
<style>body{font-family:system-ui;max-width:400px;margin:80px auto;padding:0 16px;background:#0f1115;color:#e6e6e6;text-align:center}input{width:100%;padding:10px;margin:12px 0;background:#1a1d24;border:1px solid #333;color:#fff;border-radius:6px;box-sizing:border-box}button{padding:10px 24px;background:#2f81f7;border:0;color:#fff;border-radius:6px;cursor:pointer}</style></head><body>
<h2>🔒 需要密码</h2><form method="get"><input type="password" name="pw" placeholder="输入访问密码" autofocus><br><button type="submit">进入</button></form></body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, o, code=200):
        b = json.dumps(o).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def _html(self, s, code=200):
        b = s.encode()
        self.send_response(code); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def _text(self, s, code=200):
        b = s.encode()
        self.send_response(code); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)
    def _check(self, row):
        content, expires_at, pw_hash = row[0], row[1], row[2]
        if is_expired(expires_at):
            return False, "已过期"
        if pw_hash:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            pw = qs.get("pw", [""])[0]
            if hash_pw(pw) != pw_hash:
                return None, None
        return True, content
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        p = url.path
        if p == "/" or p == "/index.html":
            return self._html(INDEX)
        m = re.match(r"^/p/([A-Za-z0-9_-]+)$", p)
        if m:
            c = db(); r = c.execute("SELECT content, expires_at, password FROM pastes WHERE pid=?", (m.group(1),)).fetchone(); c.close()
            if not r: return self._text("not found", 404)
            ok, res = self._check(r)
            if ok is None: return self._html(PWFORM)
            if not ok: return self._text(res, 410)
            return self._text(res)
        m = re.match(r"^/([A-Za-z0-9_-]{3,12})$", p)
        if m:
            c = db(); r = c.execute("SELECT url, expires_at, password FROM shorts WHERE code=?", (m.group(1),)).fetchone(); c.close()
            if not r: return self._text("not found", 404)
            ok, res = self._check(r)
            if ok is None: return self._html(PWFORM)
            if not ok: return self._text(res, 410)
            self.send_response(302); self.send_header("Location", res); self.end_headers(); return
        return self._text("not found", 404)
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        try: body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except: return self._json({"ok": False, "err": "bad json"})
        host = self.headers.get("Host", "")
        base = f"https://{host}" if self.headers.get("X-Forwarded-Proto") == "https" else f"http://{host}"
        try: exp_h = float(body.get("expires_in_hours", 0) or 0)
        except: exp_h = 0
        expires_at = time.time() + exp_h * 3600 if exp_h > 0 else 0
        pw_hash = hash_pw((body.get("password") or "").strip())
        if p == "/api/shorten":
            url = (body.get("url") or "").strip()
            if not re.match(r"^https?://", url): return self._json({"ok": False, "err": "URL 需以 http(s):// 开头"})
            code = new_code(); c = db()
            c.execute("INSERT INTO shorts(code,url,expires_at,password) VALUES(?,?,?,?)", (code, url, expires_at, pw_hash)); c.commit(); c.close()
            return self._json({"ok": True, "link": f"{base}/{code}"})
        if p == "/api/paste":
            t = body.get("content") or ""
            if not t.strip(): return self._json({"ok": False, "err": "内容为空"})
            if len(t) > 200000: return self._json({"ok": False, "err": "内容超长 (200KB)"})
            pid = new_code(8); c = db()
            c.execute("INSERT INTO pastes(pid,content,expires_at,password) VALUES(?,?,?,?)", (pid, t, expires_at, pw_hash)); c.commit(); c.close()
            return self._json({"ok": True, "link": f"{base}/p/{pid}"})
        return self._json({"ok": False, "err": "unknown"})

if __name__ == "__main__":
    db().close()
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
