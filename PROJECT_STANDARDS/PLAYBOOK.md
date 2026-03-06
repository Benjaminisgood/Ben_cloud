# New Project Bootstrap Playbook

本文件只用于 **Ben_cloud 新子项目搭建**。  
不用于现有子项目的日常任务调度与执行流程管理。

现有项目运行与改造规则，请只看各项目自己的 `AGENTS.md`。

## 1. 适用范围

仅当任务满足以下任一条件时使用本文件：

1. 在 Ben_cloud 中新增一个子项目（新目录、新端口、新数据库）。
2. 对旧项目做“重建级”改造（目录、分层、迁移机制整体重构）。
3. 需要定义统一脚手架模板并沉淀为标准。

## 2. 新项目启动步骤

1. 确认项目基础信息：`id`、`name`、`mission`、`port`、SSO 接入策略。
2. 按 `FASTAPI_ENGINEERING_STANDARD.md` 建立标准目录与分层骨架。
3. 先建 Alembic baseline，再建业务模型；禁止先 `create_all` 后补迁移。
4. 落地最小可运行面：
   - `GET /health`
   - 基础认证路径（本地登录 + SSO 回调如适用）
   - 至少 1 条核心业务读写链路（route/service/repository）
5. 补齐测试与门禁：
   - `pytest -q`
   - `compileall`
   - `alembic upgrade head` 冒烟
6. 编写项目内 `AGENTS.md`，明确该项目的唯一真实代码路径、约束、测试命令。
7. 在 `registry.yaml` 注册项目并同步 Benbot 子应用配置。

## 3. 强制交付清单（DoD）

1. 目录、分层、命名符合统一标准。
2. 所有 schema 变更可由 Alembic 完整重放。
3. `make test` 通过，且关键路径有正反用例。
4. 运行态落盘只在 `data/` 与 `logs/`。
5. 默认管理员账号与 SSO 密钥策略符合 Ben_cloud 约定。
6. 项目级 `AGENTS.md` 已包含运维与回归指令。

## 4. 非目标（明确排除）

1. 不负责现有项目任务路由。
2. 不定义“每次任务都要执行”的通用操作手册。
3. 不替代各子项目自己的 `AGENTS.md`。
