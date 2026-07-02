#!/usr/bin/env python3
from __future__ import annotations

import hmac
import hashlib
import os
import secrets
import time
from http import cookies
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent / "public"
USER = os.environ.get("RPEAK_DASH_USER", "dashboard")
PASSWORD = os.environ.get("RPEAK_DASH_PASS", "")
SECRET = os.environ.get("RPEAK_DASH_SECRET", secrets.token_hex(32))
SESSION_SECONDS = 60 * 60 * 12

LOGIN_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>R-PEAK Analytics Dashboard — Login</title>
<style>
:root{--bg:#f6f8fc;--panel:#fff;--muted:#5f6f89;--text:#172033;--accent:#0f766e;--bad:#dc2626;--border:#d7deea}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:radial-gradient(circle at 20% 10%,#dbeafe 0,#f6f8fc 42%,#eef4ff 100%);color:var(--text);padding:24px}.card{width:min(520px,100%);background:linear-gradient(145deg,#ffffff,#f8fbff);border:1px solid var(--border);border-radius:20px;padding:28px;box-shadow:0 24px 80px rgba(31,45,70,.14)}h1{margin:0 0 6px;font-size:28px}.sub{color:var(--muted);font-size:14px;line-height:1.45;margin-bottom:20px}.brand{display:inline-flex;gap:8px;align-items:center;padding:6px 10px;border:1px solid var(--border);border-radius:999px;color:var(--accent);font-weight:800;font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-bottom:16px}.dot{width:8px;height:8px;border-radius:999px;background:var(--accent);box-shadow:0 0 18px var(--accent)}label{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin:14px 0 7px}input{width:100%;padding:13px 14px;border-radius:12px;border:1px solid var(--border);background:#fff;color:var(--text);font-size:16px}button{width:100%;margin-top:18px;padding:13px 14px;border:0;border-radius:12px;background:var(--accent);color:#fff;font-size:16px;font-weight:850;cursor:pointer}.msg{display:MSGDISPLAY;margin:14px 0 0;padding:10px 12px;border-radius:10px;background:#fee2e2;color:var(--bad);font-size:14px}.foot{margin-top:18px;color:var(--muted);font-size:12px;line-height:1.4}</style></head>
<body><main class="card"><div class="brand"><span class="dot"></span>Protected dashboard</div><h1>R-PEAK Analytics Dashboard</h1><div class="sub">Project setup, task bottleneck and thematic operational analytics. Please sign in to continue.</div><form method="post" action="/login"><label>Username</label><input name="username" autocomplete="username" autofocus><label>Password</label><input name="password" type="password" autocomplete="current-password"><button type="submit">Open dashboard</button></form><div class="msg">MESSAGE</div><div class="foot">Access is restricted to authorised dashboard users.</div></main></body></html>"""


def sign(value: str) -> str:
    return hmac.new(SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


def make_token(user: str) -> str:
    expiry = str(int(time.time()) + SESSION_SECONDS)
    value = f"{user}:{expiry}"
    return f"{value}:{sign(value)}"


def parse_token(token: str | None) -> str | None:
    if not token:
        return None
    try:
        user, expiry, sig = token.rsplit(":", 2)
        value = f"{user}:{expiry}"
        if int(expiry) < int(time.time()):
            return None
        if not hmac.compare_digest(sig, sign(value)):
            return None
        return user
    except Exception:
        return None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def identity(self) -> str | None:
        c = cookies.SimpleCookie(self.headers.get("Cookie"))
        m = c.get("rpeak_session")
        return parse_token(m.value) if m else None

    def show_login(self, msg: str = ""):
        body = LOGIN_PAGE.replace("MESSAGE", msg).replace("MSGDISPLAY", "block" if msg else "none").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/logout":
            self.send_response(302)
            self.send_header("Set-Cookie", "rpeak_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return
        if not self.identity():
            return self.show_login()
        return super().do_GET()

    def do_HEAD(self):
        if not self.identity():
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            return
        return super().do_HEAD()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = parse_qs(self.rfile.read(length).decode("utf-8", errors="ignore"))
        if self.path != "/login":
            self.send_error(404)
            return
        username = data.get("username", [""])[0]
        password = data.get("password", [""])[0]
        if hmac.compare_digest(username, USER) and hmac.compare_digest(password, PASSWORD):
            self.send_response(302)
            self.send_header("Set-Cookie", f"rpeak_session={make_token(username)}; Path=/; Max-Age={SESSION_SECONDS}; HttpOnly; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.show_login("Incorrect username or password.")


def main():
    if not PASSWORD:
        raise SystemExit("RPEAK_DASH_PASS must be set in the environment before starting the protected dashboard.")
    port = int(os.environ.get("PORT", "8770"))
    host = os.environ.get("HOST", "127.0.0.1")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"R-PEAK protected dashboard serving on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
