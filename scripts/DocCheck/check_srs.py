#!/usr/bin/env python3
"""
Bộ kiểm tra tài liệu đặc tả SRS (check_srs.py).
Đọc sự thật từ mã nguồn, cấu hình, số đo, CSV, docx rồi kiểm chứng với docs/SRS.md.

Chủ sở hữu: SV2 — Nguyễn Anh Quân
Sử dụng:
    python3 scripts/DocCheck/check_srs.py [--srs docs/SRS.md] [--repo <gốc repo>] [--only C1,C4]
"""

import argparse
import csv
import glob
import html
import json
import os
import pathlib
import re
import sys
import zipfile
from dataclasses import dataclass, field


@dataclass
class SRS:
    lines: list[tuple[int, str]]
    ignore_ranges: list[tuple[int, int]] = field(default_factory=list)

    def is_ignored(self, line_num: int) -> bool:
        for start, end in self.ignore_ranges:
            if start <= line_num <= end:
                return True
        return False


def load_srs(path: pathlib.Path) -> SRS:
    text = path.read_text(encoding="utf-8")
    raw_lines = text.splitlines()
    lines = [(i + 1, line) for i, line in enumerate(raw_lines)]

    ignore_ranges = []
    in_ignore = False
    ignore_start = 0
    ignore_level = 0

    for i, line in lines:
        heading_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            if in_ignore:
                if level <= ignore_level:
                    ignore_ranges.append((ignore_start, i - 1))
                    in_ignore = False

            if not in_ignore:
                if "lịch sử phiên bản" in title.lower() or "phụ lục f" in title.lower():
                    in_ignore = True
                    ignore_start = i
                    ignore_level = level

    if in_ignore:
        ignore_ranges.append((ignore_start, len(lines)))

    return SRS(lines=lines, ignore_ranges=ignore_ranges)


def facts_from_code(repo_root: pathlib.Path) -> dict:
    facts = {}

    # 1. Endpoints
    endpoints = set()
    prog_file = repo_root / "src/NewsCacheSession.Api/Program.cs"
    if prog_file.exists():
        prog_text = prog_file.read_text(encoding="utf-8")
        for m in re.finditer(r'MapHealthChecks\(\s*"([^"]+)"', prog_text):
            p = m.group(1).strip("/")
            endpoints.add(f"get /{p.lower()}")

    controllers_dir = repo_root / "src/NewsCacheSession.Api/Controllers"
    if controllers_dir.exists():
        for cfile in controllers_dir.glob("*Controller.cs"):
            text = cfile.read_text(encoding="utf-8")
            cname = cfile.stem
            if cname.endswith("Controller"):
                cname = cname[:-len("Controller")]
            class_route_m = re.search(r'\[Route\("([^"]+)"\)\]', text)
            base_route = class_route_m.group(1) if class_route_m else ""
            base_route = base_route.replace("[controller]", cname.lower())

            method_matches = re.finditer(r'\[Http(Get|Post|Put|Delete|Patch)(?:\("([^"]*)"\))?\]', text)
            for m in method_matches:
                verb = m.group(1).lower()
                sub = m.group(2) or ""
                if sub.startswith("~/") or sub.startswith("/"):
                    route = sub.lstrip("~/")
                else:
                    route = f"{base_route}/{sub}".strip("/")
                route = "/" + re.sub(r'\{[^}]+\}', '{}', route).strip("/")
                route = re.sub(r'/+', '/', route)
                endpoints.add(f"{verb} {route.lower()}")

    facts["endpoints"] = endpoints

    # 2. Cookie & Headers
    facts["cookie_name"] = "SessionId"
    facts["session_header"] = "X-Session-Id"
    facts["cache_header"] = "X-Cache"

    cus_file = repo_root / "src/NewsCacheSession.Api/Services/CurrentUserService.cs"
    if cus_file.exists():
        cus_text = cus_file.read_text(encoding="utf-8")
        cm = re.search(r'SessionCookieName\s*=\s*"([^"]+)"', cus_text)
        if cm:
            facts["cookie_name"] = cm.group(1)
        hm = re.search(r'SessionHeaderName\s*=\s*"([^"]+)"', cus_text)
        if hm:
            facts["session_header"] = hm.group(1)

    # 3. Stats fields
    stats_fields = {"hits", "misses", "totalRequests", "hitRate"}
    cache_svc = repo_root / "src/NewsCacheSession.Api/Services/ICacheService.cs"
    if cache_svc.exists():
        cs_text = cache_svc.read_text(encoding="utf-8")
        m = re.search(r'record\s+CacheStats\s*\(([^)]+)\)', cs_text)
        if m:
            raw_params = m.group(1).split(",")
            fields = set()
            for p in raw_params:
                p = p.strip()
                if p:
                    parts = p.split()
                    fname = parts[-1]
                    fields.add(fname[:1].lower() + fname[1:])
            if fields:
                stats_fields = fields
    facts["stats_fields"] = stats_fields

    # 4. Ports
    ports = {27017, 6379, 5540, 5134, 58320, 7295, 3000, 27019, 6380, 5135}
    compose_ports = {"27017:27017", "6379:6379", "5540:5540"}
    facts["ports"] = ports
    facts["compose_ports"] = compose_ports

    # 5. Versions
    versions = {
        "react": "19",
        "vite": "8",
        "tailwindcss": "4",
        "mongo_driver": "3",
        "stackexchange_redis": "3",
        "mongo_image": "mongo:7.0",
        "redis_image": "redis:7-alpine",
        "net_app": "net8.0",
        "net_test": "net10.0",
    }
    pkg_file = repo_root / "src/frontend/package.json"
    if pkg_file.exists():
        try:
            pkg = json.loads(pkg_file.read_text(encoding="utf-8"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "react" in deps:
                versions["react"] = re.search(r'\d+', deps["react"]).group(0)
            if "vite" in deps:
                versions["vite"] = re.search(r'\d+', deps["vite"]).group(0)
            if "tailwindcss" in deps:
                versions["tailwindcss"] = re.search(r'\d+', deps["tailwindcss"]).group(0)
        except Exception:
            pass

    api_csproj = repo_root / "src/NewsCacheSession.Api/NewsCacheSession.Api.csproj"
    if api_csproj.exists():
        api_text = api_csproj.read_text(encoding="utf-8")
        m_mongo = re.search(r'PackageReference\s+Include="MongoDB\.Driver"\s+Version="(\d+)', api_text)
        if m_mongo:
            versions["mongo_driver"] = m_mongo.group(1)
        m_redis = re.search(r'PackageReference\s+Include="StackExchange\.Redis"\s+Version="(\d+)', api_text)
        if m_redis:
            versions["stackexchange_redis"] = m_redis.group(1)
        m_tf = re.search(r'<TargetFramework>([^<]+)</TargetFramework>', api_text)
        if m_tf:
            versions["net_app"] = m_tf.group(1)

    test_csproj = repo_root / "tests/NewsCacheSession.Tests/NewsCacheSession.Tests.csproj"
    if test_csproj.exists():
        test_text = test_csproj.read_text(encoding="utf-8")
        m_tf = re.search(r'<TargetFramework>([^<]+)</TargetFramework>', test_text)
        if m_tf:
            versions["net_test"] = m_tf.group(1)

    facts["versions"] = versions

    # 6. Summary json
    summary_file = repo_root / "scripts/Benchmark/results/2026-10-25-chinh-thuc/summary.json"
    summary_data = {}
    if summary_file.exists():
        try:
            summary_raw = json.loads(summary_file.read_text(encoding="utf-8"))
            summary_data["latency"] = summary_raw.get("latency", {})
            summary_data["stampede"] = summary_raw.get("stampede", [])
            rps_set = set()
            for l in summary_raw.get("load", []):
                if "rps" in l:
                    rps_set.add(round(float(l["rps"]), 1))
            summary_data["rps"] = rps_set
        except Exception:
            pass
    facts["summary"] = summary_data

    # 7. Jira tasks
    jira_file = repo_root / "docs/nosql-jira-tasks.csv"
    jira_tasks = {}
    if jira_file.exists():
        with open(jira_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                k = row.get("Key")
                st = row.get("Status")
                if k:
                    jira_tasks[k] = st
    facts["jira_tasks"] = jira_tasks

    # 8. Docx paragraphs
    docx_file = repo_root / "docs/ĐỀ TÀI 06.docx"
    docx_paragraphs = []
    if docx_file.exists():
        try:
            x = zipfile.ZipFile(docx_file).read("word/document.xml").decode("utf-8")
            paras = [" ".join(html.unescape("".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S))).split())
                     for p in re.findall(r"<w:p[ >].*?</w:p>", x, re.S)]
            docx_paragraphs = [p for p in paras if p]
        except Exception:
            pass
    facts["docx_paragraphs"] = docx_paragraphs

    # 9. Keyspace patterns
    facts["keyspace"] = [
        {"key": "session:{sessionId}", "ttl": "30 phút"},
        {"key": "post:{postId}", "ttl": "10 phút"},
        {"key": "post:{postId}:views", "ttl": "Không TTL"},
        {"key": "posts:cat:{categoryId}:p{n}:v{ver}", "ttl": "3 phút"},
        {"key": "posts:ver", "ttl": "Không TTL"},
        {"key": "lock:post:{postId}", "ttl": "5 giây"},
        {"key": "posts:dirty_views", "ttl": "Không TTL"},
    ]

    return facts


# --- 12 Phép kiểm ---

def check_c1(srs: SRS, facts: dict) -> list[str]:
    """Mọi cặp METHOD /đường-dẫn trong SRS có trong tập endpoint của code."""
    errors = []
    known_endpoints = facts["endpoints"]
    endpoint_re = re.compile(r'\b(GET|POST|PUT|DELETE|PATCH)\s+([/][a-zA-Z0-9_\-\./\{\}]+)', re.IGNORECASE)

    for i, line in srs.lines:
        if srs.is_ignored(i):
            continue
        # find backtick blocks or matches
        for m in endpoint_re.finditer(line):
            verb = m.group(1).lower()
            raw_path = m.group(2).lower()
            norm_path = "/" + re.sub(r'\{[^}]+\}', '{}', raw_path).strip("/")
            norm_path = re.sub(r'/+', '/', norm_path)
            candidate = f"{verb} {norm_path}"
            if candidate not in known_endpoints:
                errors.append(f"[C1] docs/SRS.md:{i} Endpoint không hợp lệ: `{m.group(1)} {m.group(2)}`")

    return errors


def check_c2(srs: SRS, facts: dict) -> list[str]:
    """Mọi endpoint của code xuất hiện trong SRS dưới dạng METHOD /đường-dẫn."""
    errors = []
    known_endpoints = set(facts["endpoints"])
    found_endpoints = set()

    endpoint_re = re.compile(r'\b(GET|POST|PUT|DELETE|PATCH)\s+([/][a-zA-Z0-9_\-\./\{\}]+)', re.IGNORECASE)

    for i, line in srs.lines:
        for m in endpoint_re.finditer(line):
            verb = m.group(1).lower()
            raw_path = m.group(2).lower()
            norm_path = "/" + re.sub(r'\{[^}]+\}', '{}', raw_path).strip("/")
            norm_path = re.sub(r'/+', '/', norm_path)
            found_endpoints.add(f"{verb} {norm_path}")

    missing = known_endpoints - found_endpoints
    for ep in sorted(missing):
        parts = ep.split(maxsplit=1)
        formatted = f"{parts[0].upper()} {parts[1]}" if len(parts) == 2 else ep.upper()
        errors.append(f"[C2] docs/SRS.md:0 Thiếu endpoint từ code: `{formatted}`")

    return errors


def check_c3(srs: SRS, facts: dict, repo_root: pathlib.Path) -> list[str]:
    """Mọi token trong backtick trông như đường dẫn repo phải tồn tại."""
    errors = []
    path_exts = {".cs", ".jsx", ".js", ".py", ".md", ".json", ".yml", ".yaml", ".csv", ".docx", ".ps1", ".png"}

    # Build repo file set (excluding node_modules, bin, obj, .git, dist)
    repo_files = set()
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in {"node_modules", "bin", "obj", ".git", "dist", ".gemini"}]
        for f in files:
            rel = pathlib.Path(root, f).relative_to(repo_root).as_posix()
            repo_files.add(rel)

    backtick_re = re.compile(r'`([^`\n]+)`')

    for i, line in srs.lines:
        if srs.is_ignored(i):
            continue
        for m in backtick_re.finditer(line):
            token = m.group(1).strip()
            # Bỏ qua token bắt đầu bằng / hoặc http, chứa { hay : (trừ ::Method)
            if token.startswith("/") or token.startswith("http://") or token.startswith("https://"):
                continue
            if "{" in token or "}" in token:
                continue
            if ":" in token and "::" not in token:
                continue
            # Bỏ qua endpoint HTTP
            if re.match(r'^(GET|POST|PUT|DELETE|PATCH)\s+/', token, re.IGNORECASE):
                continue
            # Bỏ qua câu lệnh command line hoặc biểu thức có dấu =
            if token.startswith("python3 ") or "=" in token:
                continue

            clean_token = token.split("::")[0].strip()
            clean_token = clean_token.replace("\\", "/")

            is_path = False
            if any(clean_token.endswith(ext) for ext in path_exts):
                is_path = True
            elif "/" in clean_token and not re.search(r'\s', clean_token):
                # Token chứa / không có khoảng trắng, kiểm tra xem có giống đường dẫn hay từ ghép như MULTI/EXEC
                if any(ext in clean_token for ext in path_exts) or (repo_root / clean_token).exists():
                    is_path = True
                elif clean_token.isupper() or clean_token in {"Fetch/XHR"}:
                    is_path = False
                else:
                    is_path = True

            if not is_path:
                continue

            # Token chứa *
            if "*" in clean_token:
                parent = pathlib.Path(clean_token).parent.as_posix()
                if (repo_root / parent).exists():
                    continue
                errors.append(f"[C3] docs/SRS.md:{i} Thư mục cha không tồn tại: `{token}`")
                continue

            # Exact match from repo root
            if clean_token in repo_files or (repo_root / clean_token).exists():
                continue

            # Suffix match
            matched = any(rf.endswith(clean_token) for rf in repo_files)
            if not matched:
                errors.append(f"[C3] docs/SRS.md:{i} Đường dẫn không tồn tại: `{token}`")

    return errors


def check_c4(srs: SRS, facts: dict) -> list[str]:
    """Kiểm tra tên cookie và nhắc X-Session-Id, X-Cache."""
    errors = []
    expected_cookie = facts.get("cookie_name", "SessionId")

    cookie_re = re.compile(r'(?:cookie\s+`([^`]+)`|Cookie\s+tên\s+`([^`]+)`|Cookie:\s*([^\s,;|]+))', re.IGNORECASE)

    has_session_header = False
    has_cache_header = False

    for i, line in srs.lines:
        if "X-Session-Id" in line:
            has_session_header = True
        if "X-Cache" in line:
            has_cache_header = True

        if srs.is_ignored(i):
            continue

        for m in cookie_re.finditer(line):
            cname = m.group(1) or m.group(2) or m.group(3)
            cname = cname.strip("`").strip()
            if cname and cname != expected_cookie:
                errors.append(f"[C4] docs/SRS.md:{i} Tên cookie sai: `{cname}` (mong đợi `{expected_cookie}`)")

    if not has_session_header:
        errors.append("[C4] docs/SRS.md:0 Thiếu nhắc tới header `X-Session-Id`")
    if not has_cache_header:
        errors.append("[C4] docs/SRS.md:0 Thiếu nhắc tới header `X-Cache`")

    return errors


def check_c5(srs: SRS, facts: dict) -> list[str]:
    """Kiểm tra bảng keyspace Redis."""
    errors = []
    expected_keys = facts.get("keyspace", [])
    norm_pattern = lambda s: re.sub(r'\{[a-zA-Z0-9_\-]+\}', '{}', s).strip().lower()

    found_patterns = {}
    in_table = False

    for i, line in srs.lines:
        # Detect keyspace table
        if "|" in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 2 and any("key" in c.lower() for c in cells) and any("ttl" in c.lower() for c in cells):
                in_table = True
                continue
            if in_table:
                if not line.strip() or line.startswith("#"):
                    in_table = False
                    continue
                if set(line.replace("|", "").strip()) <= {"-", " "}:
                    continue
                if len(cells) >= 2:
                    k_cell = cells[0].replace("`", "").strip()
                    ttl_cell = cells[1].strip() if len(cells) == 2 else cells[2].strip()
                    if k_cell:
                        found_patterns[norm_pattern(k_cell)] = (i, ttl_cell)
        else:
            in_table = False

    for exp in expected_keys:
        exp_norm = norm_pattern(exp["key"])
        if exp_norm not in found_patterns:
            errors.append(f"[C5] docs/SRS.md:0 Thiếu key pattern trong bảng keyspace: `{exp['key']}`")
        else:
            line_no, ttl_val = found_patterns[exp_norm]
            # Check TTL
            exp_ttl_lower = exp["ttl"].lower()
            if "không" in exp_ttl_lower and "không" not in ttl_val.lower():
                errors.append(f"[C5] docs/SRS.md:{line_no} Key `{exp['key']}` phải có TTL là Không TTL, thực tế: `{ttl_val}`")
            elif "không" not in exp_ttl_lower:
                # check number
                m_exp = re.search(r'\d+', exp["ttl"])
                m_act = re.search(r'\d+', ttl_val)
                if m_exp and m_act and m_exp.group(0) != m_act.group(0):
                    errors.append(f"[C5] docs/SRS.md:{line_no} Key `{exp['key']}` TTL không khớp: mong đợi `{exp['ttl']}`, thực tế: `{ttl_val}`")

    return errors


def check_c6(srs: SRS, facts: dict) -> list[str]:
    """Kiểm tra khối json trong FR-19 có tập key bằng CacheStats."""
    errors = []
    expected_fields = facts.get("stats_fields", {"hits", "misses", "totalRequests", "hitRate"})

    in_fr19 = False
    in_json = False
    json_lines = []
    json_start = 0

    for i, line in srs.lines:
        if re.search(r'#####\s+FR-19\b', line):
            in_fr19 = True
            continue
        if in_fr19 and re.match(r'^(#{1,5})\s+', line) and not line.startswith("##### FR-19"):
            break

        if in_fr19:
            if "```json" in line:
                in_json = True
                json_start = i
                json_lines = []
                continue
            elif in_json and "```" in line:
                in_json = False
                break
            elif in_json:
                json_lines.append(line)

    if not json_lines:
        errors.append("[C6] docs/SRS.md:0 Không tìm thấy khối ```json trong FR-19")
        return errors

    raw_json = "\n".join(json_lines)
    try:
        data = json.loads(raw_json)
        found_keys = set(data.keys())
        if found_keys != expected_fields:
            errors.append(f"[C6] docs/SRS.md:{json_start} Field stats sai: có {sorted(found_keys)}, mong đợi {sorted(expected_fields)}")
    except Exception as e:
        errors.append(f"[C6] docs/SRS.md:{json_start} JSON trong FR-19 lỗi cú pháp: {e}")

    return errors


def check_c7(srs: SRS, facts: dict) -> list[str]:
    """Kiểm tra cổng localhost:NNNN và port mapping `NNNN:NNNN`."""
    errors = []
    allowed_ports = facts.get("ports", set())
    allowed_mappings = facts.get("compose_ports", set())

    port_map_re = re.compile(r'`(\d{4,5}):(\d{4,5})`')
    localhost_re = re.compile(r'localhost:(\d{4,5})')

    for i, line in srs.lines:
        if srs.is_ignored(i):
            continue

        for m in port_map_re.finditer(line):
            mapping = f"{m.group(1)}:{m.group(2)}"
            # allow standard QA mappings as well
            if mapping not in allowed_mappings and mapping not in {"27019:27017", "6380:6379"}:
                errors.append(f"[C7] docs/SRS.md:{i} Ánh xạ cổng không hợp lệ: `{mapping}`")

        for m in localhost_re.finditer(line):
            p = int(m.group(1))
            if p not in allowed_ports:
                errors.append(f"[C7] docs/SRS.md:{i} Cổng localhost không hợp lệ: `localhost:{p}`")

    return errors


def check_c8(srs: SRS, facts: dict) -> list[str]:
    """Kiểm tra phiên bản công nghệ khớp thực tế."""
    errors = []
    v = facts.get("versions", {})

    for i, line in srs.lines:
        if srs.is_ignored(i):
            continue

        # React N
        for m in re.finditer(r'\bReact\s+(\d+)\b', line, re.IGNORECASE):
            if m.group(1) != v.get("react"):
                errors.append(f"[C8] docs/SRS.md:{i} Phiên bản React sai: `{m.group(0)}` (thật là React {v.get('react')})")

        # Vite N
        for m in re.finditer(r'\bVite\s+(\d+)\b', line, re.IGNORECASE):
            if m.group(1) != v.get("vite"):
                errors.append(f"[C8] docs/SRS.md:{i} Phiên bản Vite sai: `{m.group(0)}` (thật là Vite {v.get('vite')})")

        # Tailwind N
        for m in re.finditer(r'\bTailwind(?:CSS)?\s+(\d+)\b', line, re.IGNORECASE):
            if m.group(1) != v.get("tailwindcss"):
                errors.append(f"[C8] docs/SRS.md:{i} Phiên bản Tailwind sai: `{m.group(0)}` (thật là Tailwind {v.get('tailwindcss')})")

        # MongoDB.Driver vN
        for m in re.finditer(r'\bMongoDB\.Driver\s+v?(\d+)', line, re.IGNORECASE):
            if m.group(1) != v.get("mongo_driver"):
                errors.append(f"[C8] docs/SRS.md:{i} Phiên bản MongoDB.Driver sai: `{m.group(0)}` (thật là v{v.get('mongo_driver')})")

        # StackExchange.Redis vN
        for m in re.finditer(r'\bStackExchange\.Redis\s+v?(\d+)', line, re.IGNORECASE):
            if m.group(1) != v.get("stackexchange_redis"):
                errors.append(f"[C8] docs/SRS.md:{i} Phiên bản StackExchange.Redis sai: `{m.group(0)}` (thật là v{v.get('stackexchange_redis')})")

        # redis image: redis:7-alpine
        for m in re.finditer(r'`redis:([0-9\.\-]+(?:alpine)?)`', line):
            img = f"redis:{m.group(1)}"
            if img != v.get("redis_image") and img != "redis:7-alpine":
                errors.append(f"[C8] docs/SRS.md:{i} Image Redis sai: `{img}` (thật là `{v.get('redis_image')}`)")

    return errors


def check_c9(srs: SRS, facts: dict) -> list[str]:
    """Kiểm tra số đo latency, số đợt stampede và rps."""
    errors = []
    summary = facts.get("summary", {})
    latency_data = summary.get("latency", {})

    # Check latency table
    # | Chỉ số | Không cache | Cache MISS | Cache HIT |
    in_latency_table = False
    checked_rows = 0

    def parse_num(s):
        s = s.replace(",", ".").strip()
        m = re.search(r'[\d\.]+', s)
        return float(m.group(0)) if m else None

    for i, line in srs.lines:
        if "|" in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) == 4 and "chỉ số" in cells[0].lower() and "không cache" in cells[1].lower():
                in_latency_table = True
                continue
            if in_latency_table:
                if not line.strip() or line.startswith("#") or set(line.replace("|", "").strip()) <= {"-", " "}:
                    if not line.strip() or line.startswith("#"):
                        in_latency_table = False
                    continue
                if len(cells) == 4:
                    metric = cells[0].lower()
                    key_map = {"mean": "mean", "p50": "median", "median": "median", "p95": "p95", "p99": "p99", "min": "min"}
                    field_key = key_map.get(metric)
                    if field_key:
                        checked_rows += 1
                        val_no_cache = parse_num(cells[1])
                        val_miss = parse_num(cells[2])
                        val_hit = parse_num(cells[3])

                        exp_no_cache = latency_data.get("khong-cache", {}).get(field_key)
                        exp_miss = latency_data.get("cache-miss", {}).get(field_key)
                        exp_hit = latency_data.get("cache-hit", {}).get(field_key)

                        if exp_no_cache and val_no_cache is not None and abs(val_no_cache - exp_no_cache) > 0.05:
                            errors.append(f"[C9] docs/SRS.md:{i} Sai số đo {metric} Không cache: {val_no_cache} (gốc {exp_no_cache:.2f})")
                        if exp_miss and val_miss is not None and abs(val_miss - exp_miss) > 0.05:
                            errors.append(f"[C9] docs/SRS.md:{i} Sai số đo {metric} Cache MISS: {val_miss} (gốc {exp_miss:.2f})")
                        if exp_hit and val_hit is not None and abs(val_hit - exp_hit) > 0.05:
                            errors.append(f"[C9] docs/SRS.md:{i} Sai số đo {metric} Cache HIT: {val_hit} (gốc {exp_hit:.2f})")
        else:
            in_latency_table = False

    # Check stampede rounds: must be 5
    exp_stampede_count = len(summary.get("stampede", [])) or 5
    for i, line in srs.lines:
        if "stampede" in line.lower():
            m_dot = re.search(r'(\d+)\s+đợt', line, re.IGNORECASE)
            if m_dot:
                dot_count = int(m_dot.group(1))
                if dot_count != exp_stampede_count:
                    errors.append(f"[C9] docs/SRS.md:{i} Số đợt stampede sai: {dot_count} đợt (thực tế {exp_stampede_count} đợt)")

        # Check standalone rps / req/s numbers
        # mọi số đi với req/s hoặc RPS thuộc tập load[].rps, trừ số đứng sau ≥/ >=
        for m in re.finditer(r'(?:(?<![≥>=])\s|^)(\d+(?:[,\.]\d+)?)\s*(?:req/s|rps)\b', line, re.IGNORECASE):
            full_match = m.group(0)
            if "≥" in full_match or ">=" in full_match:
                continue
            val_rps = round(float(m.group(1).replace(",", ".")), 1)
            valid_rps = summary.get("rps", set())
            if valid_rps and val_rps not in valid_rps:
                # kiểm tra xem phía trước trong line có >= hoặc ≥ không
                start_idx = m.start()
                prefix = line[max(0, start_idx - 10):start_idx]
                if "≥" in prefix or ">=" in prefix:
                    continue
                errors.append(f"[C9] docs/SRS.md:{i} Số đo RPS không khớp load: {val_rps} req/s")

    return errors


def check_c10(srs: SRS, facts: dict) -> list[str]:
    """Đủ 37 dòng | SCRUM-NN |, đúng trạng thái CSV; mọi N/M Jira có M = 37."""
    errors = []
    jira_tasks = facts.get("jira_tasks", {})

    found_keys = {}
    for i, line in srs.lines:
        # Check N/M Jira/ticket/task
        for m in re.finditer(r'(\d+)\s*/\s*(\d+)\s*(?:Jira|ticket|task)', line, re.IGNORECASE):
            total_m = int(m.group(2))
            if total_m != len(jira_tasks) and len(jira_tasks) > 0:
                errors.append(f"[C9] docs/SRS.md:{i} Số lượng Jira tasks sai: {m.group(0)} (tổng số ticket thật là {len(jira_tasks)})")

        m_scrum = re.search(r'\|\s*(SCRUM-\d+)\s*\|', line)
        if m_scrum:
            s_key = m_scrum.group(1)
            cells = [c.strip() for c in line.split("|")[1:-1]]
            found_keys[s_key] = (i, cells)

    for k, expected_status in jira_tasks.items():
        if k not in found_keys:
            errors.append(f"[C10] docs/SRS.md:0 Thiếu ticket Jira trong bảng ma trận: `{k}`")
        else:
            line_no, cells = found_keys[k]
            # Verify status in cells
            if not any(expected_status.lower() in c.lower() for c in cells):
                errors.append(f"[C10] docs/SRS.md:{line_no} Ticket `{k}` sai trạng thái CSV: mong đợi `{expected_status}`")

    return errors


def check_c11(srs: SRS, facts: dict) -> list[str]:
    """Mọi dòng | DB-NN | "..." | có câu trích trong text docx; mọi đoạn docx (trừ tiêu đề & miễn) có DB trích."""
    errors = []
    docx_paras = facts.get("docx_paragraphs", [])
    norm = lambda s: re.sub(r"\s+", " ", s.replace("–", "-")).strip().lower()

    full_docx_text = " ".join(docx_paras)
    norm_docx = norm(full_docx_text)

    db_quotes = {}
    db_re = re.compile(r'^\|\s*(DB-\d{2})\s*\|\s*"([^"]+)"\s*\|', re.MULTILINE)

    for i, line in srs.lines:
        m = db_re.search(line)
        if m:
            db_id = m.group(1)
            quote = m.group(2)
            db_quotes[db_id] = quote
            if norm(quote) not in norm_docx:
                errors.append(f"[C11] docs/SRS.md:{i} Trích dẫn {db_id} không có trong đề bài docx: \"{quote[:60]}...\"")

    if not db_quotes:
        errors.append("[C11] docs/SRS.md:0 Không tìm thấy bảng trích dẫn yêu cầu nguồn DB-01...DB-19")
        return errors

    # Check coverage of docx paragraphs
    exempt = [
        "số lượng thành viên: 03 sinh viên",
        "1.0đ (dummy data): bộ dữ liệu mẫu đạt chuẩn định mức bên dưới."
    ]

    for idx, p in enumerate(docx_paras):
        p_norm = norm(p)
        is_title = (idx == 0) or p.isupper() or p.strip().endswith(":")
        is_exempt = any(ex in p_norm for ex in exempt)
        if is_title or is_exempt:
            continue
        # Check if matched by at least one quote
        matched = any(norm(q) in p_norm for q in db_quotes.values())
        if not matched:
            errors.append(f"[C11] docs/SRS.md:0 Đoạn văn docx #{idx+1} chưa được câu trích DB nào phủ: \"{p[:60]}...\"")

    return errors


def check_c12(srs: SRS, facts: dict, repo_root: pathlib.Path) -> list[str]:
    """Kiểm tra cấu trúc từng khối yêu cầu FR/NFR/IR/DR và ma trận Test Case."""
    errors = []

    req_re = re.compile(r'^#####\s+((?:FR|NFR|IR|DR)-\d{2}):\s*(.*)')

    # Collect all requirements
    current_req = None
    req_blocks = {}
    current_lines = []

    for i, line in srs.lines:
        m = req_re.match(line)
        if m:
            if current_req:
                req_blocks[current_req] = current_lines
            current_req = m.group(1)
            current_lines = [(i, line)]
        elif current_req:
            if line.startswith("# ") or line.startswith("## ") or line.startswith("### ") or line.startswith("#### "):
                req_blocks[current_req] = current_lines
                current_req = None
                current_lines = []
            else:
                current_lines.append((i, line))

    if current_req:
        req_blocks[current_req] = current_lines

    referenced_dbs = set()
    referenced_tcs = set()

    for req_id, block in req_blocks.items():
        block_text = "\n".join(l[1] for l in block)
        first_line = block[0][0]

        # Properties table check
        prop_names = set()
        for _, l in block:
            if "|" in l:
                cells = [c.strip() for c in l.split("|")[1:-1]]
                if len(cells) >= 2:
                    pname = cells[0].lower()
                    pval = cells[1]
                    prop_names.add(pname)
                    if pname == "nguồn":
                        for db_m in re.finditer(r'DB-\d{2}', pval):
                            referenced_dbs.add(db_m.group(0))
                    elif pname == "ưu tiên":
                        if pval not in {"BẮT BUỘC", "NÊN", "CÓ THỂ"}:
                            errors.append(f"[C12] docs/SRS.md:{first_line} {req_id} có Mức ưu tiên không hợp lệ: `{pval}`")
                    elif pname == "kiểm chứng":
                        methods = {m.strip() for m in pval.split(",")}
                        if not methods.issubset({"T", "D", "I", "A"}):
                            errors.append(f"[C12] docs/SRS.md:{first_line} {req_id} có Phương pháp kiểm chứng không hợp lệ: `{pval}`")
                    elif pname == "test case":
                        for tc_m in re.finditer(r'TC-\d{2}', pval):
                            referenced_tcs.add(tc_m.group(0))

        required_props = {"nguồn", "ưu tiên", "phụ trách", "kiểm chứng", "test case"}
        missing_props = required_props - prop_names
        if missing_props:
            errors.append(f"[C12] docs/SRS.md:{first_line} {req_id} thiếu thuộc tính: {missing_props}")

        # Check Mô tả & Tiêu chí chấp nhận
        if "**Mô tả**" not in block_text and "**Mô tả:**" not in block_text:
            errors.append(f"[C12] docs/SRS.md:{first_line} {req_id} thiếu mục **Mô tả**")
        if "**Tiêu chí chấp nhận**" not in block_text and "**Tiêu chí chấp nhận:**" not in block_text:
            errors.append(f"[C12] docs/SRS.md:{first_line} {req_id} thiếu mục **Tiêu chí chấp nhận**")
        if "Thì" not in block_text:
            errors.append(f"[C12] docs/SRS.md:{first_line} {req_id} tiêu chí chấp nhận thiếu từ khóa 'Thì'")

    # Check that all 19 DB-xx are referenced
    for n in range(1, 20):
        db_id = f"DB-{n:02d}"
        if db_id not in referenced_dbs:
            errors.append(f"[C12] docs/SRS.md:0 Yêu cầu {db_id} chưa được khối yêu cầu nào trỏ tới")

    # Catalog of test cases: | TC-NN | <T|D|I|A> | <bằng chứng> | <yêu cầu> |
    tc_catalog = {}
    tc_re = re.compile(r'\|\s*(TC-\d{2})\s*\|\s*([TDIA])\s*\|\s*`?([^`\|]+)`?\s*\|\s*([^\|]+)\|')

    for i, line in srs.lines:
        m = tc_re.search(line)
        if m:
            tc_id = m.group(1)
            method = m.group(2)
            evidence = m.group(3).strip()
            reqs = m.group(4).strip()
            tc_catalog[tc_id] = (i, method, evidence, reqs)

    # Every referenced TC exists in catalog and vice-versa
    for tc in referenced_tcs:
        if tc not in tc_catalog:
            errors.append(f"[C12] docs/SRS.md:0 Test case `{tc}` được trỏ tới nhưng không có trong danh mục Phụ lục E")

    for tc, (line_no, method, evidence, _) in tc_catalog.items():
        if tc not in referenced_tcs:
            errors.append(f"[C12] docs/SRS.md:{line_no} Test case `{tc}` có trong danh mục nhưng không khối yêu cầu nào trỏ tới")

        # Verify evidence
        if method == "T":
            if "::" in evidence:
                fpath, mname = evidence.split("::", 1)
                fpath = fpath.strip()
                mname = mname.strip()
                # find file in tests or repo
                resolved_file = None
                candidates = [
                    repo_root / fpath,
                    repo_root / "tests/NewsCacheSession.Tests" / fpath,
                    repo_root / "src/NewsCacheSession.Api" / fpath,
                ]
                for c in candidates:
                    if c.exists():
                        resolved_file = c
                        break
                if not resolved_file:
                    # search suffix
                    for root, _, files in os.walk(repo_root):
                        for f in files:
                            rel = pathlib.Path(root, f).relative_to(repo_root).as_posix()
                            if rel.endswith(fpath):
                                resolved_file = repo_root / rel
                                break
                        if resolved_file:
                            break

                if not resolved_file:
                    errors.append(f"[C12] docs/SRS.md:{line_no} File test `{fpath}` của `{tc}` không tồn tại")
                else:
                    content = resolved_file.read_text(encoding="utf-8")
                    if resolved_file.suffix == ".cs":
                        if not re.search(r'\b' + re.escape(mname) + r'\s*\(', content):
                            errors.append(f"[C12] docs/SRS.md:{line_no} Method `{mname}` không có trong `{resolved_file.name}`")
                    else:
                        if mname not in content:
                            errors.append(f"[C12] docs/SRS.md:{line_no} Test `{mname}` không có trong `{resolved_file.name}`")
            else:
                # only file
                resolved = (repo_root / evidence).exists() or any(
                    pathlib.Path(root, f).relative_to(repo_root).as_posix().endswith(evidence)
                    for root, _, files in os.walk(repo_root)
                    for f in files
                )
                if not resolved:
                    errors.append(f"[C12] docs/SRS.md:{line_no} File bằng chứng `{evidence}` của `{tc}` không tồn tại")
        elif method == "D":
            if "phụ lục d" not in evidence.lower():
                errors.append(f"[C12] docs/SRS.md:{line_no} Test case Demo `{tc}` phải trỏ tới Phụ lục D, thực tế: `{evidence}`")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Kiểm tra tài liệu SRS với mã nguồn và dữ liệu thực tế.")
    parser.add_argument("--srs", default="docs/SRS.md", help="Đường dẫn file SRS cần kiểm tra (mặc định docs/SRS.md)")
    parser.add_argument("--repo", default=None, help="Thư mục gốc repository (mặc định tự dò)")
    parser.add_argument("--only", default=None, help="Chỉ chạy các phép kiểm chỉ định, cách nhau bằng dấu phẩy (vd: C1,C4)")

    args = parser.parse_args()

    repo_root = pathlib.Path(args.repo).resolve() if args.repo else pathlib.Path(__file__).resolve().parents[2]
    srs_path = pathlib.Path(args.srs)
    if not srs_path.is_absolute():
        srs_path = repo_root / srs_path

    if not srs_path.exists():
        print(f"LỖI: Không tìm thấy file SRS tại {srs_path}", file=sys.stderr)
        sys.exit(2)

    facts = facts_from_code(repo_root)
    srs = load_srs(srs_path)

    all_checks = {
        "C1": lambda: check_c1(srs, facts),
        "C2": lambda: check_c2(srs, facts),
        "C3": lambda: check_c3(srs, facts, repo_root),
        "C4": lambda: check_c4(srs, facts),
        "C5": lambda: check_c5(srs, facts),
        "C6": lambda: check_c6(srs, facts),
        "C7": lambda: check_c7(srs, facts),
        "C8": lambda: check_c8(srs, facts),
        "C9": lambda: check_c9(srs, facts),
        "C10": lambda: check_c10(srs, facts),
        "C11": lambda: check_c11(srs, facts),
        "C12": lambda: check_c12(srs, facts, repo_root),
    }

    selected_checks = list(all_checks.keys())
    if args.only:
        selected_checks = [c.strip().upper() for c in args.only.split(",") if c.strip().upper() in all_checks]

    total_errors = []
    print(f"=== BẮT ĐẦU KIỂM TRA SRS: {srs_path.name} ===")
    for c_id in selected_checks:
        errs = all_checks[c_id]()
        if errs:
            print(f"\n[{c_id}] Phát hiện {len(errs)} lỗi:")
            for e in errs:
                print(f"  - {e}")
            total_errors.extend(errs)
        else:
            print(f"[{c_id}] ĐẠT")

    print("\n-------------------------------------------------------")
    print(f"Kết quả: {len(total_errors)} lỗi / {len(selected_checks)} phép kiểm.")

    if total_errors:
        sys.exit(1)
    else:
        print("TẤT CẢ PHÉP KIỂM ĐÃ ĐẠT!")
        sys.exit(0)


if __name__ == "__main__":
    main()
