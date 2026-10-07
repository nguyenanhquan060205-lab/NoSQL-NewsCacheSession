"""Nạp nội dung thật có ảnh và ghi nguồn từ Wikipedia tiếng Việt/Wikinews."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pyarrow.parquet as pq
import redis
import mwparserfromhell
from pymongo import MongoClient

from seed import upsert_posts

USER_AGENT = "NewsCacheSession/1.0 (https://github.com/nguyenanhquan060205-lab/NoSQL-NewsCacheSession; educational content import)"
DATA_DIR = Path(__file__).parent / "data"
SNAPSHOT = datetime(2023, 11, 1, tzinfo=timezone.utc)
PARQUET_URL = "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/20231101.vi/train-00000-of-00004.parquet"
LIST_VERSION_KEY = "posts:ver"


def post_cache_key(post_id):
    return "post:" + str(post_id)


def api(domain, params):
    """Request tuần tự, có timeout và backoff khi nguồn bận."""
    base = {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5}
    for attempt in range(6):
        try:
            req = Request(f"https://{domain}/w/api.php?{urlencode(base | params)}",
                          headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=60) as response:
                result = json.load(response)
            if "error" in result:
                code = result["error"].get("code")
                if code not in {"maxlag", "ratelimited", "readonly"}:
                    raise RuntimeError(str(result["error"]))
                raise URLError(code)
            time.sleep(0.15)
            return result
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504}:
                raise
            delay = max(float(error.headers.get("Retry-After", 0)), 2 ** attempt)
        except (URLError, TimeoutError):
            delay = 2 ** attempt
        print(f"Nguồn bận; thử lại sau {delay:.0f}s", flush=True)
        time.sleep(delay)
    raise RuntimeError(f"Không truy cập được API {domain} sau 6 lần thử.")


def plain(value):
    return html.unescape(re.sub(r"<[^>]*>", "", value or "")).strip()


def image_name(value):
    return unicodedata.normalize("NFC", (value or "").replace("_", " "))


def image_credits(names):
    """Chỉ chấp nhận ảnh Commons có giấy phép mở và thông tin ghi nguồn."""
    if not names:
        return {}
    names = list(dict.fromkeys(names))
    if len(names) > 50:
        images = {}
        for offset in range(0, len(names), 50):
            images.update(image_credits(names[offset:offset + 50]))
        return images
    result = api("commons.wikimedia.org", {
        "titles": "|".join("File:" + name for name in dict.fromkeys(names)),
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 800,
    })
    images = {}
    for page in result.get("query", {}).get("pages", []):
        info = page.get("imageinfo", [{}])[0]
        metadata = info.get("extmetadata", {})
        license_name = plain(metadata.get("LicenseShortName", {}).get("value", ""))
        license_url = plain(metadata.get("LicenseUrl", {}).get("value", ""))
        author = plain(metadata.get("Artist", {}).get("value", ""))
        free_license = re.fullmatch(r"CC BY(?:-SA)?(?: [1-4]\.\d)?", license_name)
        if not author or not (free_license or license_name in {"CC0", "Public domain"}):
            continue
        image_url = info.get("thumburl") or info.get("url", "")
        if not image_url.startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/")):
            continue
        images[image_name(page["title"].removeprefix("File:"))] = {
            "url": image_url, "author": author, "license": license_name,
            "licenseUrl": license_url,
            "fileUrl": info.get("descriptionurl", ""),
        }
    return images


def make_post(record, image, category_id, source):
    title, text = record["title"].strip(), record["text"].strip()
    source_url = record["url"]
    if not text or not title or len(text) < 500:
        raise ValueError("Bài quá ngắn hoặc thiếu tiêu đề.")
    if source == "wikipedia-vi":
        license_name = "CC BY-SA 3.0"
        license_url = "https://creativecommons.org/licenses/by-sa/3.0/"
        label = "Wikipedia tiếng Việt — nội dung bách khoa, bản dữ liệu 01/11/2023"
        notice = "Văn bản thuần từ dataset Wikimedia; bỏ định dạng wiki. Xem tác giả và lịch sử tại nguồn."
        date = SNAPSHOT
    else:
        license_name = "CC BY 2.5 / CC BY 4.0 (theo thời điểm xuất bản ở nguồn)"
        license_url = "https://en.wikinews.org/wiki/Wikinews:Copyright"
        label = "Wikinews tiếng Anh — tin tức cộng đồng, nguyên ngữ"
        notice = "Văn bản thuần, bỏ định dạng và template wiki; ngày hiển thị là ngày sửa đổi nguồn. Xem tác giả tại nguồn."
        date = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
    credits = (
        f"Nguồn nội dung: {label}\n{source_url}\n{notice}\n"
        f"Giấy phép nội dung: {license_name}\n{license_url}\n"
        f"Nguồn ảnh: {image['fileUrl']}\nTác giả ảnh: {image['author']}\n"
        f"Giấy phép ảnh: {image['license']}\n{image['licenseUrl']}"
    )
    return {
        "title": title, "slug": f"real-{source}-{record['id']}",
        "content": text + "\n\n--- Ghi nguồn ---\n" + credits,
        "imageUrl": image["url"], "categoryId": category_id, "authorId": None,
        "views": 0, "isDeleted": False, "deletedAt": None,
        "createdAt": date, "updatedAt": date,
    }


def category(db, slug, name):
    db.categories.update_one({"slug": slug}, {"$setOnInsert": {
        "name": name, "slug": slug, "description": "Nội dung thật có ghi nguồn và giấy phép.",
        "createdAt": datetime.now(timezone.utc),
    }}, upsert=True)
    return db.categories.find_one({"slug": slug})["_id"]


def download_parquet():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / "wikipedia-vi-20231101-00000.parquet"
    if target.exists():
        return target
    print("Tải dataset Wikipedia tiếng Việt (~291 MB)...", flush=True)
    temporary = target.with_suffix(".part")
    req = Request(PARQUET_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=120) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    pq.ParquetFile(temporary)
    temporary.replace(target)
    return target


def save_batch(db, cache, records, images, category_id, source, limit):
    accepted = []
    for record in records:
        image = images.get(image_name(record.get("image")))
        if not image:
            continue
        try:
            post = make_post(record, image, category_id, source)
        except ValueError:
            continue
        accepted.append((post, record, image))
        if len(accepted) >= limit:
            break
    if not accepted:
        return 0
    # MongoDB trước, tăng phiên bản cache danh sách sau, kể cả nếu bulk ghi dở dang.
    try:
        result = upsert_posts(db.posts, [item[0] for item in accepted])
    finally:
        cache.incr(LIST_VERSION_KEY)
    with (DATA_DIR / "sources.jsonl").open("a", encoding="utf-8") as log:
        for post, record, image in accepted:
            log.write(json.dumps({"slug": post["slug"], "sourceUrl": record["url"],
                                  "image": image, "importedAt": datetime.now(timezone.utc).isoformat()},
                                 ensure_ascii=False) + "\n")
    return result.upserted_count


def import_wikipedia(db, cache, target):
    file = download_parquet()
    category_id = category(db, "tri-thuc-wikipedia", "Tri thức · Wikipedia")
    existing = set(db.posts.distinct("slug", {"slug": {"$regex": "^real-wikipedia-vi-"}}))
    total = len(existing)
    pending = []
    scanned = 0
    for batch in pq.ParquetFile(file).iter_batches(batch_size=1000):
        for record in batch.to_pylist():
            if total >= target:
                print(f"Wikipedia tiếng Việt: đủ {total}/{target} bài", flush=True)
                return
            scanned += 1
            if len(record["text"]) < 500 or f"real-wikipedia-vi-{record['id']}" in existing:
                continue
            pending.append(record)
            if len(pending) < 50:
                continue
            total += wikipedia_batch(db, cache, pending, category_id, target - total)
            pending = []
            print(f"Wikipedia tiếng Việt: {total}/{target}; đã xét {scanned} bài", flush=True)
    if pending and total < target:
        total += wikipedia_batch(db, cache, pending, category_id, target - total)
    if total < target:
        raise RuntimeError(f"Dataset hiện tại chỉ lấy được {total}/{target} bài phù hợp có ảnh.")


def wikipedia_batch(db, cache, records, category_id, limit):
    result = api("vi.wikipedia.org", {
        "pageids": "|".join(str(r["id"]) for r in records),
        "prop": "pageimages", "piprop": "name", "pilicense": "free",
    })
    pages = {str(p["pageid"]): p for p in result.get("query", {}).get("pages", [])}
    for record in records:
        record["image"] = pages.get(str(record["id"]), {}).get("pageimage")
    images = image_credits([r["image"] for r in records if r["image"]])
    return save_batch(db, cache, records, images, category_id, "wikipedia-vi", limit)


def import_wikinews(db, cache, target):
    category_id = category(db, "tin-wikinews", "Tin quốc tế · Wikinews")
    total = db.posts.count_documents({"slug": {"$regex": "^real-wikinews-en-"}})
    continuation = {}
    while total < target:
        result = api("en.wikinews.org", {
            "generator": "categorymembers", "gcmtitle": "Category:Published",
            "gcmnamespace": 0, "gcmlimit": 20, "gcmsort": "timestamp", "gcmdir": "older",
            "prop": "pageimages|info|revisions",
            "piprop": "name", "pilicense": "free", "inprop": "url",
            "rvprop": "timestamp|content", "rvslots": "main", **continuation,
        })
        pages = result.get("query", {}).get("pages", [])
        records = [{"id": p["pageid"], "title": p["title"],
                    "text": mwparserfromhell.parse(p["revisions"][0]["slots"]["main"]["content"]).strip_code(),
                    "url": p["fullurl"], "image": p.get("pageimage"),
                    "timestamp": p.get("revisions", [{}])[0].get("timestamp", "")}
                   for p in pages if p.get("revisions")]
        images = image_credits([r["image"] for r in records if r["image"]])
        total += save_batch(db, cache, records, images, category_id, "wikinews-en", target - total)
        print(f"Wikinews: {total}/{target}", flush=True)
        continuation = result.get("continue")
        if not continuation:
            break
    if total < target:
        raise RuntimeError(f"Wikinews chỉ lấy được {total}/{target} bài phù hợp.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Nạp nội dung thật có ảnh, ghi nguồn và giấy phép.")
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--wikinews-count", type=int, default=100)
    parser.add_argument("--hide-samples", action="store_true", help="Ẩn mềm các bài Faker chưa sửa của script seed cũ sau khi nạp đủ bài thật.")
    args = parser.parse_args()
    if not 0 <= args.wikinews_count <= args.count or args.count < 1:
        parser.error("Số bài phải dương; wikinews-count nằm trong 0..count.")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=5)
    cache.ping()
    with MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"), serverSelectionTimeoutMS=5000) as client:
        db = client[os.getenv("MONGODB_DATABASE", "newsdb")]
        db.command("ping")
        import_wikinews(db, cache, args.wikinews_count)
        import_wikipedia(db, cache, args.count - args.wikinews_count)
        total = db.posts.count_documents({"slug": {"$regex": "^real-(wikipedia-vi|wikinews-en)-"}, "isDeleted": False})
        if total < args.count:
            raise RuntimeError(f"Chưa đủ bài đang hiển thị: {total}/{args.count}.")
        if args.hide_samples:
            sample_filter = {"slug": {"$regex": r"^tin-mau-\d{6}$"}, "authorId": None,
                             "isDeleted": False, "$expr": {"$eq": ["$createdAt", "$updatedAt"]}}
            samples = list(db.posts.find(sample_filter, {"_id": 1}))
            if samples:
                db.posts.update_many({"_id": {"$in": [p["_id"] for p in samples]}},
                                     {"$set": {"isDeleted": True, "deletedAt": datetime.now(timezone.utc)}})
                cache.delete(*[post_cache_key(p["_id"]) for p in samples])
                cache.incr(LIST_VERSION_KEY)
            print(f"Đã ẩn mềm {len(samples)} bài Faker cũ; có thể khôi phục từ MongoDB.", flush=True)
        from categorize_real import categorize
        topic_report = categorize(db, cache)
        print("Số bài theo chuyên mục: " + json.dumps({name: item["count"] for name, item in topic_report.items()}, ensure_ascii=False), flush=True)
        print(f"Hoàn tất: {total} bài thật có ảnh, ghi nguồn, views khởi tạo bằng 0.", flush=True)


if __name__ == "__main__":
    main()
