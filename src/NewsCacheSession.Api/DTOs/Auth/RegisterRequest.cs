using System.ComponentModel.DataAnnotations;

namespace NewsCacheSession.Api.DTOs.Auth;

public class RegisterRequest
{
    [Required]
    public string Username { get; set; } = string.Empty;

    [Required]
    [MinLength(6)]
    public string Password { get; set; } = string.Empty;
}
