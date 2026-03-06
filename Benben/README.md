# Benben Markdown 编辑器

Benben 是给实验室成员使用的临时笔记本，支持：
- Markdown 在线编辑与实时预览
- Benbot SSO 登录进入
- 模板一键新建（周报/会议纪要/实验记录）
- 并发版本保护（防止互相覆盖）
- 自动本地草稿与崩溃恢复
- 笔记导出（TXT / Markdown / HTML / PNG 图片）

## 运行前配置

```bash
# 方式一：手动
cp .env.example .env

# 方式二：脚本自动生成
./benben.sh init-env
```

必填环境变量（缺失将拒绝启动）：
- `BENBEN_OSS_ENDPOINT`
- `BENBEN_OSS_ACCESS_KEY_ID`
- `BENBEN_OSS_ACCESS_KEY_SECRET`
- `BENBEN_OSS_BUCKET_NAME`
- `BENBEN_SSO_SECRET`（与 Benbot 一致）
- `BENBEN_SESSION_SECRET_KEY`

## 常用命令

```bash
# 安装依赖
./benben.sh install

# 启动 / 停止 / 重启 / 状态
./benben.sh start
./benben.sh stop
./benben.sh restart
./benben.sh status

# 查看日志
./benben.sh logs

# 运维自检（编译 + readiness）
./benben.sh check

# 初始化 .env（缺失时）
./benben.sh init-env

# 质量检查
make test
make check
```

默认地址：`http://localhost:8600`

## 工程结构约定

- 依赖与打包配置统一放在 `apps/api/pyproject.toml`
- 运行入口仍为根目录 `app.py`，主业务代码在 `apps/`

## 当前能力说明

1. 安全基线
- 密钥全部走环境变量
- `/auth/sso` 验证后建立会话
- `/` 与 `/api/*` 强制鉴权
- 上传限制（MIME/扩展名/大小/频率）

2. 模板功能
- `/api/templates` 返回模板库
- `/api/files/from-template` 支持变量注入（日期、周次、成员、项目）

3. 导出功能
- `/api/export` 支持 `txt` / `md` / `html` 下载
- 页面支持 PNG 图片导出（基于当前编辑内容）

4. 并发保护
- `/api/files/{path}` 返回 `version`
- `/api/files` 保存需带 `base_version`，冲突返回 `409 version_conflict`

5. 草稿恢复
- 浏览器本地草稿自动保存
- 离开页面未保存提醒
- 崩溃后恢复未命名草稿或文件草稿

6. 审计日志
- 写入 `logs/benben_audit.log`（JSONL）
- 记录 `list/read/save/delete/upload/template/export` 操作
- 写接口返回 `operation_id` 并在审计日志中关联 `request_id/operation_id`
- 支持 `BENBEN_AUDIT_LOG_PATH` 与 `BENBEN_AUDIT_MAX_BYTES`（超限自动轮转）

6. 运维健康检查
- `/health`：基础状态与环境信息
- `/health/live`：进程存活探针
- `/health/ready`：配置与日志目录可写性探针（未就绪返回 `503`）
- 每个响应附带 `X-Request-ID` 与 `X-Process-Time-Ms`
