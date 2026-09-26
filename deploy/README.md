# H-13 联合部署：AutoForceAI + Genesis_CRM

**状态：部署工件，不等于生产验收。** H-13 验收还需在专用隔离主机/正式域名上验证新卷从零启动、HTTPS、两端登录、线索交接、报价 E2E、两库备份恢复。本仓 `codex/production-compose` 基于 Genesis_CRM 的 `codex/docker-runtime`（先合并 Genesis PR，再处理本 PR）。不要把本手册的示例密钥作为真实凭证。所有操作在持有数据卷快照和经审批维护窗口的主机上执行；禁止直接在生产执行破坏性 downgrade、清库或演练 restore。

## 前置与环境

- 两仓仓库并列放置：`AutoForceAI/` 与 `Genesis_CRM/`；分别从已审核合入的主线检出经过验证的 commit。`deploy/compose.yaml` 以 `../../Genesis_CRM/server` 和 `../../Genesis_CRM/web` 为只读构建上下文；发布时记录**两个 commit** 并保留对应构建镜像。Docker Compose v2、Docker Engine、可信 DNS、80/443 入站、对象存储或离线备份、足够资源与证书签发 ACME 客户端必须由运维准备。不要让 Genesis 自带 standalone Compose 与这里的联合 Compose 同时启动同一生产数据卷。
- 在 `AutoForceAI` 仓库内复制 `deploy/.env.production.example` 为不入 Git 的 `deploy/.env.production`（chmod 0600/ACL 仅运维可读）。通过机密管理器生成不同的 PostgreSQL/Mongo/两套 JWT/worker/Fernet/mail 密钥；`DATABASE_URL` 与 `POSTGRES_PASSWORD` 同步，Mongo URI 必须 URL encode 凭证并带 `authSource=admin`。`APP_DOMAIN`/`CRM_DOMAIN` 应是真实公网 DNS，CORS 两端精确 HTTPS origin。`GENESIS_TRACKING_BASE_URL` 是 CRM HTTPS 域名。**Compose config 可输出密钥，勿将其结果写日志、工单或 CI 构建产物。** `.env.production.example` 全部占位符不可直接用于上线。
- 不把容器内 DB、backend、worker 或两端 web 单独映射公网；联合 Nginx 仅发布 80/443。Compose `data` 网络隔离数据库，`app` 为内部服务和网关。设置主机防火墙，只允许指定的 ACME/HTTPS 入站及必要的运维源 IP。Docker 网络不等于防火墙；管控 docker.sock 与容器主机权限。
- Next.js 浏览器 API 基址须与前端同源。构建时 `NEXT_PUBLIC_API_URL=https://${APP_DOMAIN}` 必须匹配正式 HTTPS 域名（绝不能是内网容器名、localhost 或另一端域名）；生产 Nginx 把 `/api/`、`/auth/`、`/uploads/`、`/widget/` 等转发 backend；Next 服务端 `/api/` rewrite 的内部上游 `INTERNAL_API_URL=http://backend:8010`。Genesis Vite build-time `VITE_API_BASE_URL=/api`，Genesis web Nginx 转发 `/api/` 到 `genesis-server:5000`。不使用子路径承载另一前端；双域名直接分配各自虚拟主机。

## ACME 首次签发：有意先不启动完整生产网关

正式模板引用 `/etc/letsencrypt/live/<domain>/fullchain.pem` 与 `privkey.pem`，无证书时 Nginx **不能**启动。禁止把自签名证书放入生产目录假装签发成功。先在信任的主机上运行一次临时纯 HTTP ACME challenge 网关（可用 `nginx:1.27-alpine`，只挂载 `deploy/nginx/conf.d/acme-bootstrap.conf` 到 `/etc/nginx/conf.d/default.conf:ro` 和 `deploy/certbot/www` 到 `/var/www/certbot:ro`，只映射 `80:80`；将样板文件中的 `app.example.com`/`crm.example.com` 替换成已解析的实际域名**在私有工作副本中**）。用已审核 ACME 客户端分两次签发（示意：`certbot certonly --webroot -w <path-to-deploy/certbot/www> --cert-name <APP_DOMAIN> -d <APP_DOMAIN> -m <ACME_EMAIL> --agree-tos --no-eff-email`，再以 `<CRM_DOMAIN>` 为 `--cert-name` 和 `-d` 重复）；确保客户端写入 host `deploy/certbot/conf`（例如 Certbot `--config-dir`），两个 `live/<domain>/` 目录均存在，并将证书目录/续期权限仅赋给运维；停止临时网关，再启动正式 Compose。续期作业先 `certbot renew`，再 `docker compose ... exec nginx nginx -t && docker compose ... exec nginx nginx -s reload`，并监控证书到期、域名与 OCSP/链完整性。纯 HTTP challenge 模板返回 503，**不是**业务站点，也不算 HTTPS 验收。

## 初装和升级

```sh
# 在 AutoForceAI 仓库；切勿输出 private env 的展开内容
export COMPOSE_FILE=deploy/compose.yaml
export ENV_FILE=deploy/.env.production
# 验证占位符全部替换；本地测试只用 example，不要将真实 config 打印到屏幕
# docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config --quiet
# 全新 volume 创建后 PostgreSQL 基线为空。优先只启 DB，再运行 Alembic。
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d postgres mongo
# 等两库 healthy；先构建后端，再使用同一版本镜像运行升级；失败必须停止部署。
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build backend
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm --no-deps backend alembic upgrade head
# 验证两个真实 ACME 证书已装载，再构建/启动；不要运行 docker compose down -v。
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up --build -d
# 监控 nginx/backend/genesis-server/web/genesis-web/worker 与依赖状态；接口需实际认证演练。
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
curl -fsS https://app.example.com/health
curl -fsS https://crm.example.com/api/health
```

升级前冻结变更，检查两仓 commit 与兼容性、同步备份 PostgreSQL + Mongo、核对可解密与离线恢复演练。运行 `docker compose ... build` 构建和标记固定版本镜像，再运行 Alembic **upgrade**、滚动更新容器、检查双域名及线索/报价链路；SQL 迁移可能不可逆，升级前保留卷快照。回滚必须由值班人员手动批准：先阻断写入、记录受影响任务、保存当前状态，在有验证过的快照时将两仓代码/镜像回到兼容 commit；数据库不能无脑 `alembic downgrade` 或 `docker compose down -v`，需隔离恢复并核对 RPO/RTO，按操作单逐项切流。worker 是实际浏览器自动化，生产任务可能要求独立沙箱/可信目标限制；先在隔离环境审核浏览器插件和站点凭证后放量。

## 备份、演练与排障

- PostgreSQL H-12 工具：`deploy/backup/README.md`；Genesis Mongo H-12：`Genesis_CRM/docs/operations/mongo-backup.md`。`pgbackups`、`mongobackups` 是持久卷，但 Compose 不自带周期备份调度；运维配置私有 runner 挂载备份卷/可信凭证、定期离线复制并在演练 DB 做校验。备份报告的快照年龄不等于真实生产 RPO；跨仓 CRM 映射对账需协调同一时间点的冻结窗口。
- Nginx 启动失败先检查两个 DNS 和证书路径权限，再在可访问上游的同网络容器执行 `nginx -t`，检查无误后 `nginx -s reload`。健康检查失败：先核对 Mongo 凭证与 `authSource=admin`、PostgreSQL URL 与密码、Alembic revision；再查两个 API 日志（保护个人信息和授权头）。不向公共工单贴 `docker compose config`、包含密钥的命令行或完整日志。HTTP 429/503 先审计 AutoForceAI 单进程 rate-limit 保证与资源负载，不绕开安全限流。TLS 有效却登录失败时检查两个域名的 Cookie/CORS/origin、应用内 JWT 密钥是否一致，以及 Genesis `/api` 代理不得去掉 `/api` 前缀。
- 禁止将本地自签名演练标为生产 HTTPS 通过；已记录的本地单元测试和 `docker compose config --quiet` 只证明静态配置，完整 H-13 验收必须在目标主机执行真实容器构建/健康/业务/恢复演练。
