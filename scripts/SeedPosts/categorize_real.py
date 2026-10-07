"""Phân bài thật theo chủ đề; giữ nguyên nội dung, nguồn và lượt xem."""

import argparse
from collections import Counter
import json
import os
import re
import sys
import unicodedata

from pymongo import MongoClient, UpdateOne
import redis

from import_real import category, LIST_VERSION_KEY, post_cache_key
from seed import CATEGORIES


TOPICS = {
    "cong-nghe": (
        "công nghệ thông tin", "máy tính", "phần mềm", "phần cứng", "hệ điều hành",
        "ngôn ngữ lập trình", "lập trình", "tin học", "internet", "trình duyệt",
        "world wide web", "điện thoại di động", "điện thoại thông minh", "viễn thông",
        "bộ vi xử lý", "bộ xử lý", "bán dẫn", "robot", "trí tuệ nhân tạo",
        "điện toán", "mạng máy tính", "học máy", "mật mã học", "điện tử",
        "airbus", "boeing", "kỹ thuật hàng không",
    ),
    "giai-tri": (
        "ca sĩ", "diễn viên", "điện ảnh", "bộ phim", "phim truyện", "âm nhạc",
        "nhạc sĩ", "nghệ sĩ", "ban nhạc", "album", "tiểu thuyết", "nhà văn",
        "truyện tranh", "giải oscar", "phim hoạt hình", "nhà thơ", "sân khấu",
    ),
    "kinh-doanh": (
        "kinh tế", "kinh doanh", "ngân hàng", "tài chính", "chứng khoán",
        "thương mại", "doanh nghiệp", "cổ phiếu", "tiền tệ", "kinh tế học",
        "tập đoàn", "lạm phát", "thị trường chứng khoán", "doanh nhân", "trái phiếu",
        "công ty bảo hiểm", "bảo hiểm nhân thọ", "thuế", "thương hiệu", "xuất khẩu", "nhập khẩu",
    ),
    "the-thao": (
        "bóng đá", "bóng rổ", "bóng chuyền", "quần vợt", "tennis", "cầu lông",
        "điền kinh", "thể thao", "vận động viên", "cầu thủ", "huấn luyện viên",
        "olympic", "thế vận hội", "world cup", "đua xe", "đội tuyển", "võ thuật",
        "bơi lội", "bóng bàn", "giải vô địch", "sân vận động",
    ),
    "thoi-su": (
        "chính trị", "tổng thống", "thủ tướng", "quốc hội", "chính phủ", "bầu cử",
        "ngoại giao", "liên hợp quốc", "liên hiệp quốc", "biểu tình", "đại dịch",
        "covid-19", "nhà nước", "chủ tịch nước", "nhà chính trị", "chính trị gia",
        "quyền con người", "nhân quyền", "hiến pháp", "đảng chính trị",
    ),
}
PATTERNS = {slug: [re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)") for term in terms]
            for slug, terms in TOPICS.items()}


def classify_post(post):
    if post["slug"].startswith("real-wikinews-en-"):
        return "tin-wikinews"
    title = unicodedata.normalize("NFC", post["title"]).casefold()
    # Phần ghi nguồn/giấy phép không được ảnh hưởng đến phân loại nội dung.
    text = post["content"].split("--- Ghi nguồn ---", 1)[0].strip()
    intro = unicodedata.normalize("NFC", text.split("\n\n", 1)[0][:700]).casefold()
    # Địa danh/trường học không biến thành tin kinh doanh/thể thao chỉ vì
    # một đoạn giới thiệu nhắc tới kinh tế hoặc một câu lạc bộ địa phương.
    place_definition = re.search(r"là (?:một |1 )?(?:thành phố|xã|làng|thị trấn|thị xã|quận|huyện|tỉnh|thủ đô|thủ phủ|sân bay|trường đại học)", intro[:400])
    if place_definition:
        return "tri-thuc-wikipedia"
    scores = {slug: sum(5 * bool(p.search(title)) + bool(p.search(intro)) for p in patterns)
              for slug, patterns in PATTERNS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else "tri-thuc-wikipedia"


def categorize(db, cache=None, dry_run=False):
    definitions = list(CATEGORIES) + [
        {"slug": "tin-wikinews", "name": "Tin quốc tế · Wikinews"},
        {"slug": "tri-thuc-wikipedia", "name": "Tri thức · Wikipedia"},
    ]
    posts = list(db.posts.find({"slug": {"$regex": "^real-(wikipedia-vi|wikinews-en)-"}, "isDeleted": False},
                              {"title": 1, "content": 1, "slug": 1, "categoryId": 1}))
    assigned = [(post, classify_post(post)) for post in posts]
    counts = Counter(slug for _, slug in assigned)
    if any(not counts[d["slug"]] for d in definitions):
        raise RuntimeError("Không đủ bài phù hợp cho một số chuyên mục; cần bổ sung nguồn theo chủ đề.")
    if not dry_run:
        category_ids = {d["slug"]: category(db, d["slug"], d["name"]) for d in definitions}
        changed = [post for post, slug in assigned if post.get("categoryId") != category_ids[slug]]
        operations = [UpdateOne({"_id": post["_id"], "categoryId": post.get("categoryId")},
                                {"$set": {"categoryId": category_ids[slug]}})
                      for post, slug in assigned if post.get("categoryId") != category_ids[slug]]
        if operations:
            try:
                db.posts.bulk_write(operations, ordered=False)
            finally:
                # Vô hiệu hóa Redis sau MongoDB, kể cả khi batch chỉ ghi được một phần.
                pipe = cache.pipeline(transaction=False)
                for post in changed:
                    pipe.delete(post_cache_key(post["_id"]))
                pipe.incr(LIST_VERSION_KEY)
                pipe.execute()
    return {d["name"]: {"count": counts[d["slug"]],
                         "samples": [p["title"] for p, slug in assigned if slug == d["slug"]][:8]}
            for d in definitions}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Phân loại bài thật theo tiêu đề và phần mở đầu.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cache = None
    if not args.dry_run:
        cache = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=5)
        cache.ping()
    with MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017")) as client:
        report = categorize(client[os.getenv("MONGODB_DATABASE", "newsdb")], cache, args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
