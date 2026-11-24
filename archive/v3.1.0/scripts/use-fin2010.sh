#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
compose=(docker compose -p course-schedule-optimizer-next -f docker-compose.yml -f compose.web.yml -f compose.fin2010.yml)
db="$("${compose[@]}" ps -q db)"
if [[ -z "$db" ]]; then
  echo '未找到 course-schedule-optimizer-next 正在运行的数据库；请先确认 55432 所属容器。' >&2
  exit 1
fi
"${compose[@]}" exec -T db psql -U planner -d planner -v ON_ERROR_STOP=1 -c 'CREATE SCHEMA IF NOT EXISTS planner_fin2010_20261124'
db_password="$("${compose[@]}" exec -T db printenv POSTGRES_PASSWORD)"
export PLANNER_FIN2010_PASSWORD="$(.venv/bin/python -c 'import sys; from urllib.parse import quote; print(quote(sys.stdin.read().rstrip("\n"),safe=""))' <<< "$db_password")"
export DATABASE_URL="postgresql+psycopg://planner:${PLANNER_FIN2010_PASSWORD}@127.0.0.1:55432/planner?options=-csearch_path%3Dplanner_fin2010_20261124"
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/python scripts/migrate_sqlite_to_postgres.py private/sis-2026-11-24-fin2010.sqlite
"${compose[@]}" up -d --no-deps --build --wait backend
"${compose[@]}" up -d --no-deps --build --wait frontend
curl -fsS 'http://127.0.0.1:3100/api/courses/FIN2010?term=2026-27%20Term%202' | .venv/bin/python -c 'import json,sys; d=json.load(sys.stdin); print("FIN2010 第二学期班次数：",len(d["sections"])); assert len(d["sections"]) == 24'
