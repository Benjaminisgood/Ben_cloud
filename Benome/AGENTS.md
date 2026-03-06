# AGENTS.md - Benome

## 职责定位

Benome（ling居家）是 Ben_cloud 的民宿/短租预订子应用，核心特点：

- **访客预订**：无需注册账号，仅需姓名+手机号即可提交订单。
- **SSO 可选**：通过 Benbot 一键登录后可查看个人订单历史，角色自动映射。
- **管理员审核**：订单进入待审核状态，admin 确认收款后方可通过。

## 当前架构（唯一真实来源）

唯一后端代码路径：

- `/Users/ben/Desktop/Ben_cloud/Benome/apps/api/src/benome_api`

## 目录重点

| 路径 | 说明 |
|------|------|
| `apps/api/src/benome_api/main.py` | FastAPI 应用入口、lifespan |
| `apps/api/src/benome_api/core/config.py` | Settings（含 SSO_SECRET、OSS 配置） |
| `apps/api/src/benome_api/services/sso.py` | `verify_sso_token`——验证 Benbot SSO token |
| `apps/api/src/benome_api/web/routes/pages.py` | `/`（首页）、`/auth/sso`（SSO 回调） |
| `apps/api/src/benome_api/api/routes/bookings.py` | 预订 CRUD；POST 无需强制认证 |
| `apps/api/src/benome_api/api/routes/properties.py` | 房源 CRUD |
| `apps/api/src/benome_api/models/booking.py` | Booking 模型（`customer_id` 可空=访客） |
| `apps/api/src/benome_api/repositories/` | 数据访问层 |
| `apps/api/src/benome_api/services/` | 业务逻辑层 |
| `apps/web/templates/index.html` | 单页前端（房源大厅 + 预订 + 管理台） |
| `apps/web/static/js/site.js` | 前端逻辑（localStorage session，无 Cookie） |
| `data/benome.sqlite` | SQLite 数据库 |

## 访客预订机制

`POST /api/bookings` 接受可选的 `X-User-Id` 请求头：

- **有 X-User-Id**：关联已登录客户账号（显示在"我的预订"）。
- **无 X-User-Id**：作为访客预订（`customer_id=NULL`）；管理员查看时显示"访客预订"。

`Booking.customer_id` 字段为 `nullable=True`（迁移 `a1b2c3d4e5f6` 已落地）。

## Benbot SSO 流程

```
Benbot /goto/benome
    → Benome /auth/sso?token=<30s HMAC token>
    → verify_sso_token() 验证签名+过期
    → 查找或创建本地用户（role 映射：benbot admin→benome admin，其余→customer）
    → 返回 HTML 页面（内联 JS 写 localStorage benome_session_v1 并跳转 /）
```

`SSO_SECRET` 必须与 Benbot 的 `.env` 中 `SSO_SECRET` 保持一致。

## 启动/测试

项目根目录：`/Users/ben/Desktop/Ben_cloud/Benome`

```bash
make install      # 安装依赖
make db-upgrade   # 运行迁移（必须在首次 dev 前执行）
make dev          # 开发服务器（:8200）
make test         # 运行测试套件
```

脚本运维：

```bash
./benome.sh install
./benome.sh start
./benome.sh status
./benome.sh stop
```

## 数据库迁移规则（强制）

- **只允许**通过 Alembic 变更 schema。
- 禁止在常规流程依赖 runtime `create_all`。

| revision | 说明 |
|----------|------|
| `9f4b7a1d2c3e` | baseline（初始 schema） |
| `a1b2c3d4e5f6` | guest booking：`booking.customer_id` 改为可空 |
| `b2c3d4e5f6a7` | property media：新增 `property_media` 表 |

当前 head：`b2c3d4e5f6a7`

## Agent 修改约束

1. 所有后端改动落在 `benome_api` 包内。
2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
3. `verify_sso_token` 算法不得无故变更——修改会与 Benbot 签名不兼容。
4. 修改 `Booking.customer_id` 相关逻辑时，确认访客路径（None）和登录路径均能正常工作。
5. 先改代码再跑 `make test`，失败必须修复后再结束。

## 工程规范与持续优化（强制）

1. 新项目开发或既有代码修改，必须遵循：
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
2. 不允许为"临时可用"牺牲分层边界（route/service/repository）。
3. 每次交付至少执行一次工程优化动作：
   - 低风险优化直接落地（例如提取重复逻辑、补测试、清理无效代码）。
   - 中高风险优化在交付说明中给出明确下一步清单。
