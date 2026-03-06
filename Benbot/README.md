# Benbot

Benbot 是 Ben_cloud 的统一门户与 SSO 中枢，运行在端口 **80**（开发/生产统一）。

## 职责

| 功能 | 说明 |
|------|------|
| **统一登录** | 用户在 Benbot 完成一次登录，可跳转到任意子应用并自动携带身份 |
| **SSO token 颁发** | 点击子应用卡片时生成 30 秒 HMAC-SHA256 签名 token，子应用 `/auth/sso` 消费 |
| **健康监控** | 每 60 秒轮询所有子应用 `/health`，记录状态和响应耗时 |
| **点击统计** | 记录每个子应用的访问次数（每日累计） |
| **子应用控制** | 管理员可通过 API 对子应用发起 start / stop / restart / status 操作 |

## SSO 流程

```
用户登录 Benbot (/login)
      ↓
点击子应用卡片（/goto/{project_id}）
      ↓
Benbot 生成 token（payload: username, role, exp, nonce）
      ↓
跳转 http://{host}:{port}/auth/sso?token=...
      ↓
子应用验证 token → 创建/查找本地账号 → 写入 localStorage 会话
      ↓
子应用首页（已登录状态）
```

token 规格：Base64URL(JSON_payload + "." + HMAC-SHA256 签名)，TTL = 30 秒。

## 快速启动

```bash
cd /Users/ben/Desktop/Ben_cloud/Benbot
make install        # 首次安装依赖（如有 Makefile）
# 或直接：
python app.py

# 脚本运维
./benbot.sh init-env
./benbot.sh install | start | stop | status | logs
```

访问地址：`http://localhost`（80 为 HTTP 默认端口，无需显式写出）

默认管理员：`benbenbuben / benbenbuben`（首次启动自动创建）

如需手动创建/修复管理员：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benbot
python apps/api/scripts/init_admin.py
# 或显式指定账号
python apps/api/scripts/init_admin.py --username admin --password 'your-password'
```

## 关键配置（.env）

```ini
ADMIN_USERNAME=benbenbuben
ADMIN_PASSWORD=benbenbuben
SSO_SECRET=benbot-sso-secret-2025      # 与所有子应用共享，须保持一致
SECRET_KEY=benbenbuben                  # Session 签名
PORT=80                                 # 统一端口（开发/生产一致）
```

## 目录结构

```
Benbot/
├── app.py                          # 启动入口
├── benbot.sh                       # 运维脚本
├── .env                            # 敏感配置（不提交）
├── apps/
│   ├── api/src/benbot_api/
│   │   ├── core/config.py          # 设置类（子应用注册在此）
│   │   ├── services/sso.py         # SSO token 创建与验证
│   │   ├── services/health.py      # 健康检测服务
│   │   ├── models/                 # User, ProjectHealth, ProjectClick
│   │   ├── web/routes/
│   │   │   ├── auth.py             # /login, /logout
│   │   │   └── pages.py            # / (dashboard), /goto/{id}
│   │   └── api/routes/             # /api/projects/status, /api/projects/{id}/control
│   ├── api/scripts/init_admin.py   # 手动管理员初始化/修复脚本
│   └── web/
│       ├── templates/              # login.html, index.html
│       └── static/
└── data/benbot.sqlite
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET/POST | `/login` | 登录页面 / 提交 |
| GET | `/logout` | 登出 |
| GET | `/goto/{project_id}` | SSO 跳转（需已登录） |
| GET | `/api/projects/status` | 子应用状态与点击统计（JSON） |
| POST | `/api/projects/check-health` | 手动触发健康检测（管理员） |
| POST | `/api/projects/{id}/control` | 控制子应用 start/stop/restart（管理员） |
| GET | `/metrics` | Prometheus 文本指标（运维监控） |

## 迁移与测试

```bash
cd /Users/ben/Desktop/Ben_cloud/Benbot
make test          # 运行 API 测试
make check         # compile + pytest + alembic current
make db-upgrade    # alembic upgrade head
make migrate-smoke # 临时库迁移冒烟
```

测试目录统一规范：
- 自动化测试统一放在 `apps/api/tests/`
- Benbot 根目录不保留 `test/` 或 `test_*.py`

> 现有历史库会由 Alembic baseline 自动接管（不会重复建表）。
