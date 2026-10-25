FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN npm run build

FROM python:3.13-slim
ARG BUILD_ARCH
ARG BUILD_VERSION=1.0.0
LABEL io.hass.name="Was essen wir?" io.hass.description="Familien-Essensplan" io.hass.type="addon" io.hass.arch="${BUILD_ARCH}" io.hass.version="${BUILD_VERSION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_PATH=/data/essen.sqlite3 STATIC_DIR=/app/static TZ=Europe/Berlin
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade pip==26.2.1 && pip install --no-cache-dir -r requirements.txt && groupadd --gid 10001 essen && useradd --uid 10001 --gid essen --no-create-home essen && mkdir /data
COPY backend/*.py backend/rules.json ./backend/
COPY --from=frontend /build/dist/ ./static/
COPY run.py /app/run.py
EXPOSE 8000
CMD ["python", "/app/run.py"]
