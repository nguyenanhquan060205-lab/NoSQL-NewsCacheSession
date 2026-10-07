"""Xác minh manifest chỉ đọc; demo API có side effects phải opt-in rõ ràng."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import seed_redis as seed


def live_demo(m, cache, api, posts, admin_token=None, revoke=False, save=None):
    results = {"cacheHits": 0, "admin": "pending: thiếu SCRUM36_ADMIN_SESSION", "sliding": False}
    for c in m["caches"][:2]:
        code, body, headers = api.request("/api/posts/" + c["id"])
        hit = next((v for k, v in headers.items() if k.lower() == "x-cache"), "")
        if code != 200 or hit != "HIT" or not seed.equal_post(body, posts.get(c["id"]), "http"):
            raise RuntimeError("Cache live demo không HIT đúng dữ liệu.")
        results["cacheHits"] += 1
    token = m["sessions"][-1]["id"]
    code, me, _ = api.request("/api/auth/me", token=token)
    if code != 200 or me.get("userId") != m["user"]["id"] or me.get("role") != "user":
        raise RuntimeError("Session demo không xác thực đúng user.")
    if not 1700 <= cache.ttl(seed.session_key(token)) <= 1800:
        raise RuntimeError("Sliding TTL không về 30 phút.")
    results["sliding"] = True
    code, _, _ = api.request("/api/auth/sessions", token=token)
    if code != 403:
        raise RuntimeError("User thường không bị chặn ở admin endpoint.")
    results["userAdminDenied"] = True
    if not admin_token:
        if revoke:
            raise ValueError("Revoke cần credential admin do người dùng cung cấp.")
        return results
    code, admin, _ = api.request("/api/auth/me", token=admin_token)
    if code != 200 or admin.get("role") != "admin":
        raise ValueError("Credential không phải admin hợp lệ.")
    code, items, _ = api.request("/api/auth/sessions", token=admin_token)
    expected = {s["id"] for s in m["sessions"]}
    if code != 200 or not isinstance(items, list) or not expected <= {s.get("sessionId") for s in items}:
        raise RuntimeError("API admin không liệt kê đủ phiên trong run.")
    results["admin"] = "pass"
    if revoke:
        item = m["sessions"][0]
        # Ghi intent trước DELETE để local crash không mất dấu session đã thu hồi.
        item["status"] = "revoking"
        if save:
            save()
        code, _, _ = api.request("/api/auth/sessions/" + item["id"], method="DELETE", token=admin_token)
        denied, _, _ = api.request("/api/auth/me", token=item["id"])
        if code != 204 or cache.exists(seed.session_key(item["id"])) or denied != 401:
            raise RuntimeError("Revoke chưa vô hiệu hóa session.")
        item["status"] = "revoked"
        if save:
            save()
        results["revoke"] = True
    return results


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--live-api-demo", action="store_true")
    parser.add_argument("--revoke-one", action="store_true")
    args = parser.parse_args(argv)
    if args.revoke_one and not args.live_api_demo:
        parser.error("--revoke-one cần --live-api-demo; mặc định chỉ đọc.")
    client = cache = None
    try:
        from bson import ObjectId
        path = args.manifest.resolve()
        if path.parent != seed.DATA.resolve():
            raise ValueError("Chỉ đọc manifest trong thư mục data/ được ignore.")
        m = seed.load_manifest(path)
        client, cache = seed.connect()
        db = client.newsdb
        user = db.users.find_one({"_id": ObjectId(m["user"]["id"])}, {"username": 1, "role": 1})
        if seed.guard_user(user) != m["user"]:
            raise ValueError("Account trong manifest không còn hợp lệ.")
        posts = {str(p["_id"]): p for p in db.posts.find({"_id": {"$in": [ObjectId(c["id"]) for c in m["caches"]]}})}
        before = seed.snapshot(m, cache, posts)
        before["snapshotAt"] = int(time.time())
        if args.live_api_demo and before["ok"]:
            api = seed.Api(m["apiUrl"])
            seed.preflight(db, cache, api, m["user"]["username"], m["total"] // 2, m)
            admin_token = os.getenv("SCRUM36_ADMIN_SESSION")
            if admin_token:
                code, admin, _ = api.request("/api/auth/me", token=admin_token)
                account = db.users.find_one({"_id": ObjectId(admin["userId"])}, {"username": 1, "role": 1}) if code == 200 else None
                if not account or account.get("role") != "admin" or account.get("username") != admin.get("username"):
                    raise ValueError("Admin credential không khớp DB hiện tại.")
            if args.revoke_one and not admin_token:
                raise ValueError("Thiếu credential admin; không revoke.")
            with seed.manifest_lock(path):
                # Seed có thể vừa resume giữa preflight và lock: không dùng token snapshot cũ.
                m = seed.load_manifest(path)
                if seed.guard_user(user) != m["user"]:
                    raise ValueError("Account manifest đã thay đổi trong lúc verify.")
                before = seed.snapshot(m, cache, posts)
                before["snapshotAt"] = int(time.time())
                if not before["ok"]:
                    raise RuntimeError("Run thay đổi trước demo; xác minh snapshot lại.")
                before["demo"] = live_demo(m, cache, api, posts, admin_token, args.revoke_one,
                                           lambda: seed.save_manifest(path, m))
                before["afterDemo"] = seed.snapshot(m, cache, posts)
                before["note"] = "TTL phiên được dùng đã gia hạn; revoke giảm target 1 là expected."
        print(json.dumps(before, ensure_ascii=False))
        return 0 if before["ok"] else 1
    except Exception as error:
        print(json.dumps({"ok": False, "errorType": type(error).__name__, "message": "Xác minh chưa đạt; không in token hoặc URL credential."}, ensure_ascii=False))
        return 1
    finally:
        if client is not None:
            client.close()
        if cache is not None:
            cache.close()


if __name__ == "__main__":
    raise SystemExit(main())
