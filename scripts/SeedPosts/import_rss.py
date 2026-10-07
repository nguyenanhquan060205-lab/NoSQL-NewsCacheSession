"""Bổ sung tóm tắt RSS VnExpress cho demo phi lợi nhuận, không cào toàn bài."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
import os
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from pymongo import MongoClient
import redis

from import_real import LIST_VERSION_KEY, USER_AGENT
from seed import CATEGORIES, ensure_categories, upsert_posts

FEEDS = {
    'thoi-su': 'thoi-su', 'the-thao': 'the-thao',
    'cong-nghe': 'khoa-hoc-cong-nghe', 'giai-tri': 'giai-tri',
    'kinh-doanh': 'kinh-doanh',
}


class SummaryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.image = None

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and self.image is None:
            self.image = dict(attrs).get('src')


def parse_feed(xml, category_id, now, days=14, limit=30):
    """Giữ ngày thật, loại link ngoài nguồn và tin cũ; slug ổn định theo ID."""
    posts = {}
    for item in ET.fromstring(xml).findall('./channel/item'):
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        url = urlsplit(link)
        match = re.search(r'-(\d+)\.html$', url.path)
        if url.scheme != 'https' or url.netloc != 'vnexpress.net' or not match:
            continue
        try:
            date = parsedate_to_datetime(item.findtext('pubDate') or '')
            if date.tzinfo is None:
                continue
            date = date.astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if not now - timedelta(days=days) <= date <= now:
            continue
        summary = SummaryParser()
        summary.feed(item.findtext('description') or '')
        text = ' '.join(' '.join(summary.parts).split())
        if not title or not text:
            continue
        enclosure = item.find('enclosure')
        image = enclosure.get('url') if enclosure is not None else summary.image
        image_url = urlsplit(image or '')
        if image_url.scheme != 'https' or not (image_url.hostname or '').endswith('.vnecdn.net'):
            image = None
        slug = 'real-vnexpress-rss-' + match.group(1)
        posts[slug] = {
            'title': title, 'slug': slug,
            'content': text + '\n\nĐây là bản tóm tắt từ RSS, không phải toàn bộ bài báo.'
                + '\n\n--- Ghi nguồn ---\nNguồn: VnExpress RSS\nĐọc toàn bài tại báo gốc:\n'
                + link + '\nThông tin và ảnh do kênh RSS VnExpress cung cấp.'
                + '\nChỉ dùng cho demo học tập phi lợi nhuận; tuân thủ yêu cầu ngừng phân phối của nguồn.'
                + '\nĐiều khoản RSS: https://vnexpress.net/rss',
            'imageUrl': image, 'categoryId': category_id, 'authorId': None,
            'views': 0, 'isDeleted': False, 'deletedAt': None,
            'createdAt': date, 'updatedAt': date,
        }
    return sorted(posts.values(), key=lambda p: p['createdAt'], reverse=True)[:limit]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--days', type=int, default=14)
    parser.add_argument('--per-category', type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.days <= 30 or not 1 <= args.per_category <= 50:
        parser.error('--days phải từ 1–30; --per-category phải từ 1–50.')
    now = datetime.now(timezone.utc)
    # Tải và kiểm tra hết các feed trước khi bắt đầu ghi database.
    batches = {}
    for slug, feed in FEEDS.items():
        request = Request(f'https://vnexpress.net/rss/{feed}.rss', headers={'User-Agent': USER_AGENT})
        with urlopen(request, timeout=30) as response:
            batches[slug] = parse_feed(response.read(), None, now, args.days, args.per_category)
        if not batches[slug]:
            raise RuntimeError(f'Không có tin gần đây cho {slug}; chưa ghi dữ liệu.')
    posts = {}
    for slug, batch in batches.items():
        for post in batch:
            posts.setdefault(post['slug'], (slug, post))
    inserted = 0
    if not args.dry_run:
        cache = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), socket_timeout=5)
        cache.ping()
        with MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'), serverSelectionTimeoutMS=5000) as client:
            db = client[os.getenv('MONGODB_DATABASE', 'newsdb')]
            ids = dict(zip((c['slug'] for c in CATEGORIES), ensure_categories(db.categories, now)))
            for slug, post in posts.values():
                post['categoryId'] = ids[slug]
            try:
                result = upsert_posts(db.posts, [p for _, p in posts.values()])
                inserted = result.upserted_count
            finally:
                # MongoDB trước, vô hiệu hóa cache danh sách sau, kể cả batch ghi dở.
                cache.incr(LIST_VERSION_KEY)
    print(json.dumps({'dryRun': args.dry_run, 'selected': len(posts), 'inserted': inserted,
                      'categories': dict(Counter(slug for slug, _ in posts.values())),
                      'newest': max(p['createdAt'] for _, p in posts.values()).isoformat()},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
