"""Live local opt-in. Không sửa Mongo; chỉ xóa đúng key test vừa tạo."""
import os
import time
import unittest
import uuid

import seed_redis as seed


@unittest.skipUnless(os.getenv("RUN_REDIS_INTEGRATION") == "1", "Opt-in RUN_REDIS_INTEGRATION=1 trên local/test")
class LiveRedisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client, cls.cache = seed.connect()
        cls.api = seed.Api("http://localhost:5134")

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.cache.close()

    def test_health_and_mongo_camelcase(self):
        self.assertEqual(self.api.request("/health")[0], 200)
        p = self.client.newsdb.posts.find_one({"isDeleted": False})
        self.assertTrue(p["title"])
        self.assertNotIn("Title", p)

    def test_lua_atomic_nx_and_expiry_isolated_key(self):
        key = "scrum36-test:" + str(uuid.uuid4())
        # Không tạo session bearer giả: namespace test không được middleware đọc.
        try:
            args = (seed.CREATE_SESSION, 1, key, 2, "marker", "test")
            self.assertEqual(self.cache.eval(*args), 1)
            self.assertGreater(self.cache.pttl(key), 0)
            before = self.cache.hgetall(key)
            self.assertEqual(self.cache.eval(seed.CREATE_SESSION, 1, key, 1800, "marker", "changed"), 0)
            self.assertEqual(self.cache.hgetall(key), before)
            self.assertLessEqual(self.cache.ttl(key), 2)
            time.sleep(2.2)
            self.assertFalse(self.cache.exists(key))
        finally:
            self.cache.delete(key)

    def test_backend_cache_miss_hit_preserves_counter(self):
        p = next((p for p in self.client.newsdb.posts.find({"isDeleted": False}).sort("createdAt", -1).limit(200)
                  if not self.cache.exists(seed.cache_key(str(p["_id"])))), None)
        self.assertIsNotNone(p, "Cần một bài chưa có cache; không xóa cache thật để tạo MISS")
        item = {"id": str(p["_id"])}
        counter = seed.cache_key(item["id"]) + ":views"
        before = self.cache.get(counter)
        code, body, headers = self.api.request("/api/posts/" + item["id"])
        self.assertEqual(code, 200)
        self.assertEqual(headers.get("X-Cache"), "MISS")
        self.assertTrue(seed.equal_post(body, p, "http"))
        self.assertTrue(seed.valid_cache(self.cache, item, p))
        ttl = self.cache.pttl(seed.cache_key(item["id"]))
        code, body, headers = self.api.request("/api/posts/" + item["id"])
        self.assertEqual(headers.get("X-Cache"), "HIT")
        self.assertTrue(seed.equal_post(body, p, "http"))
        self.assertLessEqual(self.cache.pttl(seed.cache_key(item["id"])), ttl)
        self.assertEqual(self.cache.get(counter), before)

    def test_real_user_auth_if_supplied(self):
        username = os.getenv("SCRUM36_DEMO_USERNAME")
        if not username:
            self.skipTest("Thiếu SCRUM36_DEMO_USERNAME có thật; không tạo user giả")
        user = self.client.newsdb.users.find_one({"username": username}, {"username": 1, "role": 1})
        account = seed.guard_user(user)
        item = {"id": seed.new_token(), "ttl": 300, "createdAt": int(time.time())}
        key = seed.session_key(item["id"])
        try:
            self.assertTrue(seed.create_session(self.cache, item, account))
            self.assertEqual(self.api.request("/api/auth/me", token=item["id"])[0], 200)
            self.assertGreater(self.cache.ttl(key), 1700)
            self.assertEqual(self.api.request("/api/auth/sessions", token=item["id"])[0], 403)
        finally:
            self.cache.delete(key)
        self.assertEqual(self.api.request("/api/auth/me", token=item["id"])[0], 401)


if __name__ == "__main__":
    unittest.main()
