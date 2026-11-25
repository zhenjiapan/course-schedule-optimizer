# Course Planner 纯静态版

用 Next.js 编译站点，发布 out/ 内全部文件到静态网站根目录。静态托管需支持目录索引，访问 /planner/。站点从同域的 catalog.json 读取课程，后台 Web Worker 在浏览器内完成枚举、评分及复查。生成时请保持网页打开。

```sh
npm ci
npm run build
npm start
```

包含 2026–27 两学期快照，第二学期可检索 FIN2010。发布会使 catalog.json 可被访问网站的人下载。课程快照需由维护者确认可以按此方式发布。静态产物包含课表所需字段和信息提示，原始 SIS 文件留在本地。

从更新后的单服务版课程副本重新导出数据时，使用已安装该后端依赖的 Python 环境。工作目录为本站源码根目录。

```sh
COURSE_SNAPSHOT=/absolute/path/to/catalog.sqlite PYTHONPATH=/absolute/path/to/backend python scripts/export_courses.py public/catalog.json
npm run build
```

排课以每个课程组件选一个班次为单位，排除冲突并穷举可行组合。计数使用整数，偏好排序使用浮点数，接近同分时按班次标识排序，与旧版整数目标的边界同分处理可能有差异。大规模组合的速度尚待基准测试。
