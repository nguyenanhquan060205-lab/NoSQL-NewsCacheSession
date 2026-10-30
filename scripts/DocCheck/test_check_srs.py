import json
import os
import pathlib
import tempfile
import unittest
import zipfile

# check_srs module import (will raise ModuleNotFoundError if not created yet)
try:
    from scripts.DocCheck import check_srs
except ImportError:
    import check_srs


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestCheckSrsHermetic(unittest.TestCase):
    """Hermetic tests using temp directories and synthetic data."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.temp_dir.name)

        # Base facts
        self.facts = {
            "endpoints": {
                "get /api/posts",
                "get /api/posts/{}",
                "get /api/posts/slug/{}",
                "post /api/posts",
                "put /api/posts/{}",
                "delete /api/posts/{}",
                "post /api/posts/{}/view",
                "get /api/categories",
                "get /api/categories/{}",
                "get /api/categories/slug/{}",
                "post /api/categories",
                "post /api/auth/register",
                "post /api/auth/login",
                "post /api/auth/logout",
                "get /api/auth/me",
                "get /api/auth/sessions",
                "delete /api/auth/sessions/{}",
                "get /api/cache/stats",
                "post /api/images",
                "get /health",
                "get /api/health",
            },
            "cookie_name": "SessionId",
            "session_header": "X-Session-Id",
            "cache_header": "X-Cache",
            "stats_fields": {"hits", "misses", "totalRequests", "hitRate"},
            "ports": {27017, 6379, 5540, 5134, 58320, 7295, 3000, 27019, 6380, 5135},
            "compose_ports": {"27017:27017", "6379:6379", "5540:5540"},
            "versions": {
                "react": "19",
                "vite": "8",
                "tailwindcss": "4",
                "mongo_driver": "3",
                "stackexchange_redis": "3",
                "mongo_image": "mongo:7.0",
                "redis_image": "redis:7-alpine",
                "net_app": "net8.0",
                "net_test": "net10.0",
            },
            "summary": {
                "latency": {
                    "khong-cache": {"mean": 3.66, "median": 3.59, "p95": 4.46, "p99": 4.63, "min": 2.88},
                    "cache-miss": {"mean": 8.74, "median": 8.57, "p95": 10.42, "p99": 10.90, "min": 7.31},
                    "cache-hit": {"mean": 2.96, "median": 2.92, "p95": 3.55, "p99": 3.82, "min": 2.31},
                },
                "stampede": [{}, {}, {}, {}, {}],
                "rps": {328.1, 279.0, 889.4, 875.5, 885.6, 762.5},
            },
            "jira_tasks": {f"SCRUM-{i}": "Done" for i in range(13, 50)},
            "docx_paragraphs": [
                "1. Tiêu đề",
                "Trang tin tức trực tuyến có phân hệ đăng nhập, đọc bài viết; hệ thống tích hợp bộ nhớ đệm để tăng tốc độ tải trang.",
                "Hệ quản trị CSDL chính: Redis (Phối hợp MongoDB / MySQL làm DB gốc)",
            ],
            "keyspace": [
                {"key": "session:{sessionId}", "ttl": "30 phút"},
                {"key": "post:{postId}", "ttl": "10 phút"},
                {"key": "post:{postId}:views", "ttl": "Không TTL"},
                {"key": "posts:cat:{categoryId}:p{n}:v{ver}", "ttl": "3 phút"},
                {"key": "posts:ver", "ttl": "Không TTL"},
                {"key": "lock:post:{postId}", "ttl": "5 giây"},
                {"key": "posts:dirty_views", "ttl": "Không TTL"},
            ],
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_c1_endpoint_khong_hop_le_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "API: `POST /api/images/upload`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c1(srs, self.facts)
        self.assertTrue(any("POST /api/images/upload" in e for e in errors))

    def test_c1_endpoint_hop_le_dat(self):
        srs = check_srs.SRS(
            lines=[
                (1, "Endpoint: `GET /api/posts/{id}`"),
                (2, "Upload: `POST /api/images`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c1(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c2_thieu_endpoint_code_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "`GET /api/posts`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c2(srs, self.facts)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("GET /api/auth/me" in e for e in errors))

    def test_c2_du_endpoint_dat(self):
        lines = []
        for i, ep in enumerate(self.facts["endpoints"]):
            verb, path = ep.split()
            # replace {} with sample
            p = path.replace("{}", "{id}")
            lines.append((i + 1, f"Endpoint: `{verb.upper()} {p}`"))
        srs = check_srs.SRS(lines=lines, ignore_ranges=[])
        errors = check_srs.check_c2(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c3_duong_dan_khong_ton_tai_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "Sử dụng component `src/frontend/src/components/CacheBadge.jsx`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c3(srs, self.facts, repo_root=self.dir)
        self.assertTrue(any("CacheBadge.jsx" in e for e in errors))

    def test_c3_duong_dan_hop_le_dat(self):
        f = self.dir / "src" / "test.cs"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("class Test {}")

        srs = check_srs.SRS(
            lines=[
                (1, "Mã nguồn tại `src/test.cs` và `test.cs`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c3(srs, self.facts, repo_root=self.dir)
        self.assertEqual(len(errors), 0)

    def test_c4_cookie_lech_ten_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "Hệ thống dùng cookie `news_session`"),
                (2, "Mermaid: Cookie: news_session"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c4(srs, self.facts)
        self.assertTrue(any("news_session" in e for e in errors))

    def test_c4_vung_lich_su_phien_ban_duoc_bo_qua(self):
        srs = check_srs.SRS(
            lines=[
                (1, "## Lịch sử phiên bản"),
                (2, "v2.0 cũ từng ghi nhầm cookie `news_session`"),
                (3, "## 1. Giới thiệu"),
                (4, "Cookie phiên là `SessionId` kèm `X-Session-Id` và `X-Cache`"),
            ],
            ignore_ranges=[(1, 2)],
        )
        errors = check_srs.check_c4(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c5_keyspace_lech_pattern_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "| Key pattern | TTL |"),
                (2, "|---|---|"),
                (3, "| `session:{id}` | 10 phút |"),  # sai ttl
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c5(srs, self.facts)
        self.assertTrue(len(errors) > 0)

    def test_c5_keyspace_chuan_dat(self):
        lines = [
            (1, "| Key pattern | Kiểu | TTL |"),
            (2, "|---|---|---|"),
            (3, "| `session:{sessionId}` | Hash | 30 phút |"),
            (4, "| `post:{postId}` | String | 10 phút |"),
            (5, "| `post:{postId}:views` | String | Không TTL |"),
            (6, "| `posts:cat:{categoryId}:p{n}:v{ver}` | String | 3 phút |"),
            (7, "| `posts:ver` | String | Không TTL |"),
            (8, "| `lock:post:{postId}` | String | 5 giây |"),
            (9, "| `posts:dirty_views` | Set | Không TTL |"),
        ]
        srs = check_srs.SRS(lines=lines, ignore_ranges=[])
        errors = check_srs.check_c5(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c6_stats_json_lech_field_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "##### FR-19: Thống kê hiệu năng"),
                (2, "```json"),
                (3, "{\n  \"totalLookups\": 10,\n  \"cacheHits\": 8\n}"),
                (4, "```"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c6(srs, self.facts)
        self.assertTrue(any("totalLookups" in e for e in errors))

    def test_c6_stats_json_dung_field_dat(self):
        srs = check_srs.SRS(
            lines=[
                (1, "##### FR-19: Thống kê hiệu năng"),
                (2, "```json"),
                (3, "{\n  \"hits\": 10,\n  \"misses\": 2,\n  \"totalRequests\": 12,\n  \"hitRate\": 0.8333\n}"),
                (4, "```"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c6(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c7_port_la_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "RedisInsight mở tại `http://localhost:8001` và map `8001:5540`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c7(srs, self.facts)
        self.assertTrue(any("8001" in e for e in errors))

    def test_c7_port_chuan_dat(self):
        srs = check_srs.SRS(
            lines=[
                (1, "RedisInsight cổng `5540:5540` tại `http://localhost:5540`"),
                (2, "Mongo `27017:27017`, Redis `6379:6379`, Frontend `3000`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c7(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c8_version_lech_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "Dự án sử dụng React 18, Vite 5, Tailwind 3 và `redis:7.0-alpine`"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c8(srs, self.facts)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("React" in e or "Vite" in e or "redis" in e for e in errors))

    def test_c8_version_dung_dat(self):
        srs = check_srs.SRS(
            lines=[
                (1, "Dự án dùng React 19, Vite 8, Tailwind 4, MongoDB.Driver v3, StackExchange.Redis v3, `redis:7-alpine`, `mongo:7.0`, net8.0 và net10.0"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c8(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c9_so_do_lech_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "| Chỉ số | Không cache | Cache MISS | Cache HIT |"),
                (2, "|---|---|---|---|"),
                (3, "| Mean | 3,66 | 99,99 | 2,96 |"),  # 99.99 sai
                (4, "Chạy 4 đợt stampede"),  # 4 đợt sai
                (5, "Tốc độ đạt 999.9 req/s"),  # 999.9 rps sai
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c9(srs, self.facts)
        self.assertTrue(len(errors) > 0)

    def test_c9_so_do_dung_dat(self):
        srs = check_srs.SRS(
            lines=[
                (1, "| Chỉ số | Không cache | Cache MISS | Cache HIT |"),
                (2, "|---|---|---|---|"),
                (3, "| Mean | 3,66 | 8,74 | 2,96 |"),
                (4, "| P50 | 3,59 | 8,57 | 2,92 |"),
                (5, "| P95 | 4,46 | 10,42 | 3,55 |"),
                (6, "| P99 | 4,63 | 10,90 | 3,82 |"),
                (7, "| Min | 2,88 | 7,31 | 2,31 |"),
                (8, "Kết quả qua 5 đợt stampede thử nghiệm."),
                (9, "Đạt 885,6 req/s tại 50 kết nối đồng thời và cam kết ≥ 800 req/s."),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c9(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c10_thieu_ticket_jira_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "| SCRUM-13 | Đăng nhập | Quân | Done | `test.cs` | FR-01 |"),
                (2, "Đạt 49/49 Jira tasks hoàn thành"),  # 49/49 sai
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c10(srs, self.facts)
        self.assertTrue(len(errors) > 0)
        self.assertTrue(any("49/49" in e or "SCRUM" in e for e in errors))

    def test_c10_jira_du_37_ticket_dat(self):
        lines = []
        for i, (k, st) in enumerate(self.facts["jira_tasks"].items()):
            lines.append((i + 1, f"| {k} | Tác vụ {k} | SV | {st} | `evidence.cs` | FR-01 |"))
        lines.append((len(lines) + 1, "Tổng cộng có 26/37 ticket đã Done"))
        srs = check_srs.SRS(lines=lines, ignore_ranges=[])
        errors = check_srs.check_c10(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c11_trich_dan_khong_co_trong_docx_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, '| DB-01 | "Câu trích bịa đặt không có trong docx" |'),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c11(srs, self.facts)
        self.assertTrue(any("DB-01" in e for e in errors))

    def test_c11_trich_dan_docx_dung_dat(self):
        srs = check_srs.SRS(
            lines=[
                (1, '| DB-01 | "Trang tin tức trực tuyến có phân hệ đăng nhập, đọc bài viết; hệ thống tích hợp bộ nhớ đệm để tăng tốc độ tải trang." |'),
                (2, '| DB-02 | "Hệ quản trị CSDL chính: Redis (Phối hợp MongoDB / MySQL làm DB gốc)" |'),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c11(srs, self.facts)
        self.assertEqual(len(errors), 0)

    def test_c11_paraph_chua_phu_bao_loi(self):
        facts = dict(self.facts)
        facts["docx_paragraphs"] = [
            "1. Tiêu đề",
            "Đoạn văn nội dung không có câu trích nào khớp và không được miễn.",
        ]
        srs = check_srs.SRS(
            lines=[
                (1, '| DB-01 | "Trang tin tức trực tuyến có phân hệ đăng nhập, đọc bài viết; hệ thống tích hợp bộ nhớ đệm để tăng tốc độ tải trang." |'),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c11(srs, facts)
        self.assertTrue(any("chưa được câu trích DB nào phủ" in e for e in errors))

    def test_c12_tc_tro_toi_method_khong_ton_tai_bao_loi(self):
        srs = check_srs.SRS(
            lines=[
                (1, "##### FR-01: Đăng ký"),
                (2, "| Thuộc tính | Giá trị |"),
                (3, "| Nguồn | DB-01 |"),
                (4, "| Ưu tiên | BẮT BUỘC |"),
                (5, "| Phụ trách | SV1 |"),
                (6, "| Kiểm chứng | T |"),
                (7, "| Test case | TC-99 |"),
                (8, "**Mô tả** Hệ thống PHẢI có..."),
                (9, "**Tiêu chí chấp nhận**"),
                (10, "- Cho người dùng. Khi đăng ký. Thì thành công."),
                (11, "| TC-99 | T | `Integration/NonExistent.cs::TestMethod` | FR-01 |"),
            ],
            ignore_ranges=[],
        )
        errors = check_srs.check_c12(srs, self.facts, repo_root=self.dir)
        self.assertTrue(len(errors) > 0)

    def test_c12_khoi_yeu_cau_day_du_dat(self):
        test_file = self.dir / "AuthTests.cs"
        test_file.write_text("public void Register_Success() {}")

        lines = [
            (1, "##### FR-01: Đăng ký tài khoản"),
            (2, "| Thuộc tính | Giá trị |"),
            (3, "| Nguồn | DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, DB-08, DB-09, DB-10, DB-11, DB-12, DB-13, DB-14, DB-15, DB-16, DB-17, DB-18, DB-19 |"),
            (4, "| Ưu tiên | BẮT BUỘC |"),
            (5, "| Phụ trách | SV1 — Như |"),
            (6, "| Kiểm chứng | T |"),
            (7, "| Test case | TC-01 |"),
            (8, "**Mô tả** Hệ thống PHẢI có..."),
            (9, "**Tiêu chí chấp nhận**"),
            (10, "- Cho người dùng mới. Khi đăng ký. Thì nhận mã 201."),
            (11, "## Phụ lục E: Danh mục Test Case"),
            (12, "| TC-01 | T | `AuthTests.cs::Register_Success` | FR-01 |"),
        ]
        srs = check_srs.SRS(lines=lines, ignore_ranges=[])
        errors = check_srs.check_c12(srs, self.facts, repo_root=self.dir)
        self.assertEqual(len(errors), 0)


class TestCheckSrsRepoFacts(unittest.TestCase):
    """Verify that facts_from_code extracts true facts from this repository."""

    def test_facts_from_repo(self):
        facts = check_srs.facts_from_code(REPO_ROOT)

        # 1. Cookie & Headers
        self.assertEqual(facts["cookie_name"], "SessionId")
        self.assertEqual(facts["session_header"], "X-Session-Id")
        self.assertEqual(facts["cache_header"], "X-Cache")

        # 2. Endpoints: exactly 21
        self.assertEqual(len(facts["endpoints"]), 21)
        self.assertIn("post /api/images", facts["endpoints"])
        self.assertIn("get /api/auth/me", facts["endpoints"])
        self.assertIn("get /health", facts["endpoints"])
        self.assertIn("get /api/health", facts["endpoints"])
        self.assertIn("get /api/cache/stats", facts["endpoints"])

        # 3. Cache stats fields
        self.assertEqual(facts["stats_fields"], {"hits", "misses", "totalRequests", "hitRate"})

        # 4. Jira tasks: exactly 37
        self.assertEqual(len(facts["jira_tasks"]), 37)

        # 5. Docx paragraphs: exactly 26
        self.assertEqual(len(facts["docx_paragraphs"]), 26)

        # 6. Ports
        self.assertIn(27017, facts["ports"])
        self.assertIn(6379, facts["ports"])
        self.assertIn(5540, facts["ports"])

        # 7. Versions
        self.assertEqual(facts["versions"]["react"], "19")
        self.assertEqual(facts["versions"]["vite"], "8")
        self.assertEqual(facts["versions"]["tailwindcss"], "4")
        self.assertEqual(facts["versions"]["mongo_driver"], "3")
        self.assertEqual(facts["versions"]["stackexchange_redis"], "3")
        self.assertEqual(facts["versions"]["net_app"], "net8.0")
        self.assertEqual(facts["versions"]["net_test"], "net10.0")


if __name__ == "__main__":
    unittest.main()
