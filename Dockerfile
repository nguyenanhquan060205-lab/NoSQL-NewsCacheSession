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

# Image aspnet:8.0 mặc định nghe 8080 và có sẵn user không phải root tên "app".
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
USER app
ENTRYPOINT ["dotnet", "NewsCacheSession.Api.dll"]
