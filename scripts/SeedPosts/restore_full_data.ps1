param(
    [switch]$ConfirmReplace
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmReplace) {
    throw "Lệnh này thay thế posts/categories trong MongoDB và xóa cache Redis. Chạy lại với -ConfirmReplace."
}

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDirectory "../..")
$postsPath = Join-Path $scriptDirectory "data/newsdb-posts.json.gz"
$categoriesPath = Join-Path $scriptDirectory "data/newsdb-categories.json.gz"
$containerPostsPath = "/tmp/newsdb-posts.json.gz"
$containerCategoriesPath = "/tmp/newsdb-categories.json.gz"

if (-not (Test-Path -LiteralPath $postsPath)) {
    throw "Không tìm thấy file dữ liệu: $postsPath"
}
if (-not (Test-Path -LiteralPath $categoriesPath)) {
    throw "Không tìm thấy file dữ liệu: $categoriesPath"
}

Push-Location $projectRoot
try {
    docker compose up -d mongo redis
    if ($LASTEXITCODE -ne 0) { throw "Không khởi động được MongoDB/Redis." }

    docker cp $postsPath "news-mongo:$containerPostsPath"
    if ($LASTEXITCODE -ne 0) { throw "Không sao chép được dữ liệu posts vào MongoDB container." }

    docker cp $categoriesPath "news-mongo:$containerCategoriesPath"
    if ($LASTEXITCODE -ne 0) { throw "Không sao chép được dữ liệu categories vào MongoDB container." }

    # Ghi MongoDB trước. Hai file chỉ chứa posts và categories, không chứa users.
    docker exec news-mongo sh -lc `
        "gzip -dc '$containerCategoriesPath' | mongoimport --db newsdb --collection categories --drop"
    if ($LASTEXITCODE -ne 0) { throw "Khôi phục categories thất bại." }

    docker exec news-mongo sh -lc `
        "gzip -dc '$containerPostsPath' | mongoimport --db newsdb --collection posts --drop"
    if ($LASTEXITCODE -ne 0) { throw "Khôi phục posts thất bại." }

    # Chỉ vô hiệu hóa cache sau khi MongoDB đã khôi phục thành công.
    docker exec news-redis redis-cli FLUSHDB
    if ($LASTEXITCODE -ne 0) { throw "MongoDB đã khôi phục nhưng không xóa được cache Redis." }

    docker exec news-mongo mongosh --quiet newsdb --eval `
        'JSON.stringify({posts:db.posts.countDocuments({}),active:db.posts.countDocuments({isDeleted:false}),deleted:db.posts.countDocuments({isDeleted:true}),categories:db.categories.countDocuments({})})'
    if ($LASTEXITCODE -ne 0) { throw "Không xác minh được dữ liệu sau khi khôi phục." }
}
finally {
    Pop-Location
}
