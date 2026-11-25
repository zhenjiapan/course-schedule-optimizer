# Course Schedule Optimizer v3.2.0

Streamlit 版使用 v3.1.0 的 V4 CP-SAT 求解和独立校验。课程数据从只读 SQLite 快照加载，适合直接在本机运行。全栈版归档位于同级目录下的 archive/v3.1.0。

## 启动

从本目录运行，推荐 Python 3.12 或 3.13：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

默认读取 private/sis-2026-11-24-fin2010.sqlite。也可用 COURSE_SNAPSHOT 指定快照绝对路径。远程部署时，将有权使用的快照单独配置到服务端。

## 使用

选择学期和课程，在表单内设置硬约束、偏好与权重后开始搜索。进度每秒显示，前三个候选每十秒刷新。完整搜索返回前三名、合格组合总数和分支总数。可查看任一教学周、调整同组件班次并独立校验，或导出 CSV 与 JSON。

详细规则、数据口径及排错见 [使用与维护](USAGE.md)。
