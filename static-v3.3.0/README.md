# Course Planner v3.3.0

基于 v3.1.0 的 Next.js 界面和排课流程。首页、规划器与关于页导出为静态文件。Streamlit v3.2.0 归档在同级项目区的 archive/v3.2.0。

## 构建与本地预览

```bash
npm ci
npm run build
npm start
```

打开 http://127.0.0.1:3300/ 。发布时，把 out/ 内的全部文件放在静态站点的域名根目录，并启用目录索引 index.html。

## 连接排课接口

课程查询、排课、进度和校验继续使用 v3.1.0 FastAPI 和其已导入数据的 PostgreSQL。推荐用同域反向代理，把 /api/ 原样转发给该后端，并把其他路径交给 out/ 中的静态文件。

如果静态网站和 API 使用不同域名，在构建前设置 NEXT_PUBLIC_PLANNER_API_URL 为后端的 HTTPS 源地址（包括协议与域名，不加 /api）。后端或其反代需允许静态网站的 CORS 源，以及 POST 使用的 Content-Type 和 X-Search-Mode 请求头。改地址后重新构建。

纯静态预览可打开所有页面。课程列表和求解需要可用的 API。导出目录不会打包课程数据库。
