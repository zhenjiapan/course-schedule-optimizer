# Course Schedule Optimizer

**当前版本 v3.2.0（Streamlit）。** 应用在 `streamlit-v3.2.0/`，全栈版在 `archive/v3.1.0/`。

## 本地启动

推荐 Python 3.12 或 3.13。从仓库根目录运行：

```bash
cd streamlit-v3.2.0
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

打开 [课表规划](http://127.0.0.1:8501)。默认使用随本机版本保存的 FIN2010 SQLite 快照。可用 `COURSE_SNAPSHOT` 指定另一个兼容快照。

- [使用、搜索与数据说明](docs/streamlit-v3.2.0.md)
- [版本变更](CHANGELOG.md)
- [原 README 与历史入口](docs/legacy-readme.md)
- [v3.1.0 归档说明](archive/v3.1.0/ARCHIVE.md)

## 仓库目录

- `streamlit-v3.2.0/`：当前 Streamlit 应用，从这里运行 `app.py`。
- `archive/v3.1.0/`：v3.1.0 全栈版归档。
- `archive/legacy-root/`：原根目录的旧程序、数据、脚本、测试和 Docker 配置。
- `docs/`：使用、数据和部署说明。
