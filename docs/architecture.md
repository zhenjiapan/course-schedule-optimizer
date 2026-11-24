# 原项目审计与新系统架构

> 本文正文保留历史版本说明。当前版本、数据与启动方法见 [Streamlit v3.2.0 使用与维护](streamlit-v3.2.0.md)。

旧版入口负责选学期和课程、设置偏好、调用求解器和手动换班。它支持至少 12 学分，代码没有学分上限。08:30 早课支持不设偏好、少排、多排和禁止。星期偏好及已选课程的讲师偏好使用 0–5。星期禁排和每周重复的时段禁排是硬约束，重复时段合并。旧页面没有一次性日历日期禁排。搜索时间默认 15 秒，允许 1–120 秒。核心接受缺失组件豁免，旧页面未开放此开关。

来源 SQLite 有 courses、course_components、course_attributes、sections、meetings、meeting_days、instructors、meeting_instructors、sources 与 collection_runs。适配器按学期筛选 Section，将同一星期、时间和日期范围的原始 Meeting 合并，保留多个房间与真实讲师名称，过滤占位讲师。缺少可用时间的 Section 会显示警告并退出候选。CHI1000 保留 Lecture-only 特例。实际上课日期由周几与首末日期共同确定。

优化器先生成每个必修课程组件的候选组，按候选组大小、课程和组件排序。组内按得分再按 Section code 排序。回溯检查实际日期冲突，以剩余每组最大贡献构造上界，保留最高分三组。配置后的早课、星期、讲师类别取等权平均。早课与星期按实际学期会议次数计。未评分讲师取中性 2.5，没有任何活跃类别时基准分为 50。验证器按日期独立展开并检查学分、组件、硬限制及冲突。推荐流程也经过独立验证。SIS 先修条件、课程容量以及不同组件 Section 的绑定无法从现有核心验证。

旧版周视图按教学周显示实际发生的会议，输出周 CSV 和整学期 JSON。新版保留相同输出范围。周图按分钟定位，附详细列表。整学期 JSON 含输入、Section、状态和验证结果。旧版 SQLite 文件哈希不作为新版导出字段。

## 代码入口

- `frontend/app/` 使用 Next.js App Router 定义首页、Planner、About。Next.js 用 React 渲染页面，也负责路由、构建与转发 API。
- `frontend/features/` 存放 React 交互组件、课表和 API 客户端。TypeScript 检查组件输入、状态和接口响应类型。Tailwind 提供样式构建和基础规则，页面采用局部 CSS 样式。
- `backend/app/main.py` 由 FastAPI 接收 JSON，Pydantic 校验类型与范围，再交给数据库和算法。运行后可以通过 `/docs` 查看 OpenAPI。
- `backend/app/db.py` 建立连接池。`repository.py` 使用 SQLAlchemy 2.x Core 与 Psycopg 读取 PostgreSQL，输出普通 Python 数据对象。Alembic 初始化关系表，后续结构改动添加新版本。
- `backend/app/optimization/` 保留优化器与独立验证器。改动仅为包内导入和从 domain model 移除 SQLite 读取。PostgreSQL 读取端保留旧数据转换规则。
- `scripts/` 存放事务式导入工具与原目录完整性核验工具。

## API

| Method | Path | 作用 |
|---|---|---|
| GET | /api/health | 检查数据库连接 |
| GET | /api/courses | 按 term 获取目录 |
| GET | /api/courses/{code} | 按 term 查看可规划 Section、讲师和会议 |
| GET | /api/preferences/schema | 查看求解请求 JSON Schema |
| POST | /api/optimize | 输入 term、codes、preferences 和 timeout，返回状态、搜索指标和已验证方案 |
| POST | /api/validate | 输入 term、codes、preferences 和 selections，返回验证报告与通过验证的会议 |

未来可用独立的用户、课表、课表 Section、偏好版本和学期数据关系实现保存功能。LLM 可以先生成供学生确认的结构化偏好，再复用现有 Pydantic 规范与独立验证流程。推理、数据库、排课分别保有清晰的数据边界。
