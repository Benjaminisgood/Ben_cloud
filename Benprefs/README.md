# Benprefs

Benprefs 是偏好档案站，负责把 `preferences.db` 里的稳定偏好、网站使用倾向和人工确认条目收束成一个可浏览的偏好界面。

![Benprefs 首页](docs/screenshots/homepage.png)

## 当前能力

- 读取根目录 `database/preferences.db`，展示当前偏好与网站偏好。
- 提供一层本地可写的 `focus_entries`，用来承接 journal/agent 抽取后的人工确认结果。
- 支持本地登录与 `Benbot` 的 `/auth/sso` 单点登录。
- 暴露 HTML UI、`/api/dashboard` 和健康检查接口。

## 数据边界

- 只读源数据：`/Users/ben/Desktop/myapp/Ben_cloud/database/preferences.db`
- 本站运行数据：`/Users/ben/Desktop/myapp/Ben_cloud/Benprefs/data/benprefs.sqlite`
- 日志目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benprefs/logs/`

## 页面结构

- 首页：偏好概览、偏好切片、偏好确认板
- 登录页：本地账号密码登录
- SSO 入口：`/auth/sso`

## 启动

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benprefs
./benprefs.sh init-env
./benprefs.sh install
./benprefs.sh start
```

默认地址：`http://127.0.0.1:8800`

## 测试

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benprefs
make test
```
