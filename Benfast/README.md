# Benfast

Benfast 是 Ben_cloud 的文档站与 RBAC 子应用，既承载课题组正式文档站，也提供可复用的用户、权限和 SSO 接入能力。

## 主要能力

- Benbot SSO 登录接入
- `/` 作为 Benfast 首页，选择进入 `/app` 或 `/kb`
- `/portal` 兼容跳转到首页 `/`
- 文档工作台与静态站发布
- RBAC、用户与权限管理

## 快速开始

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
./benfast.sh init-env
./benfast.sh install
./benfast.sh start
./benfast.sh status
```

默认地址：
- Health: [http://127.0.0.1:8700/health](http://127.0.0.1:8700/health)
- Home: [http://127.0.0.1:8700/](http://127.0.0.1:8700/)
- Portal: [http://127.0.0.1:8700/portal](http://127.0.0.1:8700/portal)
- KB: [http://127.0.0.1:8700/kb/](http://127.0.0.1:8700/kb/)

开发模式：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
make install
make dev
```

## 测试与构建

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
make test
make check
make docs-build
make docs-serve
```

`make docs-serve` 默认在 `http://127.0.0.1:8800` 预览 `site/`。

## 关键配置

推荐从 `.env.example` 复制：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
cp .env.example .env
```

重点变量：
- `PORT=8700`
- `SQLITE_DB_PATH=/Users/ben/Desktop/Ben_cloud/Benfast/data/benfast.sqlite3`
- `SSO_SECRET=replace_with_shared_sso_secret`
- `SECRET_KEY=your_secret_key_here_generate_with_openssl_rand_hex_32`
- `DOCS_SITE_DIR`
- `LABDOCS_LOCAL_ROOT`
- `LABDOCS_DOCS_SOURCE_ROOT`
- `LABDOCS_PUBLISH_ROOT`

安全要求：
- `SSO_SECRET` 必须与 Benbot 完全一致
- 所有密钥必须显式配置，不能使用弱默认值
- 运行时数据库和日志必须放在 `data/`、`logs/` 下

## SSO 入口

Benfast 需要保持以下入口兼容：
- `GET /health`
- `GET /auth/sso?token=...`
- `GET /portal`
- `GET /kb/`

SSO 流程：

```text
Benbot /login
  -> /goto/benfast
  -> Benfast /auth/sso?token=...
  -> /
  -> /app/ or /kb/
```

## 目录结构

```text
Benfast/
├── src/
├── docs/
├── scripts/
├── tests/
├── data/
├── logs/
├── site/
├── benfast.sh
├── Makefile
└── AGENTS.md
```

## 更多文档

- 执行边界与修改约束：`/Users/ben/Desktop/Ben_cloud/Benfast/AGENTS.md`
- 文档站专题：`/Users/ben/Desktop/Ben_cloud/Benfast/docs/index.md`
