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

其中 `ROS_URL` 就是 RouterOS 的地址，必要时可以带端口，例如：

```env
ROS_URL=http://10.1.1.1
ROS_URL=http://10.1.1.1:80
ROS_URL=https://10.1.1.1:443
```

完整步骤：

```bash
mkdir -p data
cp .env.example .env
# 编辑 .env，填入你的 RouterOS IP/端口和账号密码
docker compose up -d --build
```

`docker-compose.yml` 没有把路由器 IP 写死，是因为这些值从 `.env` 注入，便于不同环境复用，也避免把设备地址和密码直接提交到仓库。

如果之前已经启动过并遇到 `sqlite3.OperationalError: unable to open database file`，通常是宿主机 `./data` 目录权限不对。先删除旧容器，然后执行：

```bash
mkdir -p data
docker compose down
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
