"""Regression SCRUM-36, không kết nối dữ liệu thật."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from contextlib import redirect_stdout, redirect_stderr
import io
import seed_redis as seed
import verify_seed_redis as verify


def post(i):
    return {"_id": f"{i:024x}", "title": f"Bài {i}", "content": "Nội dung",
            "slug": f"bai-{i}", "categoryId": "a" * 24, "isDeleted": False}


USER = {"_id": "b" * 24, "username": "demo", "role": "user"}


class FakeRedis:
    def __init__(self):
        self.values, self.ttls, self.writes = {}, {}, []

    def type(self, key):
        v = self.values.get(key)
        return "none" if v is None else "hash" if isinstance(v, dict) else "string"

    def close(self):
        pass

    def exists(self, key):
        return key in self.values

    def get(self, key):
        return self.values.get(key)

    def ttl(self, key):
        return self.ttls.get(key, -2)

    def hgetall(self, key):
        return self.values.get(key, {})

    def eval(self, script, number, key, ttl, *fields):
        if key in self.values:
            return 0
        self.values[key] = dict(zip(fields[::2], fields[1::2]))
        self.ttls[key] = int(ttl)
        self.writes.append(key)
        return 1


class FakeApi:
    def __init__(self, cache, posts):
        self.cache, self.posts = cache, {str(p["_id"]): p for p in posts}
        self.calls, self.fail_after_write = [], False

    def request(self, path, method="GET", token=None):
        self.calls.append((path, method, token))
        p = self.posts[path.rsplit("/", 1)[1]]
        key = seed.cache_key(str(p["_id"]))
        hit = self.cache.exists(key)
        payload = {"Id": str(p["_id"]), "Title": p["title"], "Content": p["content"],
                   "Slug": p["slug"], "CategoryId": str(p["categoryId"])}
        if not hit:
            self.cache.values[key], self.cache.ttls[key] = json.dumps(payload), 600
        if self.fail_after_write:
            self.fail_after_write = False
            raise TimeoutError("API timeout")
        return 200, {k[0].lower() + k[1:]: v for k, v in payload.items()}, {"X-Cache": "HIT" if hit else "MISS"}


class SeedRedisTests(unittest.TestCase):
    def setUp(self):
        self.posts = [post(i) for i in range(1, 41)]
        self.cache = FakeRedis()
        self.api = FakeApi(self.cache, self.posts)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "run.json"
        self.by_id = {str(p["_id"]): p for p in self.posts}

    def plan(self, total=40):
        return seed.make_plan(self.posts, USER, total, "http://localhost:5134")

    def execute(self, m):
        return seed.execute(m, self.cache, self.api, self.path, self.by_id)

    def test_split_40_and_50(self):
        for total in (40, 50):
            m = self.plan(total)
            self.assertEqual((len(m["sessions"]), len(m["caches"])), (total // 2, total // 2))

    def test_execute_50_live_count(self):
        result = self.execute(self.plan(50))
        self.assertTrue(result["ok"])
        self.assertEqual((result["sessions"], result["caches"], result["live"]), (25, 25, 50))

    def test_invalid_totals(self):
        for total in (0, 39, 41, 48, 51):
            with self.assertRaises(ValueError):
                self.plan(total)

    def test_reject_admin_missing_fake_account(self):
        for user in (None, {}, {**USER, "role": "admin"}, {**USER, "role": None}, {**USER, "_id": "fake"}):
            with self.assertRaises(ValueError):
                seed.make_plan(self.posts, user, 40, "http://localhost:5134")

    def test_random_tokens_and_current_dates(self):
        a, b = self.plan(), self.plan()
        ids = [s["id"] for m in (a, b) for s in m["sessions"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(s.rsplit("-", 1)[1]) == 64 for s in ids))
        self.assertGreater(a["createdAt"], 1_790_000_000)

    def test_ttl_profile(self):
        for total in (40, 50):
            ttls = [s["ttl"] for s in self.plan(total)["sessions"]]
            self.assertEqual((min(ttls), max(ttls)), (300, 1800))
            self.assertEqual(len(ttls), len(set(ttls)))

    def test_loopback_only_no_url_credentials(self):
        for url in ("http://example.com", "http://localhost.evil.test", "http://u:p@localhost", "file:///tmp/x", "http://localhost:5134/path"):
            with self.assertRaises(ValueError):
                seed.Api(url)
        seed.Api("http://127.0.0.1:5134")

    def test_redirect_is_not_followed(self):
        with self.assertRaises(ValueError):
            seed.NoRedirect().redirect_request(None, None, 302, "", {}, "http://evil.test")

    def test_cli_invalid_before_network(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            seed.parse_args(["--total", "41", "--demo-username", "demo"])

    def test_atomic_nx(self):
        m = self.plan()
        s = m["sessions"][0]
        self.assertTrue(seed.create_session(self.cache, s, m["user"]))
        key = seed.session_key(s["id"])
        before = copy.deepcopy(self.cache.values[key])
        self.assertFalse(seed.create_session(self.cache, s, m["user"]))
        self.assertEqual(before, self.cache.values[key])
        self.assertEqual(self.cache.ttl(key), s["ttl"])
        self.assertEqual(set(before), {"userId", "username", "role", "loginAt", "lastActive"})

    def test_resume_does_not_reset_existing(self):
        m = self.plan()
        self.assertEqual(self.execute(m)["live"], 40)
        sk, ck = seed.session_key(m["sessions"][0]["id"]), seed.cache_key(m["caches"][0]["id"])
        self.cache.ttls[sk], self.cache.ttls[ck] = 100, 90
        before = copy.deepcopy(self.cache.values)
        self.assertTrue(self.execute(m)["ok"])
        self.assertEqual(before, self.cache.values)
        self.assertEqual((self.cache.ttl(sk), self.cache.ttl(ck)), (100, 90))
        self.assertTrue(all(t is None for _, _, t in self.api.calls))

    def test_resume_rotates_missing_session(self):
        m = self.plan()
        self.execute(m)
        old = m["sessions"][0]["id"]
        self.cache.values.pop(seed.session_key(old))
        self.cache.ttls.pop(seed.session_key(old))
        self.assertTrue(self.execute(m)["ok"])
        self.assertNotEqual(m["sessions"][0]["id"], old)
        self.assertIn(old, m["retiredTokens"])
        self.assertFalse(self.cache.exists(seed.session_key(old)))

    def test_cache_intent_recovers_after_timeout(self):
        m = self.plan()
        self.api.fail_after_write = True
        with self.assertRaises(TimeoutError):
            self.execute(m)
        saved = seed.load_manifest(self.path)
        ids = [c["id"] for c in saved["caches"]]
        self.assertTrue(self.execute(saved)["ok"])
        self.assertEqual(ids, [c["id"] for c in saved["caches"]])
        self.assertEqual(len([k for k in self.cache.values if k.startswith("post:")]), 20)

    def test_collision_never_overwrites(self):
        m = self.plan()
        old = m["sessions"][0]["id"]
        key = seed.session_key(old)
        self.cache.values[key], self.cache.ttls[key] = "other", 80
        self.assertTrue(self.execute(m)["ok"])
        self.assertEqual((self.cache.values[key], self.cache.ttl(key)), ("other", 80))
        self.assertNotEqual(m["sessions"][0]["id"], old)

    def test_wrong_payload_or_type_fails_snapshot(self):
        m = self.plan()
        self.execute(m)
        key = seed.cache_key(m["caches"][0]["id"])
        for value in ('{"title":"bad"}', {}, 'not json'):
            self.cache.values[key] = value
            self.assertFalse(seed.snapshot(m, self.cache, self.by_id)["ok"])

    def test_foreign_data_untouched(self):
        self.cache.values.update({"posts:ver": "8", "post:foreign:views": "99", "session:foreign": {"role": "admin"}})
        self.cache.ttls["session:foreign"] = 321
        before = copy.deepcopy(self.cache.values)
        self.execute(self.plan())
        self.assertTrue(all(self.cache.values[k] == v for k, v in before.items()))
        self.assertEqual(self.cache.ttl("session:foreign"), 321)

    def test_snapshot_does_not_write(self):
        m = self.plan()
        self.execute(m)
        before = len(self.cache.writes), len(self.api.calls)
        seed.snapshot(m, self.cache, self.by_id)
        self.assertEqual(before, (len(self.cache.writes), len(self.api.calls)))

    def test_preexisting_cache_ttl_preserved(self):
        m = self.plan()
        item = m["caches"][0]
        self.api.request("/api/posts/" + item["id"])
        self.cache.ttls[seed.cache_key(item["id"])] = 99
        self.execute(m)
        self.assertEqual(self.cache.ttl(seed.cache_key(item["id"])), 99)
        self.assertEqual(item["status"], "reused")

    def test_manifest_roundtrip(self):
        m = self.plan()
        seed.save_manifest(self.path, m)
        self.assertEqual(seed.load_manifest(self.path), m)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_dry_run_no_writes_no_tokens_no_manifest(self):
        client = Mock()
        with patch.object(seed, "connect", return_value=(client, self.cache)), patch.object(seed, "preflight", return_value=(USER, self.posts)), patch.object(seed, "make_plan") as make, patch.object(seed, "DATA", Path(self.tmp.name)), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(seed.main(["--demo-username", "demo", "--dry-run"]), 0)
            make.assert_not_called()
        self.assertEqual(self.cache.writes, [])
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])
        self.assertNotIn("scrum36-demo-", output.getvalue())

    def test_no_ttl_session_fails_snapshot(self):
        m = self.plan()
        self.execute(m)
        self.cache.ttls[seed.session_key(m["sessions"][0]["id"])] = -1
        self.assertFalse(seed.snapshot(m, self.cache, self.by_id)["ok"])

    def test_cache_race_hit_is_reused(self):
        m = self.plan()
        original = self.api.request
        def race(path, **kwargs):
            original(path)
            return original(path, **kwargs)
        self.api.request = race
        self.execute(m)
        self.assertTrue(all(c["status"] == "reused" for c in m["caches"]))

    def test_manifest_tampering_rejected(self):
        for mutate in (lambda m: m["sessions"][0].update(ttl=9999), lambda m: m["caches"][0].update(id="evil"), lambda m: m["user"].update(role="admin")):
            m = self.plan()
            mutate(m)
            seed.save_manifest(self.path, m)
            with self.assertRaises(ValueError):
                seed.load_manifest(self.path)

    def test_double_process_manifest_lock(self):
        with seed.manifest_lock(self.path):
            with self.assertRaises(FileExistsError):
                with seed.manifest_lock(self.path):
                    pass
        self.assertFalse(self.path.with_suffix(".lock").exists())

    def test_partial_manifest_after_redis_failure(self):
        m = self.plan()
        original = self.cache.eval
        def fail_second(*args):
            if len(self.cache.writes) == 1:
                raise ConnectionError("Redis unavailable")
            return original(*args)
        self.cache.eval = fail_second
        with self.assertRaises(ConnectionError):
            self.execute(m)
        saved = seed.load_manifest(self.path)
        self.cache.eval = original
        self.assertTrue(self.execute(saved)["ok"])
        self.assertEqual(len(self.cache.values), 40)

    def test_deleted_post_not_warmed(self):
        m = self.plan()
        self.by_id[m["caches"][0]["id"]]["isDeleted"] = True
        result = self.execute(m)
        self.assertFalse(result["ok"])
        self.assertEqual(result["caches"], 19)

    def test_cli_zero_write_preflight_failure(self):
        with patch.object(seed, "connect", return_value=(Mock(), self.cache)), patch.object(seed, "preflight", side_effect=ValueError("Missing user")), patch.object(seed, "DATA", Path(self.tmp.name)), redirect_stdout(io.StringIO()):
            self.assertEqual(seed.main(["--demo-username", "missing"]), 1)
        self.assertEqual(self.cache.writes, [])
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_verifier_revoke_requires_optin(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            verify.main([str(self.path), "--revoke-one"])

    def test_verifier_default_no_api_calls(self):
        m = self.plan()
        self.execute(m)
        client = Mock()
        client.newsdb.users.find_one.return_value = USER
        client.newsdb.posts.find.return_value = self.posts
        with patch.object(seed, "connect", return_value=(client, self.cache)), patch.object(seed, "DATA", self.path.parent), patch.object(seed, "Api") as api, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(verify.main([str(self.path)]), 0)
            api.assert_called_once()  # load_manifest chỉ validate URL, không request.
            api.return_value.request.assert_not_called()
        self.assertTrue(json.loads(output.getvalue())["ok"])

    def test_verifier_missing_key_nonzero(self):
        m = self.plan()
        self.execute(m)
        self.cache.values.pop(seed.cache_key(m["caches"][0]["id"]))
        client = Mock()
        client.newsdb.users.find_one.return_value = USER
        client.newsdb.posts.find.return_value = self.posts
        with patch.object(seed, "connect", return_value=(client, self.cache)), patch.object(seed, "DATA", self.path.parent), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(verify.main([str(self.path)]), 1)
        self.assertEqual(json.loads(output.getvalue())["missingOrInvalid"], 1)

    def test_live_demo_wrong_admin_cannot_revoke(self):
        m = self.plan()
        self.execute(m)
        original = self.api.request
        def request(path, method="GET", token=None):
            if path.startswith("/api/posts/"):
                return original(path, method, token)
            if path == "/api/auth/me":
                if token == "bad-admin":
                    return 401, {}, {}
                self.cache.ttls[seed.session_key(token)] = 1800
                return 200, {"userId": USER["_id"], "role": "user"}, {}
            if path == "/api/auth/sessions":
                return 403, {}, {}
            self.fail("Không được revoke khi admin sai")
        self.api.request = request
        with self.assertRaises(ValueError):
            verify.live_demo(m, self.cache, self.api, self.by_id, "bad-admin", True)
        self.assertEqual(seed.snapshot(m, self.cache, self.by_id)["live"], 40)

    def test_live_demo_without_admin_reports_pending(self):
        m = self.plan()
        self.execute(m)
        original = self.api.request
        def request(path, method="GET", token=None):
            if path.startswith("/api/posts/"):
                return original(path, method, token)
            if path == "/api/auth/me":
                self.cache.ttls[seed.session_key(token)] = 1800
                return 200, {"userId": USER["_id"], "role": "user"}, {}
            return 403, {}, {}
        self.api.request = request
        result = verify.live_demo(m, self.cache, self.api, self.by_id)
        self.assertIn("pending", result["admin"])
        self.assertEqual(result["cacheHits"], 2)
        self.assertTrue(result["sliding"])

    def test_live_admin_list_revoke_and_resume_new_token(self):
        m = self.plan()
        self.execute(m)
        original = self.api.request
        old = m["sessions"][0]["id"]
        def request(path, method="GET", token=None):
            if path.startswith("/api/posts/"):
                return original(path, method, token)
            if path == "/api/auth/me":
                if token == "test-admin":
                    return 200, {"role": "admin"}, {}
                if not self.cache.exists(seed.session_key(token)):
                    return 401, {}, {}
                self.cache.ttls[seed.session_key(token)] = 1800
                return 200, {"userId": USER["_id"], "role": "user"}, {}
            if path == "/api/auth/sessions":
                return (200, [{"sessionId": s["id"]} for s in m["sessions"]], {}) if token == "test-admin" else (403, {}, {})
            if method == "DELETE" and token == "test-admin":
                self.cache.values.pop(seed.session_key(path.rsplit("/", 1)[1]))
                return 204, None, {}
            self.fail("Unexpected API call")
        self.api.request = request
        result = verify.live_demo(m, self.cache, self.api, self.by_id, "test-admin", True,
                                  lambda: seed.save_manifest(self.path, m))
        self.assertTrue(result["revoke"])
        self.assertEqual(seed.snapshot(m, self.cache, self.by_id)["live"], 39)
        self.execute(m)
        self.assertNotEqual(m["sessions"][0]["id"], old)
        self.assertEqual(request("/api/auth/me", token=old)[0], 401)


if __name__ == "__main__":
    unittest.main()
