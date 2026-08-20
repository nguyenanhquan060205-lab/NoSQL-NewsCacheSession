"""
Seed 100 bài viết mẫu vào MongoDB (newsdb.posts).
Yêu cầu: pip install pymongo faker

Cách chạy:
    cd scripts/SeedPosts
    python seed.py
"""

# TODO [SV3]: Implement seed script
# 1. Kết nối MongoDB: MongoClient("mongodb://localhost:27017")
# 2. Chọn database: client["newsdb"]
# 3. Chọn collection: db["posts"]
# 4. Dùng Faker để tạo 100 bài viết mẫu:
#    - title: faker.sentence()
#    - content: faker.paragraphs(nb=3) — nội dung dài
#    - imageUrl: f"https://picsum.photos/seed/{i}/800/400" (ảnh placeholder)
#    - authorId: None hoặc ObjectId random
#    - views: 0
#    - createdAt: faker.date_time_this_year()
#    - updatedAt: = createdAt
# 5. Insert batch: db.posts.insert_many(posts)
# 6. In ra: "Đã nạp 100 bài viết vào MongoDB!"

if __name__ == "__main__":
    print("TODO: Implement seed script — xem hướng dẫn trong comment ở trên.")
