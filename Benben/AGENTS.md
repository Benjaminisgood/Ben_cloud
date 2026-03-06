# AGENTS.md - Benben

## 职责定位

Benben 是实验室成员临时笔记与模板写作工具，负责：

1. Markdown 文档在线编辑与预览
2. 通过 Benbot SSO 登录接入
3. 模板化文档创建（周报/会议/实验记录）
4. 文档存储到 OSS `benben` 前缀
5. 审计日志记录（写入 `logs/benben_audit.log`）

## 代码边界

- 主代码目录：`/Users/ben/Desktop/Ben_cloud/Benben`
- FastAPI 代码：`Benben/apps`
- 前端模板：`Benben/templates/editor.html`

## Agent 修改约束

1. 所有后端改动优先落在 `apps` 分层目录（`core/schemas/services/api/web`）。
2. 禁止将密钥硬编码进代码，必须走 `.env`。
3. 与 SSO 相关的 token 校验逻辑变更必须评估 Benbot 兼容性。
4. 对 `/api/files` 的改动不得破坏版本并发保护（`base_version` / `version_conflict`）。
5. 上传逻辑改动必须保留大小/MIME/扩展名/频率限制。
6. 任何写操作应保留审计日志记录。
7. 变更完成必须运行：`make check`。

## 常用命令

```bash
./benben.sh install
./benben.sh start
./benben.sh stop
./benben.sh restart
./benben.sh status
./benben.sh logs
./benben.sh check
./benben.sh init-env

make test
make check
```
