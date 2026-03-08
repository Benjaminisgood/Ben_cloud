
# AGENTS.md - Benphoto

## 项目定位

Benphoto 是个人摄影照片展示站，只负责：

1. 管理指向阿里云 OSS 的照片地址或对象 key。
2. 每天固定随机抽取一定数量照片放到桌面展示。
3. 允许管理员把照片扔进垃圾桶，并从垃圾桶里捡回。
4. 提供一个卡通化的桌面场景 Web UI 与最小 API。

## 当前架构（唯一真实来源）

Benphoto 已按 Ben_cloud FastAPI 新项目规范搭建，唯一后端代码路径：

- `/Users/ben/Desktop/myapp/Ben_cloud/Benphoto/apps/api/src/benphoto_api`

## 目录重点

- API 入口：`apps/api/src/benphoto_api/main.py`
- JSON/API 路由：`apps/api/src/benphoto_api/api/routes/`
- Web 路由：`apps/api/src/benphoto_api/web/routes/`
- 配置：`apps/api/src/benphoto_api/core/config.py`
- 数据层：`apps/api/src/benphoto_api/db/`, `.../models/`, `.../repositories/`
- 业务层：`apps/api/src/benphoto_api/services/`
- 模板：`apps/web/templates/`
- 静态资源：`apps/web/static/`
- 数据库：`data/benphoto.sqlite`
- 日志：`logs/`
- 迁移：`apps/api/alembic/versions/`

## 启动/测试

项目根目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benphoto`

```bash
./benphoto.sh init-env
./benphoto.sh install
./benphoto.sh start
./benphoto.sh status
./benphoto.sh stop

make install
make db-upgrade
make dev
make test
```

## 数据库迁移规则（强制）

1. 只允许通过 Alembic 变更 schema。
2. 禁止在常规流程依赖 runtime `create_all`。
3. 所有运行时数据只允许落在 `data/` 和 `logs/`。

## Agent 修改约束

1. 所有后端改动落在 `benphoto_api` 包内。
2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
3. 每日随机选图逻辑统一放在 `services/photo_desk.py`，不要在路由里拼装随机布局。
4. OSS 地址解析统一通过服务层完成，不在模板里拼 URL。
5. 先改代码再跑 `make test`；跨应用改动完成后回到工作区根执行 `make test`。
6. 继续迭代时，遵循：
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
