# 验收记录

> 本文正文保留历史版本说明。当前版本、数据与启动方法见 [Streamlit v3.2.0 使用与维护](streamlit-v3.2.0.md)。

| 检查 | 结果 |
|---|---|
| 原目录清单、SHA-256、Git | 401 个文件系统条目，两次 JSON 基线逐字节相同，Git 为干净的 main...origin/main |
| SQLite 快照 | integrity_check 返回 ok，foreign_key_check 返回零行 |
| 快照数量 | 499 courses、757 course_components、255 course_attributes、1,700 sections、1,742 meetings、2,156 meeting_days、825 instructors、2,508 meeting_instructors、499 sources、11 collection_runs |
| 学期 Section 数量 | Term 1 为 1,476，Term 2 为 224 |
| 隔离副本旧算法测试 | 17 通过，含真实学期数据与日期 |
| 新目录算法测试 | 12 通过，含穷举对照、硬约束、评分、独立验证及超时状态 |
| 真实 SQLite 样例 | 六门课、避开早课、星期五评分 0，返回三套 95 分且验证通过的方案 |
| npm 安装 | npm ci --offline 成功 |
| Next.js 构建 | Webpack 生产构建通过，生成首页、Planner、About |
| TypeScript | strict 类型检查通过 |
| FastAPI 运行、Alembic、PostgreSQL 事务导入、真实 API | 未验证。当前环境无 Docker 或 PostgreSQL，PyPI 域名无法解析 |
| 浏览器端到端与移动设备 | 未验证 |

Git 基线使用 --no-optional-locks，涵盖原目录 .git 和 SQLite 文件在内的全部常规文件，也记录目录项及符号链接目标。只在独立目录内执行测试和数据库检查。Git 忽略的 private/ 含原始快照副本、两份哈希清单和旧版真实样例对照记录。

前端首次 Turbopack 构建在沙箱内部端口绑定时失败，项目生产构建命令改为 Next.js 的 Webpack 模式后通过。PostgreSQL 集成测试已经写入 backend/tests/test_api_postgres.py，导入数据后运行。完成真实联调前，仍需确认 PostgreSQL 逐表导入、两个学期的查询、实际 API、浏览器手动换班与导出。
