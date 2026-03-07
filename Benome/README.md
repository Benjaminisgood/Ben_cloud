# Benome

Benome 是 Ben_cloud 的民宿与短租预订子应用，核心特点是访客无需注册即可预订，管理员负责房源发布、订单审核和媒体管理。

## 核心流程

```text
管理员发布房源
  -> 访客浏览房源并提交预订
  -> 管理员确认收款并审核
  -> 已确认订单锁定对应夜晚区间
```

日期规则：
- 计费与占用按夜晚计算
- 锁定区间使用 `[check_in_date, check_out_date)`
- 退房当晚不占用，可同日接档

## 主要能力

- 房源浏览与档期查询
- 访客预订和登录客户订单查询
- 管理员房源、订单和媒体管理
- Benbot SSO 登录接入
- 阿里云 OSS 媒体存储

## 快速开始

```bash
cd /Users/ben/Desktop/Ben_cloud/Benome
make install
make db-upgrade
make dev
```

访问地址：
- Web: [http://127.0.0.1:8200](http://127.0.0.1:8200)
- Docs: [http://127.0.0.1:8200/docs](http://127.0.0.1:8200/docs)

脚本运维：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benome
./benome.sh install
./benome.sh start
./benome.sh status
./benome.sh stop
```

## 测试与迁移

```bash
cd /Users/ben/Desktop/Ben_cloud/Benome
make test
make check
```

常用迁移命令：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benome
make db-current
make db-upgrade
make db-revision m="add_xxx"
```

## 关键配置

推荐从 `.env.example` 复制：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benome
cp .env.example .env
```

重点变量：
- `PORT=8200`
- `DATABASE_URL=sqlite:////Users/ben/Desktop/Ben_cloud/Benome/data/benome.sqlite`
- `SSO_SECRET=replace_with_shared_sso_secret`
- `SECRET_KEY=replace_with_long_random_session_secret`
- `ALIYUN_OSS_ENDPOINT`
- `ALIYUN_OSS_ACCESS_KEY_ID`
- `ALIYUN_OSS_ACCESS_KEY_SECRET`
- `ALIYUN_OSS_BUCKET`

安全要求：
- `SSO_SECRET` 必须与 Benbot 完全一致
- 所有密钥必须显式配置，不能使用弱默认值

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 首页 |
| GET | `/auth/sso` | Benbot SSO 回调 |
| GET | `/api/properties` | 房源列表 |
| GET | `/api/properties/{id}/availability` | 房态查询 |
| POST | `/api/bookings` | 提交预订 |
| GET | `/api/bookings/me` | 我的预订 |
| POST | `/api/admin/properties` | 发布房源 |
| GET | `/api/admin/bookings/pending` | 待审核订单 |
| PATCH | `/api/admin/bookings/{id}/review` | 审核订单 |
| GET | `/health` | 健康检查 |

## 房间媒体

Benome 支持图片和视频上传，媒体文件存储在阿里云 OSS。

常用入口：
- `GET /api/properties/{id}/media`
- `POST /api/properties/{id}/media/upload`
- `PATCH /api/media/{id}`
- `DELETE /api/media/{id}`
- `POST /api/properties/{id}/media/{id}/set-cover`

## 目录结构

```text
Benome/
├── apps/
│   ├── api/
│   │   ├── src/benome_api/
│   │   ├── alembic/versions/
│   │   └── tests/
│   └── web/
├── docs/
├── scripts/
├── data/
├── logs/
├── Makefile
└── AGENTS.md
```

## 更多文档

- 执行边界与修改约束：`/Users/ben/Desktop/Ben_cloud/Benome/AGENTS.md`
- 详细专题文档：`/Users/ben/Desktop/Ben_cloud/Benome/docs/README.md`
