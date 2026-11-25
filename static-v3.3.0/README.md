# Course Planner v3.3.0 单服务部署

Next.js 在构建时导出页面，FastAPI 在同一域名和端口提供页面与 /api 接口。运行时使用镜像内的只读 SQLite 课程目录。排课沿用 V4 优化器、独立检验和评分解释。搜索每秒轮询一次进度，每 10 秒刷新候选前三，完成后显示合格课表总数和求解器分支数。

## 本机运行

在此目录执行以下命令，然后打开 http://127.0.0.1:3300/planner/ 。

```bash
docker build -t course-planner:3.3.0 .
docker run --rm -p 127.0.0.1:3300:8000 course-planner:3.3.0
```

## CloudBase 云托管

在 steven-timetable 环境选择「云函数 / 托管 → 云托管 → 创建服务 → 本地代码」，上传根目录包含 Dockerfile 的部署 ZIP。服务端口为 8000，健康检查路径可设为 /api/health。启用 Web 访问并将实例数上限设为 1，避免发起求解和查询进度落到不同实例。重启会中断进行中的任务。客户端会轮询短请求，完整求解在服务进程内继续。

部署成功后，使用云托管服务的新 HTTPS 域名，访问 /planner/，选择 2026–27 第二学期搜索 FIN2010 并生成课表。数据库随服务发布，部署表单的环境变量留空。

## 更新课程快照

执行下列命令生成新文件，确认后把它替换为 private/catalog.sqlite 并重新构建。

```bash
python3 scripts/export_catalog.py /path/to/sis.sqlite private/catalog-new.sqlite
```

导出只保留课程、班次、教师和会议等排课字段。数据库路径在网站目录之外，仅由 API 访问。部署包与镜像携带导出的目录，请通过所选 CloudBase 环境的本地代码上传或使用私有镜像仓库。原始快照和私有目录不应提交到公开仓库。

本地已核对静态构建、同域路由、只读限制，以及 FIN2010 的完整求解和独立验证。Docker 镜像构建、跨进程进度和腾讯云部署需要在可运行容器的环境验收。
