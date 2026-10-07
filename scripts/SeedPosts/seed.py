"""Nạp bài viết mẫu vào MongoDB, chạy lại an toàn và giữ dữ liệu hiện có."""

from __future__ import annotations

import argparse
import random
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from os import environ
from typing import Any, Sequence

from bson import ObjectId
from faker import Faker
from pymongo import MongoClient, UpdateOne


DEFAULT_POST_COUNT = 100
DEFAULT_MONGODB_URI = "mongodb://localhost:27017"
DEFAULT_DATABASE = "newsdb"
SEED = 20261007

CATEGORIES = (
    {"name": "Thời sự", "slug": "thoi-su"},
    {"name": "Thể thao", "slug": "the-thao"},
    {"name": "Công nghệ", "slug": "cong-nghe"},
    {"name": "Giải trí", "slug": "giai-tri"},
    {"name": "Kinh doanh", "slug": "kinh-doanh"},
)


def slugify(value: str) -> str:
    """Chuẩn hóa tiếng Việt thành slug ASCII theo quy ước API."""
    normalized = value.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", normalized)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def build_posts(
    count: int,
    category_ids: Sequence[ObjectId],
    *,
    reference_time: datetime | None = None,
    seed: int = SEED,
) -> list[dict[str, Any]]:
    """Tạo bài viết mẫu đúng schema, không truy cập database."""
    if count < 1:
        raise ValueError("Số bài viết phải lớn hơn 0.")
    if not category_ids:
        raise ValueError("Cần ít nhất một ObjectId chuyên mục để tạo bài viết.")

    faker = Faker("vi_VN")
    faker.seed_instance(seed)
    rng = random.Random(seed)
    now = reference_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    posts: list[dict[str, Any]] = []
    for index in range(count):
        title = faker.sentence(nb_words=8).strip().rstrip(".!?")
        created_at = now - timedelta(
            days=rng.randint(0, 365),
            seconds=rng.randint(0, 86_399),
        )
        posts.append(
            {
                "title": title,
                "slug": f"tin-mau-{index + 1:06d}",
                "content": "\n\n".join(faker.paragraphs(nb=rng.randint(3, 6))),
                "imageUrl": f"https://picsum.photos/seed/newscache-{index + 1:03d}/800/450",
                "categoryId": rng.choice(category_ids),
                "authorId": None,
                "views": 0,
                "isDeleted": False,
                "deletedAt": None,
                "createdAt": created_at,
                "updatedAt": created_at,
            }
        )
    return posts


def ensure_categories(collection: Any, now: datetime) -> list[ObjectId]:
    """Tạo chuyên mục còn thiếu, giữ nguyên chuyên mục đã tồn tại."""
    category_ids: list[ObjectId] = []
    for category in CATEGORIES:
        collection.update_one(
            {"slug": category["slug"]},
            {
                "$setOnInsert": {
                    **category,
                    "description": None,
                    "createdAt": now,
                }
            },
            upsert=True,
        )
        saved = collection.find_one({"slug": category["slug"]}, {"_id": 1})
        if not saved:
            raise RuntimeError(f"Không tạo/đọc được chuyên mục {category['name']}.")
        category_ids.append(saved["_id"])
    return category_ids


def upsert_posts(collection: Any, posts: Sequence[dict[str, Any]]) -> Any:
    """Nạp bài mẫu còn thiếu; giữ nguyên bài đã có cùng slug."""
    operations = [
        UpdateOne({"slug": post["slug"]}, {"$setOnInsert": post}, upsert=True)
        for post in posts
    ]
    return collection.bulk_write(operations, ordered=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nạp tối thiểu 100 bài viết mẫu có ảnh vào MongoDB newsdb.posts."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_POST_COUNT,
        help="Số bài cần seed (mặc định: 100; hỗ trợ 1.000+ bài).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tạo và kiểm tra dữ liệu mẫu nhưng không kết nối/ghi MongoDB.",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.count < DEFAULT_POST_COUNT:
        raise SystemExit("SCRUM-32 yêu cầu tối thiểu 100 bài; --count phải >= 100.")

    if args.dry_run:
        posts = build_posts(args.count, [ObjectId() for _ in CATEGORIES])
        print(f"Dry run thành công: tạo {len(posts)} bài mẫu; không ghi MongoDB.")
        print(f"Ví dụ: {posts[0]['title']} | {posts[0]['imageUrl']}")
        return 0

    mongo_uri = environ.get("MONGODB_URI", DEFAULT_MONGODB_URI)
    database_name = environ.get("MONGODB_DATABASE", DEFAULT_DATABASE)
    now = datetime.now(timezone.utc)

    with MongoClient(mongo_uri, serverSelectionTimeoutMS=5_000) as client:
        database = client[database_name]
        database.command("ping")
        category_ids = ensure_categories(database["categories"], now)
        posts = build_posts(args.count, category_ids, reference_time=now)
        result = upsert_posts(database["posts"], posts)

    print(
        f"Đã seed {args.count} bài mẫu có ảnh vào {database_name}.posts "
        f"({result.upserted_count} mới, {result.matched_count} đã tồn tại)."
    )
    print(f"Chuyên mục được dùng: {len(category_ids)}; dữ liệu cũ không bị xóa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
