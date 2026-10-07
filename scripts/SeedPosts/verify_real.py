"""Kiểm tra dữ liệu thật đã nạp và API phân trang, cache, ảnh mẫu."""

import argparse
from collections import Counter
import json
import os
import sys
from urllib.request import Request, urlopen

from bson import ObjectId
from pymongo import MongoClient

from import_real import USER_AGENT
from seed import CATEGORIES


def get_json(url):
    with urlopen(url, timeout=30) as response:
        return json.load(response), response.headers.get("X-Cache")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Xác minh bài thật trong MongoDB và API local.")
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--api", default="http://localhost:5134/api")
    args = parser.parse_args()
    with MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017")) as client:
        db = client[os.getenv("MONGODB_DATABASE", "newsdb")]
        posts = list(db.posts.find({"slug": {"$regex": "^real-(wikipedia-vi|wikinews-en)-"}, "isDeleted": False}))
        assert len(posts) == args.count, f"Số bài: {len(posts)}/{args.count}"
        assert len({post["slug"] for post in posts}) == args.count
        categories = set(db.categories.distinct("_id"))
        for post in posts:
            assert isinstance(post["categoryId"], ObjectId) and post["categoryId"] in categories
            assert post["title"] and len(post["content"]) >= 500 and "--- Ghi nguồn ---" in post["content"]
            assert post["imageUrl"].startswith(("https://upload.wikimedia.org/", "https://thumb.wikimedia.org/"))
            assert post["views"] >= 0 and post["authorId"] is None
        sources = {source: sum(p["slug"].startswith("real-" + source + "-") for p in posts)
                   for source in ["wikipedia-vi", "wikinews-en"]}
        active_posts = list(db.posts.find({"isDeleted": False}))
        category_counts = Counter(str(p["categoryId"]) for p in active_posts)
        expected_slugs = [c["slug"] for c in CATEGORIES] + ["tin-wikinews", "tri-thuc-wikipedia"]
        topic_report = {}
        for topic in db.categories.find({"slug": {"$in": expected_slugs}}):
            topic_count = category_counts[str(topic["_id"])]
            assert topic_count > 0, topic["name"]
            filtered, _ = get_json(args.api + "/posts?pageSize=12&categoryId=" + str(topic["_id"]))
            assert filtered["totalItems"] == topic_count
            assert all(p["categoryId"] == str(topic["_id"]) for p in filtered["items"])
            topic_report[topic["name"]] = topic_count
        assert len(topic_report) == len(expected_slugs)
        listing, _ = get_json(args.api + "/posts?pageSize=12")
        assert listing["totalItems"] == len(active_posts), listing["totalItems"]
        last, _ = get_json(args.api + f"/posts?pageSize=12&page={listing['totalPages']}")
        assert len(last["items"]) == (len(active_posts) % 12 or 12)
        assert all(p["slug"].startswith("real-") for p in listing["items"] + last["items"])
        samples = [next(p for p in posts if p["slug"].startswith("real-" + source + "-")) for source in sources if sources[source]]
        for post in samples:
            detail, _ = get_json(args.api + "/posts/" + str(post["_id"]))
            assert detail["title"] == post["title"] and detail["content"] == post["content"]
            _, second_cache = get_json(args.api + "/posts/" + str(post["_id"]))
            assert second_cache == "HIT"
            filtered, _ = get_json(args.api + "/posts?pageSize=12&categoryId=" + str(post["categoryId"]))
            assert filtered["totalItems"] == category_counts[str(post["categoryId"])]
            assert all(p["categoryId"] == str(post["categoryId"]) for p in filtered["items"])
            with urlopen(Request(post["imageUrl"], headers={"User-Agent": USER_AGENT}), timeout=30) as image:
                assert image.status == 200 and image.headers.get("Content-Type", "").startswith("image/")
        report = {"activeRealPosts": len(posts), "activeTotalPosts": len(active_posts), "sources": sources, "categories": topic_report,
                  "uniqueSlugs": len({post["slug"] for post in posts}), "pagesOf12": listing["totalPages"],
                  "lastPageItems": len(last["items"]), "schema": "OK", "api": "OK", "sampleImages": "HTTP 200"}
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
