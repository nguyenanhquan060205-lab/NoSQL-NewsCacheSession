"""
Benchmark: So sánh thời gian đọc bài viết từ DB gốc vs Redis Cache.
Yêu cầu: pip install requests matplotlib

Cách chạy:
    cd scripts/Benchmark
    python benchmark.py
"""

# TODO [SV3]: Implement benchmark script
# 1. Chọn 1 post_id đã tồn tại (hoặc lấy từ API GET /api/posts)
#
# 2. Lần 1 — Cache Miss (đọc từ MongoDB):
#    - Xóa cache trước: gọi DELETE hoặc dùng redis-cli DEL post:{id}
#    - start = time.time()
#    - requests.get(f"http://localhost:5000/api/posts/{post_id}")
#    - time_db = time.time() - start
#    - In ra: f"Lần 1 (DB gốc): {time_db*1000:.2f}ms"
#
# 3. Lần 2 — Cache Hit (đọc từ Redis):
#    - start = time.time()
#    - requests.get(f"http://localhost:5000/api/posts/{post_id}")
#    - time_cache = time.time() - start
#    - In ra: f"Lần 2 (Redis Cache): {time_cache*1000:.2f}ms"
#
# 4. Vẽ biểu đồ so sánh (matplotlib):
#    - Bar chart: DB vs Cache
#    - Lưu file: benchmark_result.png
#
# 5. (Bonus) Lặp với nhiều bài viết, tính trung bình

if __name__ == "__main__":
    print("TODO: Implement benchmark script — xem hướng dẫn trong comment ở trên.")
