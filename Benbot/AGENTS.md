# AGENTS.md - Benbot

## 职责定位

Benbot 是 Ben_cloud 的**统一门户和 SSO 中枢**，不承载业务数据，只负责：

1. 用户登录与 session 管理
2. 颁发 SSO token 给子应用
3. 轮询子应用健康状态
4. 记录子应用访问点击统计
5. 提供管理员子应用控制接口（start/stop/restart）

## 当前架构（唯一真实来源）

唯一后端代码路径：

- `/Users/ben/Desktop/Ben_cloud/Benbot/apps/api/src/benbot_api`

## 目录重点

| 路径 | 说明 |
|------|------|
| `apps/api/src/benbot_api/main.py` | FastAPI 应用入口、lifespan（启动健康检测循环） |
| `apps/api/src/benbot_api/core/config.py` | 设置类；**子应用注册表在此**（get_projects()） |
| `apps/api/src/benbot_api/services/sso.py` | `create_sso_token` / `verify_sso_token` |
| `apps/api/src/benbot_api/services/health.py` | 异步健康检测（asyncio.gather） |
| `apps/api/src/benbot_api/web/routes/auth.py` | `/login` (GET/POST) / `/logout` |
| `apps/api/src/benbot_api/web/routes/pages.py` | `/` dashboard / `/goto/{project_id}` SSO 跳转 |
| `apps/api/src/benbot_api/api/routes/` | `/api/projects/status` / control |
| `apps/api/src/benbot_api/models/` | User, ProjectHealth, ProjectClick |
| `apps/api/tests/` | **唯一自动化测试目录** |
| `apps/web/templates/` | login.html, index.html |
| `data/benbot.sqlite` | SQLite 数据库 |

## 新增子应用流程

1. 在 `core/config.py` 的 `get_projects()` 里添加 `ProjectConfig`：
   ```python
   ProjectConfig(
       id="newapp",
       name="NewApp",
       description="...",
       icon="🆕",
       port=XXXX,
       internal_url=self.NEWAPP_INTERNAL_URL,
       public_url=self.NEWAPP_PUBLIC_URL,
       sso_entry_path="/auth/sso",
       sso_enabled=True,
   )
   ```
2. 在 `Settings` 中添加对应的 `NEWAPP_INTERNAL_URL` 和 `NEWAPP_PUBLIC_URL` 字段。
3. 在子应用实现 `GET /auth/sso?token=...` 端点，使用 `SSO_SECRET` 验证 token。
4. 在 `project_standards/registry.yaml` 注册新应用。

## SSO token 规格

```python
# payload 字段
{
  "u": username,      # 用户名
  "r": role,          # 角色（"admin" 或 "user"）
  "e": exp_timestamp, # 过期时间（当前 Unix 时间 + 30 秒）
  "n": nonce,         # 8 字节随机 hex（防重放）
}
# 编码：Base64URL(JSON_payload + "." + HMAC-SHA256(JSON_payload, SSO_SECRET))
```

## Agent 修改约束

1. 所有后端改动落在 `benbot_api` 包内。
2. 子应用注册配置变更只能在 `core/config.py` 的 `get_projects()` 中进行。
3. SSO token 签名逻辑（`services/sso.py`）不得在无充分理由时变更——修改会导致所有子应用的 SSO 失效。
4. 健康检测逻辑变更后，确认 lifespan 中的后台任务仍能正常启停。
5. 测试文件统一放在 `apps/api/tests/`；Benbot 根目录禁止新增 `test/` 或 `test_*.py`。
6. Schema 变更必须通过 Alembic（`apps/api/alembic`），禁止重新引入 `create_all` 作为长期迁移方案。
7. 安全相关变量（`SECRET_KEY` / `SSO_SECRET` / `NANOBOT_API_TOKEN`）必须在 `.env` 显式配置，禁止依赖不安全默认值。

## 启动/运维

项目根目录：`/Users/ben/Desktop/Ben_cloud/Benbot`

```bash
python app.py          # 开发启动

./benbot.sh init-env   # 生成 .env（如缺失）
./benbot.sh install    # 安装依赖
./benbot.sh start      # 后台启动
./benbot.sh status     # 查看状态
./benbot.sh stop       # 停止
./benbot.sh logs       # 查看日志

# 数据迁移
make db-upgrade        # alembic upgrade head
make db-current        # 查看当前版本
```

## 环境变量（.env）

| 变量 | 说明 |
|------|------|
| `ADMIN_USERNAME / ADMIN_PASSWORD` | 管理员账号（默认 `benbenbuben / benbenbuben`） |
| `SSO_SECRET` | SSO 签名密钥，须与所有子应用一致 |
| `SECRET_KEY` | Session 签名密钥 |
| `PORT` | 监听端口（开发/生产统一为 80） |
| `BENXXX_INTERNAL_URL` | 子应用内网地址（健康检测用） |
| `BENXXX_PUBLIC_URL` | 子应用公网地址（浏览器跳转用） |
| `HEALTH_CHECK_INTERVAL` | 健康检测间隔秒数（默认 60） |
