# AGENTS.md - Benvinyl

## 项目定位

Benvinyl 是音频展示站，负责把你放在阿里云 OSS 的音频引用整理成一个黑胶唱片机场景：

1. 每天固定随机上线一批音频节目。
2. 在桌面唱片堆里切换当天节目。
3. 管理员可把唱片拖进垃圾桶，暂时下架。
4. 管理员可从垃圾桶捡回唱片，重新放回当天唱片堆。

不做分类系统、不做复杂推荐、不在本项目落地原始音频文件。

## 当前架构（唯一真实来源）

Benvinyl 已按 Ben_cloud FastAPI 新项目规范搭建，唯一后端代码路径：

- `/Users/ben/Desktop/myapp/Ben_cloud/Benvinyl/apps/api/src/benvinyl_api`

## 目录重点

- API 入口：`apps/api/src/benvinyl_api/main.py`
- JSON/API 路由：`apps/api/src/benvinyl_api/api/routes/`
- Web 路由：`apps/api/src/benvinyl_api/web/routes/`
- 配置：`apps/api/src/benvinyl_api/core/config.py`
- 数据层：`apps/api/src/benvinyl_api/db/`, `.../models/`, `.../repositories/`
- 业务层：`apps/api/src/benvinyl_api/services/`
- 模板：`apps/web/templates/`
- 静态资源：`apps/web/static/`
- 数据库：`data/benvinyl.sqlite`
- 日志：`logs/`
- 迁移：`apps/api/alembic/versions/`

## 启动/测试

项目根目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benvinyl`

```bash
./benvinyl.sh init-env
./benvinyl.sh install
./benvinyl.sh start
./benvinyl.sh status
./benvinyl.sh stop

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

1. 所有后端改动落在 `benvinyl_api` 包内。
2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
3. 每日节目编排、垃圾桶恢复和 OSS URL 拼装只能在 `services/` 编排。
4. 所有展示都以服务层输出的聚合视图为准，不在路由里写复杂 SQL。
5. 先改代码再跑 `make test`；跨应用改动完成后回到工作区根执行 `make test`。
6. 继续迭代时，遵循：
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
