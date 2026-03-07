# 系统运维

本页用于说明 Benfast 文档站在 Ben_cloud 中的运行方式。

## 服务角色

- `Benfast`：课题组文档站主应用（Markdown -> 文档网站）。
- `Benbot`：统一门户与 SSO 入口。

## 登录流

1. 用户从 Benbot 门户点击 Benfast。
2. Benbot 跳转 `Benfast /auth/sso?token=...`。
3. Benfast 校验 token 后建立本地会话。
4. 成功后跳转到文档站首页 `/kb/`。

## 日常运维命令

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
./benfast.sh init-env
./benfast.sh install
./benfast.sh start
./benfast.sh status
./benfast.sh logs
```

生成日期：`2026-03-07`
