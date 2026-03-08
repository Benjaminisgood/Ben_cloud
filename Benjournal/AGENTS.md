
# AGENTS.md - Benjournal

## 项目定位

Benjournal 是个人日记原始事实源站点，当前只负责：

1. 按天录入语音日志与手工文本。
2. 合并当天音频并归档到 OSS。
3. 调用 STT 获得当天转写文本并落 SQLite。
4. 对外提供可供未来 agent 消费的原始 journal 文本。

未来跨项目事实提取、Graphiti episode 写入、Benlab/Benhealth 等结构化同步，不在本项目代码范围内。

## 当前架构（唯一真实来源）

Benjournal 已按 Ben_cloud FastAPI 新项目规范搭建，唯一后端代码路径：

- `/Users/ben/Desktop/myapp/Ben_cloud/Benjournal/apps/api/src/benjournal_api`

## 目录重点

- API 入口：`apps/api/src/benjournal_api/main.py`
- JSON/API 路由：`apps/api/src/benjournal_api/api/routes/`
- Web 路由：`apps/api/src/benjournal_api/web/routes/`
- 配置：`apps/api/src/benjournal_api/core/config.py`
- 数据层：`apps/api/src/benjournal_api/db/`, `.../models/`, `.../repositories/`
- 业务层：`apps/api/src/benjournal_api/services/`
- 模板：`apps/web/templates/`
- 静态资源：`apps/web/static/`
- 数据库：`data/benjournal.sqlite`
- 音频片段目录：`data/audio_segments/`
- 合并音频目录：`data/audio_combined/`
- 本地 OSS 镜像目录：`data/local_oss/`（开发/测试默认 provider）
- 日志：`logs/`
- 迁移：`apps/api/alembic/versions/`

## 启动/测试

项目根目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benjournal`

```bash
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

1. 所有后端改动落在 `benjournal_api` 包内。
2. 新增查询放 `repositories`，业务逻辑放 `services`，路由层保持薄。
3. 音频合并、OSS 上传、STT 调用只能在 `services/` 编排，禁止把外部集成直接写进路由。
4. 所有展示都以服务层输出的聚合视图为准，不在路由里写复杂 SQL。
5. 先改代码再跑 `make test`；跨应用改动完成后回到工作区根执行 `make test`。
6. 继续迭代时，遵循：
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`
