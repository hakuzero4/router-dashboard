ARG NODE_VERSION=22
ARG PYTHON_VERSION=3.12

FROM node:${NODE_VERSION}-bookworm-slim AS frontend-build
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM python:${PYTHON_VERSION}-slim AS runtime

ARG APP_PORT=8787
ARG APP_USER=app
ARG APP_UID=10001
ARG APP_GID=10001
ARG BUILD_DATE=unknown
ARG VCS_REF=unknown
ARG VERSION=dev

LABEL org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/hakuzero4/router-dashboard"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    APP_PORT=${APP_PORT}

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
RUN mkdir -p /app/data

VOLUME ["/app/data"]
EXPOSE ${APP_PORT}

CMD ["sh", "-c", "uvicorn main:app --app-dir /app/backend --host 0.0.0.0 --port ${APP_PORT}"]
