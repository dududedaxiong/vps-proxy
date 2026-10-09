#!/usr/bin/env python3
import socket, ssl, threading, base64, os, struct
H = "nezha-agent.mick.cc.cd"
I = os.environ.get("TID", "")
J = os.environ.get("TSEC", "")

def E(s, d, o=0x2):
    f = bytearray([0x80 | o])
    n = len(d)
    m = os.urandom(4)
    if n < 126:
        f.append(0x80 | n)
    elif n < 65536:
        f.append(0x80 | 126)
        f.extend(struct.pack("!H", n))
    else:
        f.append(0x80 | 127)
        f.extend(struct.pack("!Q", n))
    f.extend(m)
    f.extend(bytes(b ^ m[i % 4] for i, b in enumerate(d)))
    s.sendall(bytes(f))

def R(s, n):
    b = b""
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c:
            return None
        b += c
    return b

def G(s):
    h = R(s, 2)
    if not h:
        return None, None
    o = h[0] & 0x0F
    v = (h[1] & 0x80) != 0
    l = h[1] & 0x7F
    if l == 126:
        r = R(s, 2)
        l = struct.unpack("!H", r)[0]
    elif l == 127:
        r = R(s, 8)
        l = struct.unpack("!Q", r)[0]
    k = R(s, 4) if v else None
    p = R(s, l) if l else b""
    if v:
        p = bytes(x ^ k[i % 4] for i, x in enumerate(p))
    return o, p

def U():
    s = socket.create_connection((H, 443), 15)
    w = ssl.create_default_context().wrap_socket(s, server_hostname=H)
    k = base64.b64encode(os.urandom(16)).decode()
    C = chr(13) + chr(10)
    q = "GET / HTTP/1.1" + C
    q += "Host: " + H + C
    q += "CF-Access-Client-Id: " + I + C
    q += "CF-Access-Client-Secret: " + J + C
    q += "Upgrade: websocket" + C
    q += "Connection: Upgrade" + C
    q += "Sec-WebSocket-Key: " + k + C
    q += "Sec-WebSocket-Version: 13" + C + C
    w.sendall(q.encode())
    r = b""
    while b"\r\n\r\n" not in r:
        r += w.recv(4000)
    if b"101" not in r.split(b"\r\n")[0]:
        raise Exception("up fail")
    return w

def F(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            E(b, d)
    except:
        pass
    try:
        E(b, b"", 0x8)
    except:
        pass

def D(a, b):
    try:
        while True:
            o, d = G(a)
            if o is None or o == 0x8:
                break
            if o == 0x9:
                E(a, d, 0xA)
                continue
            if o == 0xA:
                continue
            if d:
                b.sendall(d)
    except:
        pass

def V(c):
    try:
        w = U()
    except Exception as e:
        print("up fail:", e, flush=True)
        c.close()
        return
    x = threading.Thread(target=F, args=(c, w), daemon=True)
    y = threading.Thread(target=D, args=(w, c), daemon=True)
    x.start()
    y.start()
    x.join()
    y.join()
    c.close()
    w.close()

srv = socket.socket()
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 18008))
srv.listen(10)
print("Listening 127.0.0.1:18008", flush=True)
while True:
    c, _ = srv.accept()
    threading.Thread(target=V, args=(c,), daemon=True).start()
