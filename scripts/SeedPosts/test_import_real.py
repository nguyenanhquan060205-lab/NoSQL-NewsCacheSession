import unittest
from unittest.mock import patch

from bson import ObjectId

from import_real import image_credits, image_name, make_post, save_batch


class RealImportTests(unittest.TestCase):
    def test_image_names_match_across_wikimedia_endpoints(self):
        self.assertEqual(image_name("Hà_Nội.jpg"), image_name("Hà Nội.jpg"))

    def test_post_keeps_real_text_and_attribution_with_existing_schema(self):
        record = {"id": "123", "title": "Hà Nội", "text": "Nội dung nguồn. " * 60,
                  "url": "https://vi.wikipedia.org/wiki/H%C3%A0_N%E1%BB%99i"}
        image = {"url": "https://upload.wikimedia.org/example.jpg", "author": "Tác giả ảnh",
                 "fileUrl": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                 "license": "CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/"}
        category_id = ObjectId()
        post = make_post(record, image, category_id, "wikipedia-vi")
        self.assertTrue(post["content"].startswith(record["text"].strip()))
        self.assertIn(record["url"], post["content"])
        self.assertIn(image["author"], post["content"])
        self.assertIn(image["licenseUrl"], post["content"])
        self.assertEqual(post["views"], 0)
        self.assertEqual(post["categoryId"], category_id)
        self.assertEqual(post["slug"], "real-wikipedia-vi-123")

    def test_missing_license_or_restricted_image_is_rejected(self):
        pages = []
        for name, license_name, author in [("free.jpg", "CC BY-SA 4.0", "Alice"),
                                           ("restricted.jpg", "Fair use", "Bob"),
                                           ("noncommercial.jpg", "CC BY-NC 4.0", "Bob"),
                                           ("unknown.jpg", "CC BY 4.0", "")]:
            pages.append({"title": "File:" + name, "imageinfo": [{
                "url": "https://thumb.wikimedia.org/" + name,
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:" + name,
                "extmetadata": {"LicenseShortName": {"value": license_name}, "Artist": {"value": author}},
            }]})
        with patch("import_real.api", return_value={"query": {"pages": pages}}):
            images = image_credits(["free.jpg", "restricted.jpg", "unknown.jpg"])
        self.assertEqual(list(images), ["free.jpg"])

    def test_short_article_is_rejected(self):
        with self.assertRaises(ValueError):
            make_post({"id": "1", "title": "Ngắn", "text": "Quá ngắn", "url": "https://vi.wikipedia.org/wiki/Test"},
                      {}, ObjectId(), "wikipedia-vi")

    def test_batch_without_licensed_image_never_writes(self):
        from unittest.mock import Mock
        db, cache = Mock(), Mock()
        self.assertEqual(save_batch(db, cache, [{"image": "bad.jpg"}], {}, ObjectId(), "wikipedia-vi", 10), 0)
        db.posts.bulk_write.assert_not_called()
        cache.incr.assert_not_called()


if __name__ == "__main__":
    unittest.main()
