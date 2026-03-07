# 关键接口清单

## 健康检查

- `GET /health`：服务存活检查。

## SSO 入口

- `GET /auth/sso?token=...`：接收 Benbot 签发 token 并登录。

## 门户入口

- `GET /portal`：登录后跳转到 `/kb/`。

## 文档站入口

- `GET /kb/`：文档首页。
- `GET /kb/{doc_path}`：文档静态资源与页面。

## 认证信息

- `GET /auth/me`：查看当前会话用户。
- `POST /auth/logout`：退出当前会话。
