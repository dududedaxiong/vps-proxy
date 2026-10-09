#!/usr/bin/env python3
"""轻量短链接 + Pastebin，二合一。纯标准库，零依赖。"""
import http.server, sqlite3, json, os, re, secrets, urllib.parse

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "links.db")
PORT = int(os.environ.get("PORT", "18081"))

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS shorts(code TEXT PRIMARY KEY, url TEXT, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS pastes(pid TEXT PRIMARY KEY, content TEXT, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    return c

def new_code(n=6):
    return secrets.token_urlsafe(n)[:n]

INDEX = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>短链接 · Pastebin</title>
<style>body{font-family:system-ui;max-width:640px;margin:40px auto;padding:0 16px;background:#0f1115;color:#e6e6e6}h2{margin-top:32px}input,textarea{width:100%;padding:10px;margin:8px 0;background:#1a1d24;border:1px solid #333;color:#fff;border-radius:6px;box-sizing:border-box}button{padding:10px 24px;background:#2f81f7;border:0;color:#fff;border-radius:6px;cursor:pointer}#out{margin-top:12px;word-break:break-all;color:#7ee787}</style></head><body>
<h1>🔗 短链接 · 📋 Pastebin</h1>
<h2>短链接</h2><input id="u" placeholder="https://..."><button onclick="go('shorten')">生成</button>
<h2>Pastebin</h2><textarea id="t" rows="6" placeholder="粘贴文本..."></textarea><button onclick="go('paste')">发布</button>
<div id="out"></div>
<script>async function go(k){const out=document.getElementById('out');out.textContent='...';
const body=k=='shorten'?{url:document.getElementById('u').value}:{content:document.getElementById('t').value};
const r=await fetch('/api/'+k,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const j=await r.json();out.innerHTML=j.ok?('✅ <a href="'+j.link+'" style="color:#7ee787">'+j.link+'</a>'):('❌ '+j.err);}</script>
</body></html>"""

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
    def do_GET(self):
        p = urllib.parse.urlparse(self.path).path
        if p == "/" or p == "/index.html":
            return self._html(INDEX)
        m = re.match(r"^/p/([A-Za-z0-9_-]+)$", p)
        if m:
            c = db(); r = c.execute("SELECT content FROM pastes WHERE pid=?", (m.group(1),)).fetchone(); c.close()
            if r: return self._text(r[0])
            return self._text("not found", 404)
        m = re.match(r"^/([A-Za-z0-9_-]{3,12})$", p)
        if m:
            c = db(); r = c.execute("SELECT url FROM shorts WHERE code=?", (m.group(1),)).fetchone(); c.close()
            if r:
                self.send_response(302); self.send_header("Location", r[0]); self.end_headers(); return
            return self._text("not found", 404)
        return self._text("not found", 404)
    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path
        try: body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except: return self._json({"ok": False, "err": "bad json"})
        host = self.headers.get("Host", "")
        base = f"http://{host}"
        if p == "/api/shorten":
            url = (body.get("url") or "").strip()
            if not re.match(r"^https?://", url): return self._json({"ok": False, "err": "URL 需以 http(s):// 开头"})
            code = new_code(); c = db()
            c.execute("INSERT INTO shorts(code,url) VALUES(?,?)", (code, url)); c.commit(); c.close()
            return self._json({"ok": True, "link": f"{base}/{code}"})
        if p == "/api/paste":
            t = body.get("content") or ""
            if not t.strip(): return self._json({"ok": False, "err": "内容为空"})
            if len(t) > 200000: return self._json({"ok": False, "err": "内容超长 (200KB)"})
            pid = new_code(8); c = db()
            c.execute("INSERT INTO pastes(pid,content) VALUES(?,?)", (pid, t)); c.commit(); c.close()
            return self._json({"ok": True, "link": f"{base}/p/{pid}"})
        return self._json({"ok": False, "err": "unknown"})

if __name__ == "__main__":
    db().close()
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
