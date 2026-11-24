# 服务器部署

1. 准备独立数据库、应用凭据和备份。用 `DATABASE_URL` 配置后端，用有迁移权限的账号运行 Alembic。确认课程信息授权后再导入到获准的环境。
2. 安装后端依赖，运行 `uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`。用进程管理器配置开机启动、重启、日志保留和资源配额。
3. 在 frontend 运行 `npm ci`，配置 `PLANNER_API_URL`，运行 `npm run build` 与 `npm start -- --hostname 127.0.0.1`。构建与运行阶段使用一致的上游地址。
4. 使用 Caddy 或 Nginx 监听公网 443 并配置 HTTPS，反向代理到 Next.js 3000。FastAPI 和 PostgreSQL 留在私网。代理、负载均衡器及宿主平台的超时需要覆盖 120 秒搜索预算和处理余量，或者将生产预算下调。
5. 部署验收检查 HTTPS、`/api/health`、课程查询、求解、手动校验和导出。重跑导入以验证幂等。Compose 示例用于本地数据库，卷 planner-data 在容器重启间保留数据。

当前每个 API 进程有两个求解子进程和两个槽位。饱和时返回 503。算法区分超时有解和超时未找到解。外层 deadline 返回 504，正在运行的子任务持有槽位直至退出。多实例的总并发与进程数量相乘。未来需要集中队列、独立 worker、任务取消和全局配额时，可复用现有 optimize_job。发布前按真实课程组合测量延迟、内存和队列行为。
