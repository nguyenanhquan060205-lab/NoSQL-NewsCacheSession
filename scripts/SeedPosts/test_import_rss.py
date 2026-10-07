import unittest
from datetime import datetime, timezone
from bson import ObjectId
from import_rss import parse_feed


class RssTests(unittest.TestCase):
    def feed(self, date='Thu, 08 Oct 2026 07:00:00 +0700', host='vnexpress.net'):
        return f'''<rss><channel><item><title>Tin thử nghiệm</title>
        <description><![CDATA[<a><img src="https://i1-vnexpress.vnecdn.net/test.jpg"/></a><br/>Tóm tắt &amp; nội dung.]]></description>
        <link>https://{host}/tin-thu-123.html</link><pubDate>{date}</pubDate>
        </item></channel></rss>'''

    def test_date_schema_and_safe_summary(self):
        category_id = ObjectId()
        now = datetime(2026, 10, 8, 2, tzinfo=timezone.utc)
        post = parse_feed(self.feed(), category_id, now)[0]
        self.assertEqual(post['createdAt'], datetime(2026, 10, 8, tzinfo=timezone.utc))
        self.assertEqual(post['categoryId'], category_id)
        self.assertEqual(post['slug'], 'real-vnexpress-rss-123')
        self.assertEqual(post['views'], 0)
        self.assertNotIn('<img', post['content'])
        self.assertIn('Tóm tắt & nội dung.', post['content'])
        self.assertIn('https://vnexpress.net/tin-thu-123.html', post['content'])

    def test_reject_stale_future_invalid_and_foreign_link(self):
        now = datetime(2026, 10, 8, 2, tzinfo=timezone.utc)
        for date in ['Thu, 01 Jan 2026 07:00:00 +0700', 'Fri, 09 Oct 2026 07:00:00 +0700', 'invalid']:
            self.assertEqual(parse_feed(self.feed(date), ObjectId(), now), [])
        self.assertEqual(parse_feed(self.feed(host='example.com'), ObjectId(), now), [])


if __name__ == '__main__':
    unittest.main()
