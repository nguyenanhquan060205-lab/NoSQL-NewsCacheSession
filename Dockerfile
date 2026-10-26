# Image API .NET 8 cho Render (Docker) — xem docs/huong-dan-deploy.md.
# Build: docker build -t news-api .
# Chạy:  docker run -p 8080:8080 -e MongoSettings__ConnectionString=... -e RedisSettings__ConnectionString=... news-api

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Restore riêng theo file .csproj để layer NuGet được cache khi chỉ đổi code.
COPY src/NewsCacheSession.Api/NewsCacheSession.Api.csproj src/NewsCacheSession.Api/
RUN dotnet restore src/NewsCacheSession.Api/NewsCacheSession.Api.csproj

COPY src/NewsCacheSession.Api/ src/NewsCacheSession.Api/
RUN dotnet publish src/NewsCacheSession.Api/NewsCacheSession.Api.csproj -c Release -o /app --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app .

# Nghe ở 0.0.0.0 (IPv4). Mặc định của image aspnet:8.0 là [::]:8080 — chỉ mở socket IPv6, Render
# không dò thấy cổng nên deploy treo 15 phút rồi "Timed Out". Bỏ HTTP_PORTS để Kestrel khỏi cảnh báo ghi đè.
ENV ASPNETCORE_HTTP_PORTS= \
    ASPNETCORE_URLS=http://0.0.0.0:8080
EXPOSE 8080
# Image có sẵn user không phải root tên "app".
USER app
ENTRYPOINT ["dotnet", "NewsCacheSession.Api.dll"]
