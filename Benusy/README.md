# Benusy（达人运营协作平台）

Benusy 是 Ben_cloud 旗下的达人/博主运营协作系统，基于 FastAPI 构建。
连接品牌方（管理员）与内容创作者（博主），完成任务发布、接单、提交、审核、结算全流程。

## 核心业务流程

```
管理员发布推广任务（平台、奖励、名额）
    ↓
博主浏览任务 → 接单（生成 Assignment）
    ↓
博主完成推广 → 提交作品/数据
    ↓
管理员审核 Assignment → 通过/拒绝
    ↓
审核通过 → 生成结算记录 → 结算到账
```

## 支持平台

- 抖音（Douyin）
- 小红书（Xiaohongshu）
- 微博（Weibo）

每个平台有独立的指标权重配置（`PlatformMetricConfig`），用于计算实际奖励。

## 功能一览

| 功能 | 权限 | 说明 |
|------|------|------|
| 浏览已发布任务 | 所有人 | 公开任务列表 |
| 接单 / 取消接单 | 博主 | 每任务限制接单人数 |
| 提交作品数据 | 博主 | 上传成果链接 + 指标数据 |
| 提交手动指标 | 博主 | 含截图证明，待审核 |
| 查看我的接单 | 博主 | Assignment 状态追踪 |
| 发布 / 编辑任务 | 管理员 | 标题、奖励、平台、名额 |
| 审核接单 | 管理员 | 通过/拒绝，触发结算 |
| 审核手动指标 | 管理员 | 审核博主自报数据 |
| 结算管理 | 管理员 | 查看/更新结算记录状态 |
| 用户审核 | 管理员 | 审核博主账号注册申请 |
| 平台指标权重配置 | 管理员 | 配置各平台计分系数 |
| 达人权重分配 | 管理员 | 设置博主任务分配权重 |
| Benbot 一键登录 | 可选 | SSO 跳转，角色自动映射 |

## 快速开始

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benusy
make install      # 安装依赖
make db-upgrade   # 运行 Alembic 迁移
make dev          # 启动开发服务器（:8100）
```

API 文档：http://127.0.0.1:8100/docs

## 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| `benbenbuben` | `benbenbuben` | admin（首次启动自动创建） |

## 环境变量（.env）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_USERNAME` | `benbenbuben` | 管理员账号 |
| `ADMIN_PASSWORD` | `benbenbuben` | 管理员密码 |
| `SSO_SECRET` | `dev-sso-secret` | 与 Benbot 共享的 SSO 签名密钥 |
| `SECRET_KEY` | `dev-secret-key` | JWT / Session 签名密钥 |
| `PORT` | `8100` | 监听端口 |
| `DATABASE_URL` | `sqlite:///data/benusy.sqlite` | 数据库连接 |

## 认证方式

Benusy 采用**双模认证**：

- **JWT Bearer Token**：`POST /auth/token` 获取，60 分钟有效期（remember me 延长至 30 天）。
- **Session Cookie**：Web 页面登录后自动携带，`POST /auth/login` 写入。
- **Benbot SSO**：`GET /auth/sso?token=<token>` 接收 Benbot 颁发的 30 秒 HMAC token，验证后建立本地 session。

`get_current_user()` 依赖同时接受 JWT 和 session cookie，优先使用 JWT。

## API 端点概览

| 前缀 | 说明 |
|------|------|
| `/auth` | 注册、登录、SSO、token 刷新 |
| `/users` | 个人资料、密码、账号管理 |
| `/tasks` | 任务浏览、接单、取消 |
| `/assignments` | 我的接单、提交作品、手动指标 |
| `/dashboard` | 概览统计、用户数据 |
| `/admin` | 23 个管理端点（用户审核、任务管理、结算、指标配置等） |
| `/public` | 无需认证的公开任务列表 |

## 核心数据模型

| 模型 | 说明 |
|------|------|
| `User` | 平台用户（admin / blogger），含社媒账号、权重、粉丝数 |
| `Task` | 推广任务（draft → published → cancelled） |
| `Assignment` | 接单记录（pending → submitted → approved / rejected） |
| `Metric` | 系统记录的作品数据（点赞、收藏、分享、播放） |
| `ManualMetricSubmission` | 博主自报指标（含截图，待管理员审核） |
| `SettlementRecord` | 结算记录（pending → settled） |
| `PayoutInfo` | 收款信息（银行卡/微信/支付宝） |
| `PlatformMetricConfig` | 平台计分权重配置 |
| `SocialAccount` | 抖音/小红书/微博账号绑定 |

## 数据库迁移（Alembic）

| revision | 说明 |
|----------|------|
| `43b1d4e82862` | baseline（初始 schema） |

当前 head：`43b1d4e82862`

## Benbot 门户接入

Benbot 通过 `/goto/benusy` 跳转到 `GET /auth/sso?token=...`，完成统一身份认证，角色映射到 Benusy 的 admin / blogger。

## 目录结构

```
Benusy/
├── apps/
│   ├── api/
│   │   ├── src/benusy_api/
│   │   │   ├── main.py              # FastAPI 应用入口
│   │   │   ├── core/config.py       # Settings（含 SSO_SECRET）
│   │   │   ├── models/              # SQLModel 模型
│   │   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   │   ├── repositories/        # 数据访问层
│   │   │   ├── services/            # 业务逻辑层
│   │   │   ├── api/routes/          # JSON API 路由
│   │   │   └── web/routes/          # HTML 页面路由
│   │   ├── alembic/versions/        # 数据库迁移脚本
│   │   └── tests/                   # Pytest 测试套件
│   └── web/
│       ├── templates/               # Jinja2 模板
│       └── static/                  # CSS / JS
├── data/benusy.sqlite               # SQLite 数据库
├── .env                             # 环境变量（不入 git）
└── Makefile
```
