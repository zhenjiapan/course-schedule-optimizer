# LLM-Assisted Personalized Course Selection & Timetable Optimization

CUHK–Shenzhen 选课和排课工具。Next.js 提供选课和周课表界面，FastAPI 查询 PostgreSQL，独立 Python 进程运行 V4 CP-SAT 求解器。本阶段涵盖排课功能，LLM 是后续开发方向。

## 本地启动

需要 Node.js 22+、Python 3.11+ 和 Docker Compose，或一套可连接的 PostgreSQL 17。以下命令从项目根目录运行。

```bash
cp .env.example .env
set -a
source .env
set +a
docker compose up -d --wait db
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/python scripts/migrate_sqlite_to_postgres.py private/sis-2026-11-22.sqlite
```

首次导入需要把有权使用的 SQLite 快照放入 `private/`。本机交付目录包含源快照的副本。11 月 22 日更新后的课程与配对数据在 `private/sis-2026-11-22.sqlite`。该目录被 Git 忽略，且启动后的服务仅读 PostgreSQL。导入会在一个事务中按依赖顺序写入课程表与可用的班次配对表，逐行校验并在失败时回滚。相同快照可重复导入，主键冲突且内容不同会中止。已有额外记录会保留。

两个终端分别运行：

```bash
# 终端 A，项目根目录。若使用自定义 .env，先按上面的方法加载
.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

```bash
# 终端 B，项目根目录
cd frontend
npm ci
npm run dev
```

访问 [Planner](http://localhost:3000/planner) 和 [OpenAPI](http://127.0.0.1:8000/docs)。变更 API 地址时，在运行 Next.js 的环境设置 `PLANNER_API_URL`，生产构建也须包含该变量。使用现有 PostgreSQL 时可跳过 Compose，并将 `DATABASE_URL` 指向目标数据库。

## 测试

```bash
PYTHONPATH=backend .venv/bin/pytest backend/tests
PYTHONPATH=backend RUN_POSTGRES_TESTS=1 .venv/bin/pytest backend/tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## V4 求解和验证

网页 `/planner` 使用 `POST /api/v4/optimize` 生成最多三张课表，换班后使用 `POST /api/v4/validate` 独立检查。课程由用户先选定，求解器为每个必需组件选一个班次。评分等级为 1–5，3 表示中立。输入字段见 `GET /api/v4/preferences/schema`。搜索时间保护额度由 `V4_MAX_TIMEOUT_SECONDS` 配置，默认 180 秒，前端从设置接口获取当前额度。若手动更改额度，启动前端和后端时请使用同一个环境变量值。Next.js 转发时限在求解额度上额外保留 15 秒，用于等待并传回响应。

生成期间，前端轮询 `GET /api/v4/progress/{job_id}` 显示 CP-SAT 找到新解或结束一轮搜索时报告的累计分支数；求解结束后响应还包含各阶段搜索统计。该计数会按求解器快照刷新，可能跳跃。

- 支持教师、星期、时间、日内结构、周内结构五类损失。教师使用当前目录中的姓名键。授课比例缺失时，同一节的教师等权，未知教师按中立处理。
- 星期和时段的效用范围在原始硬可行域上求证并固定。排序采用有理数的等价整数目标。整数范围不足时通过分段进位保持精确，仍受请求限时约束。
- `optimal` 表示规定顺序的前三名都已证明，或剩余解已耗尽。`feasible_unproven` 返回通过独立检查的可行结果与已证明的名次数。`infeasible_proven` 和 `timeout_no_feasible` 分别表示已证无解和限时内未找到已验证计划。
- 网页按六个模块提供 V4 参数表单。启用周规则时，在「课表结构」中勾选经校历核对的完整教学周。日评价日期缺省为候选课程授课日期的并集，并会提示该口径。
- PostgreSQL 的 `meeting_occurrence_overrides` 可按原始会议 ID 提供权威日期数组。缺少覆盖记录的课程使用目录里的星期和日期范围。当前 SIS 快照没有额外的逐日覆盖数据。新增数据库需要运行至 Alembic 最新版本。

### 本机已导入的 V4 数据

本机 PostgreSQL 的 `planner_v4` schema 导入了 11 月 22 日快照。保留同一个数据库服务器时，用以下命令启动后端：

```bash
DATABASE_URL='postgresql+psycopg://planner:planner@127.0.0.1:55432/planner?options=-csearch_path%3Dplanner_v4' \
  .venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8014
```

另一终端从项目根目录运行：

```bash
PLANNER_API_URL=http://127.0.0.1:8014 npm --prefix frontend run build
PLANNER_API_URL=http://127.0.0.1:8014 npm --prefix frontend run start -- --hostname 127.0.0.1 --port 3140
```

打开 http://127.0.0.1:3140/planner。真实数据回归测试需要导入有已核实配对的新版快照，并设置 `RUN_POSTGRES_TESTS=1` 和上述数据库连接。

详见 [审计和架构](docs/architecture.md)、[部署](docs/deployment.md)、[验收记录](docs/verification.md) 和 [优化算法修改日志](docs/optimization-changelog.md)。
