namespace NewsCacheSession.Api.Services;

/// <summary>
/// Ai được đăng bài và tải ảnh. Bản deploy công khai đặt <c>PostingSettings:AdminOnly=true</c> để người lạ
/// đăng ký xong không đăng được nội dung (ví dụ link lừa đảo — đủ để Google gắn cờ cả trang).
/// Mặc định tắt: chạy local và demo chấm điểm giữ nguyên quy tắc cũ (ai đăng nhập cũng đăng bài được).
/// </summary>
public static class PostingPolicy
{
    public const string AdminOnlyMessage = "Bản demo trực tuyến chỉ cho quản trị viên đăng bài và tải ảnh.";

    public static bool Allows(CurrentUser user, IConfiguration config) =>
        user.IsAdmin || !config.GetValue<bool>("PostingSettings:AdminOnly");
}
