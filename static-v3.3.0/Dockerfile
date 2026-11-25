FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY next.config.ts next-env.d.ts tsconfig.json postcss.config.mjs ./
COPY app ./app
COPY features ./features
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/out /site
COPY --chmod=444 private/catalog.sqlite /data/catalog.sqlite
USER 65534:65534
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.site:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
