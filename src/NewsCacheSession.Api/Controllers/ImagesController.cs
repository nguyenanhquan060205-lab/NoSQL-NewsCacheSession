using Microsoft.AspNetCore.Mvc;
using NewsCacheSession.Api.Services;

namespace NewsCacheSession.Api.Controllers;

[ApiController]
[Route("api/images")]
public sealed class ImagesController : ControllerBase
{
    private const long MaxFileSize = 5 * 1024 * 1024;
    private readonly ICurrentUserService _currentUser;
    private readonly IImageStorageService _imageStorage;

    public ImagesController(ICurrentUserService currentUser, IImageStorageService imageStorage)
    {
        _currentUser = currentUser;
        _imageStorage = imageStorage;
    }

    [HttpPost]
    [Consumes("multipart/form-data")]
    [RequestSizeLimit(MaxFileSize)]
    public async Task<IActionResult> Upload(IFormFile? file, CancellationToken cancellationToken)
    {
        if (await _currentUser.GetAsync(HttpContext) == null)
            return Unauthorized(new { message = "Bạn cần đăng nhập để tải ảnh lên." });

        if (file == null)
            return BadRequest(new { message = "Vui lòng chọn một ảnh." });

        try
        {
            var uploaded = await _imageStorage.UploadAsync(file, cancellationToken);
            return Ok(new { imageUrl = uploaded.Url, imagePublicId = uploaded.PublicId });
        }
        catch (InvalidDataException exception)
        {
            return BadRequest(new { message = exception.Message });
        }
        catch (InvalidOperationException exception)
        {
            return StatusCode(StatusCodes.Status503ServiceUnavailable, new { message = exception.Message });
        }
    }
}
