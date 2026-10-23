namespace NewsCacheSession.Api.Services;

public sealed record UploadedImage(string Url, string PublicId);

public interface IImageStorageService
{
    Task<UploadedImage> UploadAsync(IFormFile file, CancellationToken cancellationToken = default);

    Task DeleteAsync(string publicId, CancellationToken cancellationToken = default);
}
