using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace NewsCacheSession.Api.Services;

public sealed class CloudinarySettings
{
    public string CloudName { get; set; } = string.Empty;
    public string ApiKey { get; set; } = string.Empty;
    public string ApiSecret { get; set; } = string.Empty;
}

public sealed class CloudinaryImageStorageService : IImageStorageService
{
    private const long MaxFileSize = 5 * 1024 * 1024;
    private static readonly IReadOnlyDictionary<string, string> AllowedContentTypes =
        new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            ["image/jpeg"] = "jpg",
            ["image/png"] = "png",
            ["image/webp"] = "webp",
        };

    // HttpClient mặc định chờ 100 giây; Cloudinary treo thì request sửa/xóa bài và tải ảnh treo theo.
    private static readonly TimeSpan RequestTimeout = TimeSpan.FromSeconds(15);

    private readonly HttpClient _httpClient;
    private readonly CloudinarySettings _settings;

    public CloudinaryImageStorageService(HttpClient httpClient, IOptions<CloudinarySettings> options)
    {
        _httpClient = httpClient;
        _httpClient.Timeout = RequestTimeout;
        _settings = options.Value;
    }

    public async Task<UploadedImage> UploadAsync(IFormFile file, CancellationToken cancellationToken = default)
    {
        ValidateSettings();
        var extension = ValidateFileMetadata(file);
        await ValidateSignatureAsync(file, extension, cancellationToken);
        var publicId = $"posts/{Guid.NewGuid():N}";
        var timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(CultureInfo.InvariantCulture);
        var parameters = new Dictionary<string, string>
        {
            ["public_id"] = publicId,
            ["timestamp"] = timestamp,
        };

        await using var stream = file.OpenReadStream();
        using var multipart = new MultipartFormDataContent();
        using var streamContent = new StreamContent(stream);
        streamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(file.ContentType);
        multipart.Add(streamContent, "file", $"upload.{extension}");
        multipart.Add(new StringContent(_settings.ApiKey), "api_key");
        multipart.Add(new StringContent(timestamp), "timestamp");
        multipart.Add(new StringContent(publicId), "public_id");
        multipart.Add(new StringContent(Sign(parameters)), "signature");

        using var response = await _httpClient.PostAsync(
            $"https://api.cloudinary.com/v1_1/{Uri.EscapeDataString(_settings.CloudName)}/image/upload",
            multipart,
            cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"Cloudinary upload thất bại: {(int)response.StatusCode}.");

        using var document = JsonDocument.Parse(body);
        var url = document.RootElement.GetProperty("secure_url").GetString();
        var responsePublicId = document.RootElement.GetProperty("public_id").GetString();
        if (string.IsNullOrWhiteSpace(url) || string.IsNullOrWhiteSpace(responsePublicId))
            throw new InvalidOperationException("Cloudinary trả về dữ liệu ảnh không hợp lệ.");

        return new UploadedImage(url, responsePublicId);
    }

    public async Task DeleteAsync(string publicId, CancellationToken cancellationToken = default)
    {
        ValidateSettings();
        var timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString(CultureInfo.InvariantCulture);
        var parameters = new Dictionary<string, string>
        {
            ["invalidate"] = "true",
            ["public_id"] = publicId,
            ["timestamp"] = timestamp,
            ["type"] = "upload",
        };

        using var form = new FormUrlEncodedContent(new Dictionary<string, string>(parameters)
        {
            ["api_key"] = _settings.ApiKey,
            ["signature"] = Sign(parameters),
        });
        using var response = await _httpClient.PostAsync(
            $"https://api.cloudinary.com/v1_1/{Uri.EscapeDataString(_settings.CloudName)}/image/destroy",
            form,
            cancellationToken);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"Cloudinary xóa ảnh thất bại: {(int)response.StatusCode}.");
    }

    private string Sign(IReadOnlyDictionary<string, string> parameters)
    {
        var canonical = string.Join('&', parameters
            .Where(pair => !string.IsNullOrWhiteSpace(pair.Value))
            .OrderBy(pair => pair.Key, StringComparer.Ordinal)
            .Select(pair => $"{pair.Key}={pair.Value}"));
        var bytes = SHA1.HashData(Encoding.UTF8.GetBytes(canonical + _settings.ApiSecret));
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }

    private void ValidateSettings()
    {
        if (string.IsNullOrWhiteSpace(_settings.CloudName) ||
            string.IsNullOrWhiteSpace(_settings.ApiKey) ||
            string.IsNullOrWhiteSpace(_settings.ApiSecret))
            throw new InvalidOperationException("Cloudinary chưa được cấu hình.");
    }

    private static string ValidateFileMetadata(IFormFile file)
    {
        if (file == null || file.Length == 0)
            throw new InvalidDataException("Vui lòng chọn một ảnh.");
        if (file.Length > MaxFileSize)
            throw new InvalidDataException("Ảnh không được vượt quá 5 MB.");
        if (!AllowedContentTypes.TryGetValue(file.ContentType, out var extension))
            throw new InvalidDataException("Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.");
        return extension;
    }

    private static async Task ValidateSignatureAsync(
        IFormFile file,
        string extension,
        CancellationToken cancellationToken)
    {
        var header = new byte[12];
        await using var stream = file.OpenReadStream();
        var read = await stream.ReadAsync(header.AsMemory(), cancellationToken);
        var valid = extension switch
        {
            "jpg" => read >= 3 && header[0] == 0xFF && header[1] == 0xD8 && header[2] == 0xFF,
            "png" => read >= 8 &&
                     header.AsSpan(0, 8).SequenceEqual(new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A }),
            "webp" => read >= 12 &&
                      header.AsSpan(0, 4).SequenceEqual("RIFF"u8) &&
                      header.AsSpan(8, 4).SequenceEqual("WEBP"u8),
            _ => false,
        };

        if (!valid)
            throw new InvalidDataException("Nội dung file không khớp định dạng ảnh đã chọn.");
    }
}
