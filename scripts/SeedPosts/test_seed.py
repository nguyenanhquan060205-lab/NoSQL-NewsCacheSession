import unittest
from datetime import datetime, timezone

from bson import ObjectId

from seed import CATEGORIES, build_posts, ensure_categories, slugify, upsert_posts


class SeedPostsTests(unittest.TestCase):
    def test_slugify_removes_vietnamese_diacritics(self):
        self.assertEqual(slugify("Đà Nẵng: Công nghệ mới!"), "da-nang-cong-nghe-moi")

    def test_build_posts_creates_schema_compatible_posts_with_images(self):
        category_ids = [ObjectId() for _ in CATEGORIES]
        fixed_now = datetime(2026, 10, 7, tzinfo=timezone.utc)

        posts = build_posts(100, category_ids, reference_time=fixed_now)

        self.assertEqual(len(posts), 100)
        self.assertEqual(len({post["slug"] for post in posts}), 100)
        for post in posts:
            self.assertEqual(
                set(post),
                {
                    "title",
                    "slug",
                    "content",
                    "imageUrl",
                    "categoryId",
                    "authorId",
                    "views",
                    "isDeleted",
                    "deletedAt",
                    "createdAt",
                    "updatedAt",
                },
            )
            self.assertTrue(post["title"])
            self.assertGreaterEqual(len(post["content"]), 100)
            self.assertTrue(post["imageUrl"].startswith("https://picsum.photos/seed/"))
            self.assertIsInstance(post["categoryId"], ObjectId)
            self.assertIn(post["categoryId"], category_ids)
            self.assertIsNone(post["authorId"])
            self.assertEqual(post["views"], 0)
            self.assertEqual(post["createdAt"], post["updatedAt"])
            self.assertTrue(post["createdAt"].tzinfo)

    def test_build_posts_is_reproducible_for_safe_reruns(self):
        category_ids = [ObjectId("650000000000000000000001")]
        fixed_now = datetime(2026, 10, 7, tzinfo=timezone.utc)

        first = build_posts(100, category_ids, reference_time=fixed_now)
        second = build_posts(100, category_ids, reference_time=fixed_now)

        self.assertEqual(first, second)

    def test_build_posts_rejects_missing_categories(self):
        with self.assertRaisesRegex(ValueError, "ObjectId chuyên mục"):
            build_posts(100, [])

    def test_slugs_are_stable_when_generator_changes_and_count_grows(self):
        ids = [ObjectId()]
        original = build_posts(100, ids, seed=1)
        expanded = build_posts(1000, ids, seed=2)
        self.assertEqual([p["slug"] for p in original], [p["slug"] for p in expanded[:100]])

    def test_ensure_categories_upserts_without_deleting_existing_data(self):
        class CollectionSpy:
            def __init__(self):
                self.documents = {}
                self.calls = []

            def update_one(self, query, update, upsert):
                self.calls.append((query, update, upsert))
                self.documents.setdefault(query["slug"], {"_id": ObjectId()})

            def find_one(self, query, projection):
                return self.documents[query["slug"]]

        collection = CollectionSpy()
        ids = ensure_categories(collection, datetime(2026, 10, 7, tzinfo=timezone.utc))

        self.assertEqual(len(ids), len(CATEGORIES))
        self.assertTrue(all(isinstance(category_id, ObjectId) for category_id in ids))
        self.assertTrue(all(call[2] is True for call in collection.calls))
        self.assertTrue(all("$setOnInsert" in call[1] for call in collection.calls))

    def test_upsert_posts_uses_stable_slug_and_set_on_insert(self):
        class CollectionSpy:
            def bulk_write(self, operations, ordered):
                self.operations = operations
                self.ordered = ordered

        collection = CollectionSpy()
        posts = build_posts(
            100,
            [ObjectId("650000000000000000000001")],
            reference_time=datetime(2026, 10, 7, tzinfo=timezone.utc),
        )

        upsert_posts(collection, posts)

        self.assertEqual(len(collection.operations), 100)
        self.assertFalse(collection.ordered)
        self.assertTrue(all(operation._upsert for operation in collection.operations))
        self.assertTrue(all("$setOnInsert" in operation._doc for operation in collection.operations))


if __name__ == "__main__":
    unittest.main()
