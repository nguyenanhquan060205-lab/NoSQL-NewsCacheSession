"""
Smoke test sau deploy: kiểm tra nhanh các luồng chính của API trên một môi trường đang chạy
(local, container, Render, hoặc qua Vercel).

Các bước (dừng ở bước đầu tiên hỏng, trả mã thoát 1):
  1. GET /health                    → 200, mongodb + redis đều Healthy
  2. GET /api/posts?pageSize=1      → totalItems ≥ --min-posts
  3. Đăng nhập admin                → có cookie SessionId, GET /api/auth/me 200
  4. Tạo bài → GET hai lần          → X-Cache MISS rồi HIT
  5. Sửa bài → GET lại              → MISS và có tiêu đề mới (cache cũ đã bị xóa)
  6. POST /api/posts/{id}/view      → lượt xem tăng đúng 1
  7. Xóa bài                        → 204, GET sau đó 404 (dọn luôn dữ liệu test)
  8. Đăng xuất                      → GET /api/auth/me 401
  9. (--spa-url) GET <url>/posts/{id} → 200 HTML (fallback SPA của Vercel)

Chỉ dùng thư viện chuẩn Python nên chạy được trên mọi máy của nhóm (cả Windows).
Script tự tạo và tự xóa bài viết test; không đụng bài có sẵn, không ghi Redis trực tiếp.

Cách chạy:
    set SMOKE_ADMIN_PASS=...        (Windows)   |   export SMOKE_ADMIN_PASS=...   (macOS/Linux)
    python scripts/Smoke/smoke_test.py --base-url http://localhost:5134 --admin-user admin
    python scripts/Smoke/smoke_test.py --base-url https://<app>.vercel.app --admin-user admin --spa-url https://<app>.vercel.app
"""

import argparse
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 90  # Render free ngủ sau 15 phút, lần gọi đầu có thể mất khoảng 1 phút để thức dậy


class SmokeFailure(Exception):
    pass


class Client:
    """HTTP client giữ cookie như trình duyệt (cookie SessionId là HttpOnly)."""

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, method, path, body=None):
        url = path if path.startswith("http") else self.base_url + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json", "Accept": "*/*"})
        try:
            with self.opener.open(req, timeout=TIMEOUT_SECONDS) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as err:
            return err.code, dict(err.headers), err.read()

    def json(self, method, path, body=None):
        status, headers, raw = self.request(method, path, body)
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = None
        return status, headers, payload

    def has_cookie(self, name):
        return any(c.name == name for c in self.cookies)


def header(headers, name):
    """Lấy header không phân biệt hoa thường."""
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def expect(condition, message):
    if not condition:
        raise SmokeFailure(message)


def check_not_cdn_cached(headers):
    # Vercel tôn trọng header cache của upstream: nếu /api bị CDN giữ thì X-Cache và dữ liệu sai.
    vercel_cache = header(headers, "x-vercel-cache")
    expect(vercel_cache in (None, "MISS", "BYPASS", "PRERENDER"),
           f"response /api bị CDN cache (x-vercel-cache: {vercel_cache})")


def run(args):
    client = Client(args.base_url)
    steps = []

    def step(name, fn):
        started = time.perf_counter()
        note = fn()
        elapsed = (time.perf_counter() - started) * 1000
        steps.append(name)
        print(f"PASS  {name}  ({elapsed:.0f} ms){'  — ' + note if note else ''}")

    def health():
        status, _, body = client.json("GET", "/health")
        expect(status == 200, f"/health trả {status}")
        entries = (body or {}).get("entries", {})
        bad = {k: v.get("status") for k, v in entries.items() if v.get("status") != "Healthy"}
        expect(body.get("status") == "Healthy" and not bad, f"/health chưa Healthy: {bad or body.get('status')}")
        return ", ".join(f"{k}={v.get('status')}" for k, v in entries.items())

    def list_posts():
        status, _, body = client.json("GET", "/api/posts?pageSize=1")
        expect(status == 200, f"GET /api/posts trả {status}")
        total = body.get("totalItems", 0)
        expect(total >= args.min_posts, f"totalItems = {total} < {args.min_posts}")
        return f"totalItems = {total}"

    def login():
        status, _, body = client.json("POST", "/api/auth/login",
                                      {"username": args.admin_user, "password": args.admin_pass})
        expect(status == 200, f"đăng nhập trả {status}: {(body or {}).get('message')}")
        expect(client.has_cookie("SessionId"), "không nhận được cookie SessionId")
        status, _, me = client.json("GET", "/api/auth/me")
        expect(status == 200, f"/api/auth/me trả {status}")
        expect(me.get("role") == "admin", f"tài khoản {args.admin_user} không phải admin (role={me.get('role')})")
        return f"role = {me.get('role')}, TTL còn {me.get('expiresInSeconds')} s"

    state = {}

    def create_then_miss_hit():
        title = f"Smoke test {time.strftime('%Y%m%d-%H%M%S')}"
        status, _, body = client.json("POST", "/api/posts", {"title": title, "content": "Bài viết do smoke test tạo, sẽ tự xóa."})
        expect(status == 201, f"tạo bài trả {status}: {(body or {}).get('message')}")
        state["id"] = body["id"]
        seen = []
        for _ in range(2):
            status, headers, _ = client.json("GET", f"/api/posts/{state['id']}")
            expect(status == 200, f"GET bài vừa tạo trả {status}")
            check_not_cdn_cached(headers)
            seen.append(header(headers, "X-Cache"))
        expect(seen == ["MISS", "HIT"], f"X-Cache lần lượt là {seen}, kỳ vọng ['MISS', 'HIT']")
        return f"id = {state['id']}, X-Cache {seen[0]} → {seen[1]}"

    def edit_invalidates():
        new_title = f"Smoke test đã sửa {time.strftime('%H%M%S')}"
        status, _, body = client.json("PUT", f"/api/posts/{state['id']}", {"title": new_title, "content": "Đã sửa."})
        expect(status == 200, f"sửa bài trả {status}: {(body or {}).get('message')}")
        status, headers, body = client.json("GET", f"/api/posts/{state['id']}")
        expect(header(headers, "X-Cache") == "MISS", f"sau khi sửa X-Cache = {header(headers, 'X-Cache')}, cache cũ chưa bị xóa")
        expect(body.get("title") == new_title, f"tiêu đề sau khi sửa là \"{body.get('title')}\"")
        return "MISS + tiêu đề mới"

    def view_counter():
        status, _, first = client.json("POST", f"/api/posts/{state['id']}/view")
        expect(status == 200, f"POST view trả {status}")
        status, _, second = client.json("POST", f"/api/posts/{state['id']}/view")
        expect(second["views"] == first["views"] + 1, f"lượt xem {first['views']} → {second['views']}")
        return f"views {first['views']} → {second['views']}"

    def spa_fallback():
        status, headers, raw = client.request("GET", f"{args.spa_url.rstrip('/')}/posts/{state['id']}")
        content_type = header(headers, "Content-Type") or ""
        expect(status == 200 and "text/html" in content_type, f"F5 ở /posts/{{id}} trả {status} {content_type}")
        expect(b'id="root"' in raw, "HTML trả về không phải trang SPA (thiếu #root)")
        return "200 text/html"

    def delete_post():
        status, _, _ = client.json("DELETE", f"/api/posts/{state['id']}")
        expect(status == 204, f"xóa bài trả {status}")
        status, _, _ = client.json("GET", f"/api/posts/{state['id']}")
        expect(status == 404, f"GET sau khi xóa trả {status}")
        state.pop("id")
        return "204 → 404"

    def logout():
        status, _, _ = client.json("POST", "/api/auth/logout")
        expect(status == 200, f"đăng xuất trả {status}")
        status, _, _ = client.json("GET", "/api/auth/me")
        expect(status == 401, f"/api/auth/me sau đăng xuất trả {status}")
        return "/api/auth/me → 401"

    try:
        step("GET /health", health)
        step("GET /api/posts", list_posts)
        step("Đăng nhập admin", login)
        step("Tạo bài, GET hai lần", create_then_miss_hit)
        step("Sửa bài xóa cache", edit_invalidates)
        step("Bộ đếm lượt xem", view_counter)
        if args.spa_url:
            step("Fallback SPA (F5 trang con)", spa_fallback)
        step("Xóa bài", delete_post)
        step("Đăng xuất", logout)
    except SmokeFailure as failure:
        print(f"FAIL  {failure}")
        if "id" in state:
            client.json("DELETE", f"/api/posts/{state['id']}")  # dọn bài test nếu còn
        return 1

    print(f"OK — {len(steps)}/{len(steps)} bước đạt trên {args.base_url}")
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # console Windows mặc định không phải UTF-8

    parser = argparse.ArgumentParser(description="Smoke test các luồng chính sau deploy.")
    parser.add_argument("--base-url", required=True, help="Gốc URL chứa /health và /api (API hoặc Vercel)")
    parser.add_argument("--admin-user", required=True, help="Tài khoản admin để tạo/sửa/xóa bài test")
    parser.add_argument("--admin-pass", default=os.environ.get("SMOKE_ADMIN_PASS"),
                        help="Mật khẩu admin (nên đặt qua biến môi trường SMOKE_ADMIN_PASS)")
    parser.add_argument("--min-posts", type=int, default=100, help="Số bài tối thiểu phải có (mặc định 100)")
    parser.add_argument("--spa-url", help="URL frontend để kiểm tra F5 ở trang con (bỏ qua nếu không có)")
    args = parser.parse_args(argv)
    if not args.admin_pass:
        parser.error("thiếu mật khẩu admin: dùng --admin-pass hoặc biến môi trường SMOKE_ADMIN_PASS")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
