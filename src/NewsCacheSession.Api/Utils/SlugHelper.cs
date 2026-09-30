using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace NewsCacheSession.Api.Utils;

/// <summary>
/// Sinh slug thân thiện URL từ tiêu đề tiếng Việt.
/// Dùng chung cho bài viết và chuyên mục để hai nơi không sinh ra slug khác kiểu nhau.
/// </summary>
public static class SlugHelper
{
    private static readonly Regex NonAlphanumeric = new("[^a-z0-9]+", RegexOptions.Compiled);

    /// <summary>
    /// "Tin nóng hôm nay!" → "tin-nong-hom-nay".
    /// </summary>
    public static string ToSlug(string text, string fallback = "bai-viet")
    {
        // Normalize(FormD) tách chữ và dấu thành 2 ký tự rồi ta bỏ ký tự dấu đi.
        // Riêng 'đ' phải thay tay: nó là một ký tự Unicode độc lập, KHÔNG phải 'd' + dấu,
        // nên FormD không tách được và nó sẽ bị regex loại mất.
        var normalized = text.Trim().ToLowerInvariant()
            .Replace('đ', 'd')
            .Normalize(NormalizationForm.FormD);

        var sb = new StringBuilder(normalized.Length);
        foreach (var c in normalized)
        {
            if (CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
                sb.Append(c);
        }

        var slug = NonAlphanumeric.Replace(sb.ToString(), "-").Trim('-');
        return string.IsNullOrEmpty(slug) ? fallback : slug;
    }
}
