# Benusy

Benusy 是 Ben_cloud 的达人运营协作平台，用于管理任务发布、达人接单、提交审核和结算流程。

## 核心流程

```text
管理员发布任务
  -> 达人接单
  -> 达人提交作品与数据
  -> 管理员审核
  -> 生成并更新结算记录
```

支持平台：
- 抖音
- 小红书
- 微博

## 主要能力

- 公开任务浏览
- 接单、取消接单、作品提报
- 手动指标提交与审核
- 结算管理
- 平台指标权重配置
- Benbot SSO 一键登录

## 快速开始

```bash
cd /Users/ben/Desktop/Ben_cloud/Benusy
make install
make db-upgrade
make dev
```

访问地址：
- Web: [http://127.0.0.1:8100](http://127.0.0.1:8100)
- Docs: [http://127.0.0.1:8100/docs](http://127.0.0.1:8100/docs)

脚本运维：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benusy
./benusy.sh install
./benusy.sh start
./benusy.sh status
./benusy.sh stop
```

## 测试与迁移

```bash
cd /Users/ben/Desktop/Ben_cloud/Benusy
make test
make check
```

常用迁移命令：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benusy
make db-current
make db-upgrade
make db-revision m="add_xxx"
```

## 关键配置

推荐从 `.env.example` 复制：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benusy
cp .env.example .env
```

重点变量：
- `PORT=8100`
- `DATABASE_URL=sqlite:////Users/ben/Desktop/Ben_cloud/Benusy/data/benusy.sqlite`
- `SSO_SECRET=replace_with_shared_sso_secret`
- `SECRET_KEY=replace_with_long_random_session_secret`
- `ACCESS_TOKEN_EXPIRE_MINUTES=60`
- `REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS=30`

安全要求：
- `SSO_SECRET` 必须与 Benbot 完全一致
- 所有密钥必须显式配置，不能使用弱默认值

## 认证方式

- `POST /auth/token`：JWT Bearer Token
- `POST /auth/login`：Web Session 登录
- `GET /auth/sso?token=...`：Benbot SSO 登录

`get_current_user()` 同时接受 JWT 和 session cookie，优先 JWT。

## API 概览

| 前缀 | 说明 |
|------|------|
| `/auth` | 注册、登录、SSO、token 刷新 |
| `/users` | 个人资料与账号管理 |
| `/tasks` | 任务浏览、接单、取消 |
| `/assignments` | 接单、提报、手动指标 |
| `/dashboard` | 数据概览 |
| `/admin` | 管理端任务、审核、结算、权重配置 |
| `/public` | 无需认证的公开列表 |

## 目录结构

```text
Benusy/
├── apps/
│   ├── api/
│   │   ├── src/benusy_api/
│   │   ├── alembic/versions/
│   │   └── tests/
│   └── web/
├── data/
├── logs/
├── Makefile
└── AGENTS.md
```

## 更多文档

- 执行边界与修改约束：`/Users/ben/Desktop/Ben_cloud/Benusy/AGENTS.md`
