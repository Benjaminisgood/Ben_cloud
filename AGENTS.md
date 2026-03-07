# AGENTS.md - Ben_cloud Dispatcher

本文件是 Ben_cloud 的根级调度入口。

## 目标

1. 将任务路由到正确子应用。
2. 强制执行跨项目通用安全与工程底线。
3. 明确“新项目标准”与“现有项目规则”的边界。

## 强制启动序列

每次任务执行必须按此顺序操作：

1. 读本文件。
2. 根据任务意图选择目标子应用（见下方路由策略）。
3. 读目标子应用自己的 `AGENTS.md`。
4. 仅在目标子应用范围内执行；跨应用任务需显式标注边界。

## 路由策略

| 意图关键词 | 目标应用 |
|-----------|---------|
| 门户、SSO、健康监控、子应用管理、系统运维 | **Benbot** |
| Markdown、笔记、周报、模板、会议纪要、实验记录 | **Benben** |
| 社交、家庭、生活、日程、提醒、亲友 | **Benlab** |
| 学习、协作、团队、复盘、研究、工作 | **Benoss** |
| 达人、任务、审核、结算、运营、分配 | **Benusy** |
| 民宿、房源、预定、预订、入住、退房、锁期 | **Benome** |
| 文献、科研数据、元信息、聚合、抓取 | **Bensci** |
| 剪贴板、文件中转、上传下载、断点续传 | **Benfer** |
| 模板、后端模板、RBAC、管理后台、脚手架 | **Benfast** |

- 意图模糊时：写操作前提出一个简短澄清问题。
- 跨应用任务：拆分为每个应用内的独立步骤执行。

## 新项目标准边界（关键）

`PROJECT_STANDARDS/` 的唯一作用是：**未来新增项目搭建时的统一规范来源**。

- 仅在“新项目搭建/重建级改造”场景使用 `PROJECT_STANDARDS/`。
- 现有项目的执行细则、业务规则、约束说明，全部以各项目自身 `AGENTS.md` 为准。

## 全局强制规则

1. 不得绕过子应用 `AGENTS.md` 中的约束。
2. Schema 变更仅允许通过 Alembic；禁止 ad-hoc 直接修改数据库 schema。
3. 优先通过 API / 服务层变更，不直接 patch 数据。
4. 任务完成前必须跑测试：
   - 单应用改动：该应用 `make test`。
   - 跨应用改动：根目录 `make test`（workdir：`/Users/ben/Desktop/Ben_cloud`）。
5. 写操作（`POST` / `PATCH` / `DELETE`）须记录返回 ID，用于审计和回滚。
6. 认证失败处理：
   - `401`：重新登录一次后再重试一次。
   - 连续 `401` 或任何 `403`：停止并上报。
7. 如涉及新项目搭建或重建级改造，必须遵循：
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/PLAYBOOK.md`
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`

## 参考文件

| 文件 | 用途 |
|------|------|
| `PROJECT_STANDARDS/README.md` | 新项目标准目录说明 |
| `PROJECT_STANDARDS/PLAYBOOK.md` | 新项目搭建流程 |
| `PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md` | FastAPI 工程硬标准 |
| `PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md` | 新项目落地检查清单 |
| `PROJECT_STANDARDS/IMPROVEMENT_LOOP.md` | 标准演进机制 |
| `PROJECT_STANDARDS/registry.yaml` | 项目注册表与模板字段 |
