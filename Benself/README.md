# Benself

Benself 是 Ben_cloud 的数字我闭环站点。它把 `journals.db` 当作原始事实源，把 `preferences.db`、`health.db`、`finance.db` 当作确认事实层，再把两者整理成给人和 agent 都能消费的自我上下文。

## 当前能力

- 读取根目录 `database/journals.db` 的最近 journal，展示 raw signals。
- 聚合 `preferences.db`、`health.db`、`finance.db`，形成可审计的 confirmed facts。
- 生成一份可直接粘给 AI 的 `prompt_block`，让 agent 更快理解你。
- 支持 Graphiti 预览、同步记录和图搜索；未安装依赖或缺少 `OPENAI_API_KEY` 时会优雅降级。
- 支持本地登录与 `Benbot` 的 `/auth/sso` 单点登录。

## 数据边界

- 原始事实：`/Users/ben/Desktop/myapp/Ben_cloud/database/journals.db`
- 确认事实：`/Users/ben/Desktop/myapp/Ben_cloud/database/preferences.db`、`/Users/ben/Desktop/myapp/Ben_cloud/database/health.db`、`/Users/ben/Desktop/myapp/Ben_cloud/database/finance.db`
- 本站运行数据：`/Users/ben/Desktop/myapp/Ben_cloud/Benself/data/benself.sqlite`
- Graphiti/Kuzu：`/Users/ben/Desktop/myapp/Ben_cloud/Benself/data/graphiti.kuzu`
- 日志目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benself/logs/`

## 主要接口

- `GET /api/dashboard`
- `GET /api/raw-journals`
- `GET /api/confirmed-facts`
- `GET /api/agent-context`
- `POST /api/graph-sync-runs`
- `GET /api/graph-search?q=...`

## 启动

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benself
./benself.sh init-env
./benself.sh install
./benself.sh start
```

默认地址：`http://127.0.0.1:9800`

## Graphiti 说明

- 项目默认开启 Graphiti 功能位。
- 真正执行同步与搜索还需要：
  - 已安装依赖：`make install`
  - 环境里存在 `OPENAI_API_KEY`
- 没有满足条件时，Benself 仍然会输出完整的 agent context 预览和同步预览记录。

## 测试

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benself
make test
```
