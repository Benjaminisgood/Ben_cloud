# AGENTS.md - Ben_cloud Dispatcher

本文件是 Ben_cloud 的根级调度入口。

## 目标

1. 将任务路由到正确子应用或根目录范围。
2. 强制执行跨项目通用安全与工程底线。
3. 明确“新项目标准”与“现有项目规则”的边界。
4. 维护根级文档、统一脚本、Benbot 注册表与测试矩阵的一致性。

## 强制启动序列

每次任务执行必须按此顺序操作：

1. 读本文件。
2. 判断任务属于根目录范围还是某个子应用。
3. 若属于子应用：读目标子应用自己的 `AGENTS.md`。
4. 仅在目标范围内执行；跨应用任务需显式标注边界。

## 根级任务边界

以下任务直接视为 **Ben_cloud 根目录任务**，不强行路由到单个子应用：

- 根级文档维护：`AGENTS.md`、`README.md`
- 统一脚本与联合入口：`Ben.sh`、根 `Makefile`
- 工作区项目清单、路由表、测试矩阵、目录结构同步
- `PROJECT_STANDARDS/` 的目录说明和新项目规范文档维护
- Benbot 子应用注册表与根文档之间的一致性检查

若任务同时涉及根目录和业务子应用：

- 先明确根级部分与子应用部分的边界。
- 分别读取对应子应用 `AGENTS.md` 后再执行。

## 路由策略

| 意图关键词 | 目标范围 |
|-----------|---------|
| 根目录、工作区、统一启动、统一测试、根 README、根 AGENTS、Makefile、Ben.sh、PROJECT_STANDARDS | **Ben_cloud 根目录** |
| 门户、SSO、健康监控、子应用管理、系统运维 | **Benbot** |
| Markdown、笔记、周报、模板、会议纪要、实验记录 | **Benben** |
| 社交、家庭、生活、日程、提醒、亲友 | **Benlab** |
| 学习、协作、团队、复盘、研究、工作 | **Benoss** |
| 达人、任务、审核、结算、运营、分配 | **Benusy** |
| 民宿、房源、预定、预订、入住、退房、锁期 | **Benome** |
| 文献、科研数据、元信息、聚合、抓取 | **Bensci** |
| 剪贴板、文件中转、上传下载、断点续传 | **Benfer** |
| 模板、后端模板、RBAC、管理后台、脚手架 | **Benfast** |
| 凭证、密钥、密码、令牌、secret、OAuth | **Bencred** |
| 链接、网址、收藏、书签、网页元信息 | **Benlink** |
| 偏好、喜好、兴趣、习惯、网站偏好、偏好确认 | **Benprefs** |
| 健康、运动、营养、训练、身体指标、健康观察 | **Benhealth** |
| 财务、预算、账户、流水、储蓄、资金 | **Benfinance** |
| 日记、日志、语音日志、转写、归档、journal | **Benjournal** |
| 自我画像、数字我、agent context、confirmed facts、graphiti | **Benself** |
| 照片、摄影、相册、拍立得、图片展示 | **Benphoto** |
| 音频、播客、节目、黑胶、唱片、音频展示 | **Benvinyl** |
| 视频、放映、胶卷、电视、影片、视频展示 | **Benreel** |

- 意图模糊时：写操作前提出一个简短澄清问题。
- 跨应用任务：拆分为每个应用内的独立步骤执行。
- 根级任务不得替代子应用内的业务实现判断。

## 当前工作区项目

当前根目录已纳入以下项目：

- `Benbot`
- `Benben`
- `Benlab`
- `Benoss`
- `Benusy`
- `Benome`
- `Bensci`
- `Benfer`
- `Benfast`
- `Bencred`
- `Benlink`
- `Benprefs`
- `Benhealth`
- `Benfinance`
- `Benjournal`
- `Benself`
- `Benphoto`
- `Benvinyl`
- `Benreel`

新增、移除或重命名项目时，必须同步检查：

1. 本文件的路由策略与项目清单。
2. 根 `README.md` 的工作区总览、目录结构与测试说明。
3. `Benbot/apps/api/src/benbot_api/core/config.py` 中的 `get_projects()` 注册表。
4. 根 `Makefile` 的 `test`、`check`、`ci`、`migrate-smoke` 覆盖范围。
5. 是否存在 `<DirName>/<dirname>.sh`，以保证 `Ben.sh` 自动发现正常工作。

## 新项目标准边界（关键）

`PROJECT_STANDARDS/` 的唯一作用是：**未来新增项目搭建时的统一规范来源**。

- 仅在“新项目搭建/重建级改造”场景使用 `PROJECT_STANDARDS/`。
- 现有项目的执行细则、业务规则、约束说明，全部以各项目自身 `AGENTS.md` 为准。

## 全局强制规则

1. 不得绕过子应用 `AGENTS.md` 中的约束。
2. Schema 变更仅允许通过 Alembic；禁止 ad-hoc 直接修改数据库 schema。
3. 优先通过 API / 服务层变更，不直接 patch 数据。
4. 任务完成前必须跑验证：
   - 根级改动或跨应用改动：在 `/Users/ben/Desktop/myapp/Ben_cloud` 执行根目录 `make test`。
   - 单应用改动：优先执行该应用 `AGENTS.md` 或 `README.md` 规定的测试命令；多数项目为项目根 `make test`。
   - `Bencred`、`Benlink` 这类测试入口在子目录的项目，按其子应用文档执行，不假定项目根一定有 `Makefile`。
   - `make check` 只能作为快速自检，不替代 `make test`。
5. 写操作（`POST` / `PATCH` / `DELETE`）须记录返回 ID，用于审计和回滚。
6. 认证失败处理：
   - `401`：重新登录一次后再重试一次。
   - 连续 `401` 或任何 `403`：停止并上报。
7. 如涉及新项目搭建或重建级改造，必须遵循：
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/PLAYBOOK.md`
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md`
   - `/Users/ben/Desktop/myapp/Ben_cloud/PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md`

## 参考文件

| 文件 | 用途 |
|------|------|
| `README.md` | 根级工作区总览、启动/测试入口、当前项目清单 |
| `PROJECT_STANDARDS/README.md` | 新项目标准目录说明 |
| `PROJECT_STANDARDS/PLAYBOOK.md` | 新项目搭建流程 |
| `PROJECT_STANDARDS/FASTAPI_ENGINEERING_STANDARD.md` | FastAPI 工程硬标准 |
| `PROJECT_STANDARDS/FASTAPI_UNIFICATION_PROGRESS.md` | 新项目落地检查清单 |
| `PROJECT_STANDARDS/IMPROVEMENT_LOOP.md` | 标准演进机制 |
| `PROJECT_STANDARDS/registry.yaml` | 项目注册表与模板字段 |
