import unittest

from categorize_real import classify_post


class CategorizeRealTests(unittest.TestCase):
    def post(self, title, intro=""):
        return {"slug": "real-wikipedia-vi-1", "title": title, "content": intro}

    def test_topic_from_title_and_intro(self):
        cases = [
            ("Máy tính", "", "cong-nghe"),
            ("Một hệ thống mới", "Đây là phần mềm chạy trên hệ điều hành.", "cong-nghe"),
            ("Âm nhạc", "", "giai-tri"),
            ("Tên nghệ sĩ", "Là ca sĩ và nhạc sĩ người Việt.", "giai-tri"),
            ("Ngân hàng", "", "kinh-doanh"),
            ("Trái phiếu chính phủ", "Một loại trái phiếu.", "kinh-doanh"),
            ("Bóng đá", "", "the-thao"),
            ("Chính phủ", "", "thoi-su"),
            ("RNA", "Phân tử sinh học thuộc nhóm axit nucleic.", "tri-thuc-wikipedia"),
            ("Mũ bảo hiểm", "Dụng cụ bảo vệ đầu.", "tri-thuc-wikipedia"),
            ("Một thành phố", "Là một thành phố với nền kinh tế thương mại phát triển.", "tri-thuc-wikipedia"),
        ]
        for title, intro, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(classify_post(self.post(title, intro)), expected)

    def test_source_credits_are_not_used_as_topic_keywords(self):
        post = self.post("RNA", "Phân tử sinh học.\n\n--- Ghi nguồn ---\nTác giả ảnh: Nhạc sĩ, diễn viên")
        self.assertEqual(classify_post(post), "tri-thuc-wikipedia")

    def test_news_keeps_its_source_section(self):
        self.assertEqual(classify_post({"slug": "real-wikinews-en-3", "title": "Football", "content": "News"}), "tin-wikinews")


if __name__ == "__main__":
    unittest.main()
