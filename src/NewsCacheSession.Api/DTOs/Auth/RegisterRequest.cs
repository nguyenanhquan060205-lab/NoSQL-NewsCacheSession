using System.ComponentModel.DataAnnotations;

namespace NewsCacheSession.Api.DTOs.Auth;

public class RegisterRequest
{
    [Required]
    [MaxLength(50, ErrorMessage = "Username tối đa 50 ký tự.")]
    public string Username { get; set; } = string.Empty;

    // BCrypt chỉ dùng 72 byte đầu: hai mật khẩu dài chung 72 byte đầu sẽ cùng đăng nhập được.
    [Required]
    [MinLength(6)]
    [MaxLength(72, ErrorMessage = "Mật khẩu tối đa 72 ký tự.")]
    public string Password { get; set; } = string.Empty;
}
