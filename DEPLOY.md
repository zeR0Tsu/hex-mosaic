# 部署文档

本项目是纯静态单页应用（`index.html` 零依赖），部署只需把文件放到任意静态服务器。

## 1. 本地预览

不要直接双击打开就够用；若需要 `http://` 环境（例如测试剪贴板、跨域），用脚本起本地服务器：

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\preview.ps1
```

```bash
# macOS / Linux
bash scripts/preview.sh
```

默认地址 http://localhost:8080 ，按 `Ctrl+C` 停止。

## 2. 构建产物

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

```bash
bash scripts/build.sh
```

产物输出到 `dist/`，只包含运行所需的 `index.html`。把这个目录整体上传即可。

## 3. GitHub Pages（推荐）

已内置工作流 [.github/workflows/pages.yml](.github/workflows/pages.yml)：推送到 `main` 即自动构建并发布。

### 首次启用

1. 打开仓库 `Settings → Pages`
2. **Source** 选择 **GitHub Actions**
3. 推送到 `main`，或到 `Actions → Deploy to GitHub Pages → Run workflow` 手动触发

### 部署脚本

```powershell
# Windows：提交当前改动并推送，触发 Pages 部署
powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 "更新说明"
```

```bash
# macOS / Linux
bash scripts/deploy.sh "更新说明"
```

脚本会依次执行：构建 → `git add -A` → 提交 → 推送 `main` → 输出 Pages 地址。

### 注意

- **私有仓库启用 Pages 需要 GitHub Pro / Team 及以上套餐**。免费账号的私有仓库无法发布 Pages，可改用下面的「自托管」，或把仓库改为 public。
- 首次部署后站点地址为 `https://<用户名>.github.io/<仓库名>/`。

## 4. 自托管

把 `dist/` 内容拷到服务器网站根目录即可。Nginx 示例：

```nginx
server {
    listen 80;
    server_name hex.example.com;
    root /var/www/hex-mosaic;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

由于是单文件应用，也可直接放到任意对象存储 / CDN（OSS、S3、Cloudflare Pages、Vercel 等），无需构建命令，指定静态目录为 `dist/`。

## 5. 命令行版环境

```bash
python -m pip install pillow
python hex_dot_art.py input.png -o out.png
```

要求 Python 3.8+。无需其他依赖。
