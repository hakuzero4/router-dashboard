# hAP 流量台

给 MikroTik RouterOS 7 用的本机流量面板：WAN 实时曲线 + 内网 Top Talker。

## 打开

```bash
# 后端
./run.sh

# 前端（开发）
cd frontend && npm run dev
```

- 面板：http://10.1.1.10:5173
- API：http://10.1.1.10:8787/api/snapshot

生产可先 `cd frontend && npm run build`，然后只跑 `./run.sh`，打开 http://10.1.1.10:8787

## 路由器

REST 用户需要 `read,api,rest-api`。账号写在项目根目录 `.env`，不要提交。

## Docker

镜像默认监听 `8787`，运行时读取根目录 `.env` 中的 `ROS_URL`、`ROS_USER`、`ROS_PASSWORD`、`WAN_INTERFACE`。

```bash
cp .env.example .env
docker compose up -d --build
```

如果要手工构建镜像：

```bash
docker build \
  --build-arg NODE_VERSION=22 \
  --build-arg PYTHON_VERSION=3.12 \
  --build-arg APP_PORT=8787 \
  -t ghcr.io/hakuzero4/router-dashboard:local .
```

GitHub Actions 已提供 `.github/workflows/docker-image.yml`，会在推送 `main` 或 `v*` tag 时构建并发布 GHCR 镜像。
