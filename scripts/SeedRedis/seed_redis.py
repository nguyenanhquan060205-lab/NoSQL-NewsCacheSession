"""SCRUM-36: session demo an toàn và cache bài thật do API tạo."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import uuid

DATA = Path(__file__).resolve().parent / "data"
OBJECT_ID = re.compile(r"^[0-9a-f]{24}$")
TOKEN = re.compile(r"^scrum36-demo-[0-9a-f]{64}$")
CREATE_SESSION = """
local ttl = tonumber(ARGV[1])
if not ttl or ttl < 1 or ttl > 1800 then return redis.error_reply('TTL invalid') end
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('HSET', KEYS[1], unpack(ARGV, 2))
redis.call('EXPIRE', KEYS[1], ttl)
return 1
"""


def cache_key(post_id):
    return f"post:{post_id}"


def session_key(session_id):
    return f"session:{session_id}"


def new_token():
    return "scrum36-demo-" + secrets.token_hex(32)


def guard_user(user):
    if not user or user.get("role") != "user" or not user.get("username") or not OBJECT_ID.fullmatch(str(user.get("_id", ""))):
        raise ValueError("Cần tài khoản thường có thật, không dùng admin/fallback.")
    return {"id": str(user["_id"]), "username": user["username"], "role": "user"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Không theo redirect API, tránh gửi credential sai origin.")


class Api:
    def __init__(self, url):
        u = urlsplit(url)
        try:
            local = u.hostname == "localhost" or ipaddress.ip_address(u.hostname or "").is_loopback
        except ValueError:
            local = False
        if not local or u.scheme not in ("http", "https") or u.username or u.password or u.path not in ("", "/") or u.query or u.fragment:
            raise ValueError("API URL phải là origin loopback không chứa credential.")
        self.url = url.rstrip("/")
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, path, method="GET", token=None):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("API path không hợp lệ.")
        headers = {"Accept": "application/json"}
        if token:
            headers["X-Session-Id"] = token
        req = Request(self.url + path, method=method, headers=headers)
        try:
            response = self.opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None, dict(response.headers)


def make_plan(posts, user, total, api_url):
    if total not in (40, 50):
        raise ValueError("Tổng key chỉ nhận 40 hoặc 50.")
    account = guard_user(user)
    Api(api_url)
    n = total // 2
    if len(posts) < n:
        raise ValueError("Không đủ bài active chưa có cache trong 200 ứng viên.")
    now = int(time.time())
    return {"schema": 1, "runId": str(uuid.uuid4()), "total": total, "user": account,
            "apiUrl": api_url.rstrip("/"), "createdAt": now, "retiredTokens": [],
            "sessions": [{"id": new_token(), "ttl": 300 + i * 1500 // (n - 1),
                          "createdAt": now, "status": "planned"} for i in range(n)],
            "caches": [{"id": str(p["_id"]), "status": "planned"} for p in posts[:n]]}


def save_manifest(path, manifest):
    """Write-ahead intent, atomic replace; file chứa bearer token nên không log."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_manifest(path):
    with Path(path).open(encoding="utf-8") as stream:
        m = json.load(stream)
    n = m.get("total", 0) // 2
    if m.get("schema") != 1 or m.get("total") not in (40, 50) or len(m.get("sessions", [])) != n or len(m.get("caches", [])) != n:
        raise ValueError("Manifest không đúng schema/count.")
    Api(m["apiUrl"])
    guard_user({"_id": m["user"]["id"], **m["user"]})
    if any(not TOKEN.fullmatch(s["id"]) or not 300 <= s["ttl"] <= 1800 for s in m["sessions"]):
        raise ValueError("Manifest token/TTL không hợp lệ.")
    if any(not OBJECT_ID.fullmatch(c["id"]) for c in m["caches"]):
        raise ValueError("Manifest post ID không hợp lệ.")
    for group in ("sessions", "caches"):
        if len({x["id"] for x in m[group]}) != n:
            raise ValueError("Manifest có ID trùng.")
    return m


@contextmanager
def manifest_lock(path):
    """Chặn hai tiến trình seed cùng run; stale lock cần kiểm tra thủ công."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".lock")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def create_session(cache, item, user):
    if not TOKEN.fullmatch(item["id"]) or not 300 <= item["ttl"] <= 1800 or user["role"] != "user":
        raise ValueError("Session không đúng hợp đồng demo.")
    fields = {"userId": user["id"], "username": user["username"], "role": "user",
              "loginAt": str(item["createdAt"]), "lastActive": str(item["createdAt"])}
    args = [str(value) for pair in fields.items() for value in pair]
    return bool(cache.eval(CREATE_SESSION, 1, session_key(item["id"]), item["ttl"], *args))


def valid_session(cache, item, user):
    key = session_key(item["id"])
    if cache.type(key) != "hash" or not 0 <= cache.ttl(key) <= 1800:
        return False
    h = cache.hgetall(key)
    return (h.get("userId") == user["id"] and h.get("username") == user["username"]
            and h.get("role") == "user" and h.get("loginAt", "").isdigit()
            and h.get("lastActive", "").isdigit())


def equal_post(payload, post, casing="cache"):
    if not isinstance(payload, dict) or not post or post.get("isDeleted") is True:
        return False
    fields = {"Id": str(post["_id"]), "Title": post.get("title"), "Content": post.get("content"),
              "Slug": post.get("slug"), "CategoryId": str(post["categoryId"]) if post.get("categoryId") else None}
    for name in ("imageUrl", "authorId"):
        if name in post:
            value = post[name]
            fields[name[0].upper() + name[1:]] = str(value) if name == "authorId" and value is not None else value
    for name, value in fields.items():
        key = name if casing == "cache" else name[0].lower() + name[1:]
        if payload.get(key) != value:
            return False
    for name in ("createdAt", "updatedAt"):
        if name in post:
            key = name[0].upper() + name[1:] if casing == "cache" else name
            try:
                actual = datetime.fromisoformat(payload[key].replace("Z", "+00:00"))
                expected = post[name]
                if actual.replace(tzinfo=None) != expected.astimezone(timezone.utc).replace(tzinfo=None):
                    return False
            except (KeyError, TypeError, ValueError, AttributeError):
                return False
    return True


def valid_cache(cache, item, post):
    key = cache_key(item["id"])
    if cache.type(key) != "string" or not 0 <= cache.ttl(key) <= 600:
        return False
    try:
        return equal_post(json.loads(cache.get(key)), post)
    except (TypeError, ValueError):
        return False


def snapshot(m, cache, posts):
    sessions = sum(valid_session(cache, s, m["user"]) for s in m["sessions"])
    caches = sum(valid_cache(cache, c, posts.get(c["id"])) for c in m["caches"])
    n = m["total"] // 2
    return {"ok": sessions == caches == n, "runId": m["runId"], "target": m["total"],
            "sessions": sessions, "caches": caches, "live": sessions + caches,
            "missingOrInvalid": m["total"] - sessions - caches,
            "statuses": {g: dict(Counter(x["status"] for x in m[g])) for g in ("sessions", "caches")}}


def execute(m, cache, api, path, posts):
    save_manifest(path, m)
    for index, item in enumerate(m["sessions"]):
        key = session_key(item["id"])
        if valid_session(cache, item, m["user"]):
            item["status"] = "reused"
        else:
            # Không hồi sinh token đã hết hạn/thu hồi; collision không ghi đè.
            if item["status"] != "planned" or cache.exists(key):
                m["retiredTokens"].append(item["id"])
                item = {**item, "id": new_token(), "createdAt": int(time.time()), "status": "planned"}
                m["sessions"][index] = item
            item["status"] = "creating"
            save_manifest(path, m)
            if not create_session(cache, item, m["user"]):
                raise RuntimeError("Collision session; resume sẽ cấp token mới.")
            item["status"] = "created"
        save_manifest(path, m)
    for item in m["caches"]:
        p = posts.get(item["id"])
        if not p or p.get("isDeleted") is True:
            item["status"] = "skipped"
        elif cache.exists(cache_key(item["id"])):
            item["status"] = "reused" if valid_cache(cache, item, p) else "invalid"
        else:
            item["status"] = "warming"
            save_manifest(path, m)
            code, body, headers = api.request("/api/posts/" + item["id"])
            if code != 200 or not equal_post(body, p, "http") or not valid_cache(cache, item, p):
                raise RuntimeError("API/cache không khớp Mongo hoặc TTL/type/casing sai.")
            cache_header = next((v for k, v in headers.items() if k.lower() == "x-cache"), None)
            if cache_header not in ("HIT", "MISS"):
                raise RuntimeError("Thiếu header X-Cache hợp lệ.")
            item["status"] = "created" if cache_header == "MISS" else "reused"
        save_manifest(path, m)
    return snapshot(m, cache, posts)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--total", type=int, choices=(40, 50), default=40)
    p.add_argument("--demo-username", required=True)
    p.add_argument("--api-url", default="http://localhost:5134")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--resume", type=Path)
    return p.parse_args(argv)


def connect():
    import redis
    from pymongo import MongoClient
    # Hợp đồng API local hiện có: DB newsdb, Redis DB 0; không suy đoán môi trường khác.
    mongo = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if mongo not in ("mongodb://localhost:27017", "mongodb://127.0.0.1:27017") or redis_url not in ("redis://localhost:6379/0", "redis://127.0.0.1:6379/0") or os.getenv("MONGODB_DATABASE", "newsdb") != "newsdb":
        raise ValueError("Script chỉ hỗ trợ môi trường local newsdb/Redis DB 0 đã chốt.")
    client = MongoClient(mongo, serverSelectionTimeoutMS=5000, tz_aware=True)
    cache = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5)
    try:
        client.admin.command("ping")
        cache.ping()
    except Exception:
        client.close()
        cache.close()
        raise
    return client, cache


def preflight(db, cache, api, username, n, manifest=None):
    from bson import ObjectId
    user = db.users.find_one({"username": username}, {"username": 1, "role": 1})
    account = guard_user(user)
    if manifest and (manifest["user"] != account or manifest["apiUrl"] != api.url):
        raise ValueError("Account/origin không khớp manifest.")
    code, _, _ = api.request("/health")
    if code != 200:
        raise RuntimeError("API health chưa sẵn sàng.")
    needed = sum(not valid_session(cache, s, account) for s in manifest["sessions"]) if manifest else n
    count = 0
    for key in cache.scan_iter(match="session:*", count=100):
        count += 1
        if cache.type(key) != "hash":
            raise ValueError("Có session wrong-type, API admin không đọc được; báo owner.")
        if count + needed > 200:
            raise ValueError("Vượt 200 phiên của API admin; không tự xóa phiên.")
    if manifest:
        selected = list(db.posts.find({"_id": {"$in": [ObjectId(c["id"]) for c in manifest["caches"]]}}))
    else:
        candidates = db.posts.find({"isDeleted": {"$ne": True}}).sort("createdAt", -1).limit(200)
        selected = []
        for post in candidates:
            if post.get("title") and post.get("content") and not cache.exists(cache_key(str(post["_id"]))):
                selected.append(post)
                if len(selected) == n:
                    break
        if len(selected) < n:
            raise ValueError("Không đủ cache absent trong 200 bài; không xóa cache hiện có.")
    # Endpoint slug không cache: xác nhận API đọc đúng DB trước bất kỳ mutation nào.
    for post in selected:
        if post.get("isDeleted") is not True:
            code, body, _ = api.request("/api/posts/slug/" + quote(post["slug"], safe=""))
            if code != 200 or not equal_post(body, post, "http"):
                raise ValueError("API/Mongo khác môi trường hoặc dữ liệu không đúng contract.")
    return user, selected


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    client = cache = None
    manifest = path = None
    posts = []
    try:
        api = Api(args.api_url)
        client, cache = connect()
        if args.resume:
            path = args.resume.resolve()
            if path.parent != DATA.resolve():
                raise ValueError("Resume chỉ đọc manifest trong scripts/SeedRedis/data/.")
        else:
            path = DATA / (str(uuid.uuid4()) + ".json")
        # Dry-run không tạo file/lock/token; chỉ đọc DB/Redis và API slug không cache.
        if args.dry_run:
            manifest = load_manifest(path) if args.resume else None
            if manifest and manifest["total"] != args.total:
                raise ValueError("Total không khớp manifest.")
            preflight(client.newsdb, cache, api, args.demo_username, args.total // 2, manifest)
            print(json.dumps({"ok": True, "dryRun": True, "total": args.total, "sessions": args.total // 2, "caches": args.total // 2, "writes": 0}))
            return 0
        with manifest_lock(path):
            manifest = load_manifest(path) if args.resume else None
            if manifest and manifest["total"] != args.total:
                raise ValueError("Total không khớp manifest.")
            user, posts = preflight(client.newsdb, cache, api, args.demo_username, args.total // 2, manifest)
            manifest = manifest or make_plan(posts, user, args.total, api.url)
            result = execute(manifest, cache, api, path, {str(p["_id"]): p for p in posts})
            print(json.dumps({**result, "manifest": str(path)}, ensure_ascii=False))
            return 0 if result["ok"] else 1
    except Exception as error:
        # Không in exception body/URL vì revoke paths và manifest chứa bearer token.
        result = {"ok": False, "errorType": type(error).__name__, "message": "Chạy chưa hoàn tất; kiểm tra preflight và dùng manifest để resume."}
        if manifest is not None and cache is not None:
            result["manifest"] = str(path)
            try:
                result["partial"] = snapshot(manifest, cache, {str(p["_id"]): p for p in posts})
            except Exception:
                result["partial"] = "Redis chưa đọc được; dùng manifest để resume."
        print(json.dumps(result, ensure_ascii=False))
        return 1
    finally:
        if client is not None:
            client.close()
        if cache is not None:
            cache.close()


if __name__ == "__main__":
    raise SystemExit(main())
