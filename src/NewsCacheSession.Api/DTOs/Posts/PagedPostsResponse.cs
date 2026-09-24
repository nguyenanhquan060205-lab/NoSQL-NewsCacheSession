namespace NewsCacheSession.Api.DTOs.Posts;

public class PagedPostsResponse
{
    public List<PostResponse> Items { get; set; } = new();
    public int Page { get; set; }
    public int PageSize { get; set; }
    public long TotalItems { get; set; }
    public int TotalPages { get; set; }
}
