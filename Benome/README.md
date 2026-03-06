# Benome（ling居家）

Benome 是 Ben_cloud 旗下的民宿/短租预订系统，基于 FastAPI 构建。
核心设计原则：**访客无需注册即可预订**，管理员负责审核订单与发布房源。

## 核心业务流程

```
管理员发布房源
    ↓
访客浏览房源 → 填写姓名+手机号 → 提交预订（待审核）
（或登录账号后提交，订单关联账号）
    ↓
管理员确认收款 → 审核通过 → 订单确认
    ↓
对应夜晚日期被锁定（[check_in_date, check_out_date) 半开区间）
```

日期规则：
- 入住/退房默认中午计算。
- 计费与占用按"**夜晚**"计算。
- 锁定区间采用 `[check_in_date, check_out_date)`——退房当晚不占用，可同日接档。

## 功能一览

| 功能 | 权限 | 说明 |
|------|------|------|
| 浏览房源 | 所有人 | 按城市筛选，无需登录 |
| 查档期 | 所有人 | 指定日期区间内是否可订 |
| 提交预订 | 所有人（访客） | 仅需姓名+手机号，无需账号 |
| 我的预订 | 已登录客户 | 查看关联账号的订单历史 |
| 发布房源 | 管理员 | 标题、城市、价格、人数等 |
| 审核订单 | 管理员 | 通过/拒绝，标记收款状态 |
| Benbot 一键登录 | 可选 | SSO 跳转，跳转后自动识别角色 |

## 快速开始

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benome
make install      # 安装依赖
make db-upgrade   # 运行 Alembic 迁移
make dev          # 启动开发服务器（:8200）
```

API 文档：http://127.0.0.1:8200/docs

## 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| `benbenbuben` | `benbenbuben` | admin（首次启动自动创建） |

> 访客预订无需任何账号，填写入住人姓名和手机号即可。

## 环境变量（.env）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_USERNAME` | `benbenbuben` | 管理员账号 |
| `ADMIN_PASSWORD` | `benbenbuben` | 管理员密码 |
| `SSO_SECRET` | `benbot-sso-secret-2025` | 与 Benbot 共享的 SSO 签名密钥 |
| `SECRET_KEY` | `dev-secret-key` | Session 签名密钥 |
| `PORT` | `8200` | 监听端口 |
| `DATABASE_URL` | `sqlite:///data/benome.sqlite` | 数据库连接 |
| `ALIYUN_OSS_ENDPOINT` | — | OSS Endpoint（可选，用于数据同步） |
| `ALIYUN_OSS_ACCESS_KEY_ID` | — | OSS AccessKey ID |
| `ALIYUN_OSS_ACCESS_KEY_SECRET` | — | OSS AccessKey Secret |
| `ALIYUN_OSS_BUCKET` | — | OSS Bucket 名称 |

## API 端点概览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/` | 所有人 | 首页（index.html） |
| GET | `/auth/sso` | — | Benbot SSO 回调，写 localStorage 后跳转 `/` |
| POST | `/api/auth/register` | — | 注册客户账号 |
| POST | `/api/auth/login` | — | 账号密码登录，返回用户信息与轻量 token |
| GET | `/api/properties` | 所有人 | 列出所有上架房源 |
| POST | `/api/admin/properties` | admin | 发布新房源 |
| GET | `/api/properties/{id}/availability` | 所有人 | 查询档期可用性 |
| POST | `/api/bookings` | 所有人（访客） | 提交预订（无需登录） |
| GET | `/api/bookings/me` | 已登录客户 | 查询我的订单 |
| GET | `/api/admin/bookings/pending` | admin | 查看待审核订单 |
| PATCH | `/api/admin/bookings/{id}/review` | admin | 审核订单（通过/拒绝） |
| GET | `/health` | — | 健康检测端点（Benbot 轮询） |

> `POST /api/bookings` 通过可选的 `X-User-Id` 请求头关联账号；不传则为访客预订。

## 数据库迁移（Alembic）

| revision | 说明 |
|----------|------|
| `9f4b7a1d2c3e` | baseline（初始 schema） |
| `a1b2c3d4e5f6` | guest booking：`booking.customer_id` 改为可空 |
| `b2c3d4e5f6a7` | 添加房间媒体表（property_media） |

当前 head：`b2c3d4e5f6a7`

## 房间媒体功能（新增 🎉）

Benome 现已支持为每个房间上传**图片和视频**，所有文件存储在阿里云 OSS。

### 功能特点

- ✅ 支持图片（JPG/PNG/GIF/WebP）和视频（MP4）上传
- ✅ 自动存储到阿里云 OSS（bucket: `benome`）
- ✅ 支持设置封面图片
- ✅ 支持拖拽上传，最大 500MB
- ✅ 房间详情页展示媒体画廊
- ✅ 支持灯箱模式查看大图/视频

### 使用方法

1. **管理员登录** Benome 后台（`/admin/dashboard`）
2. 在"房间媒体管理"卡片中选择要管理的房间
3. 拖拽文件或点击选择文件上传
4. 填写标题、描述（可选），可勾选"设为封面"
5. 上传完成后可在房间详情页查看

### API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/properties/{id}/media` | 所有人 | 获取房间媒体列表 |
| POST | `/api/properties/{id}/media/upload` | admin | 上传媒体文件 |
| GET | `/api/media/{id}` | 所有人 | 获取媒体详情 |
| PATCH | `/api/media/{id}` | admin | 更新媒体信息 |
| DELETE | `/api/media/{id}` | admin | 删除媒体 |
| POST | `/api/properties/{id}/media/{id}/set-cover` | admin | 设为封面 |

### 前端页面

- `/properties/{id}` - 房间详情页（带媒体画廊）
- `/admin/properties/{id}/media` - 管理员媒体管理页

### OSS 配置

在 `.env` 文件中配置阿里云 OSS：

```bash
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_ACCESS_KEY_ID=your_access_key_id
ALIYUN_OSS_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_OSS_BUCKET=benome
```

> 注意：bucket 名称固定为 `benome`，与其他项目（Benlab→benlab, Benusy→benusy）保持一致命名规则。

## 目录结构

```
Benome/
├── apps/
│   ├── api/
│   │   ├── src/benome_api/
│   │   │   ├── main.py              # FastAPI 应用入口
│   │   │   ├── core/config.py       # 配置（Settings）
│   │   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   │   ├── repositories/        # 数据访问层
│   │   │   ├── services/            # 业务逻辑层
│   │   │   │   └── sso.py           # Benbot SSO token 验证
│   │   │   ├── api/routes/          # JSON API 路由
│   │   │   └── web/routes/          # HTML 页面路由（含 /auth/sso）
│   │   ├── alembic/versions/        # 数据库迁移脚本
│   │   └── tests/                   # Pytest 测试套件
│   └── web/
│       ├── templates/index.html     # 单页前端模板
│       └── static/
│           ├── css/main.css
│           └── js/site.js
├── docs/
│   ├── guides/                      # 功能与操作指南
│   └── reports/                     # 阶段报告与实现总结
├── scripts/                         # 运维与调试脚本
├── data/                            # 本地数据库目录
├── logs/                            # 运行日志目录
├── .env                             # 环境变量（不入 git）
└── Makefile
```
