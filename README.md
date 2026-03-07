# Ben_cloud

Ben_cloud 是一个多应用工作区。根目录负责统一调度、联合测试与跨项目规则；具体业务和执行细则以各子应用自己的 `AGENTS.md` 与 `README.md` 为准。

## 工作区总览

| 应用 | 默认端口 | 主要职责 | 启动入口 |
|------|----------|----------|----------|
| `Benbot` | `80` | 门户、SSO、健康监控、子应用控制 | `Benbot/benbot.sh` |
| `Benoss` | `8000` | 学习、协作、团队记录 | `Benoss/benoss.sh` |
| `Benusy` | `8100` | 达人运营、任务审核、结算 | `Benusy/benusy.sh` |
| `Benome` | `8200` | 民宿房源与预订 | `Benome/benome.sh` |
| `Bensci` | `8300` | 文献元信息聚合、抓取、导出 | `Bensci/bensci.sh` |
| `Benfer` | `8500` | 剪贴板与文件中转 | `Benfer/benfer.sh` |
| `Benben` | `8600` | Markdown 编辑、模板写作 | `Benben/benben.sh` |
| `Benfast` | `8700` | 文档站、RBAC、后端模板 | `Benfast/benfast.sh` |
| `Benlab` | `9000` | 实验室管理 | `Benlab/benlab.sh` |

补充：
- `Benbot` 当前项目注册表已包含：`Benoss`、`Benusy`、`Benome`、`Bensci`、`Benfer`、`Benben`、`Benfast`、`Benlab`。
- `Benfer` 脚本默认端口是 `8500`；如果本地 `.env` 覆盖了 `PORT`，需要同步检查 `Benbot` 里的跳转与健康检查配置。

## 文档优先级

1. 根级调度与跨项目规则：`/Users/ben/Desktop/Ben_cloud/AGENTS.md`
2. 子应用执行细则：各项目目录下 `AGENTS.md`
3. 子应用使用说明：各项目目录下 `README.md`
4. `PROJECT_STANDARDS/` 仅用于新项目搭建或重建级改造

## 启动与运维

统一调度：

```bash
cd /Users/ben/Desktop/Ben_cloud
./Ben.sh start all
./Ben.sh status all
./Ben.sh restart benome
./Ben.sh logs benbot
./Ben.sh ip benusy
./Ben.sh open
```

单项目开发：

```bash
cd /Users/ben/Desktop/Ben_cloud/<project>
make install
make db-upgrade
make dev
```

说明：
- `Benben`、`Benfer`、`Bensci`、`Benfast` 也已接入各自的 `Makefile`，不必再按“无 Makefile 项目”处理。
- 具体端口、环境变量和脚本命令，以子项目文档为准。

## 测试与 CI

根目录命令：

```bash
cd /Users/ben/Desktop/Ben_cloud
make test
make check
make ci
```

当前根 `Makefile` 已覆盖全部 9 个子应用：
- `Benbot`
- `Benben`
- `Benlab`
- `Benoss`
- `Benusy`
- `Benfer`
- `Benfast`
- `Bensci`
- `Benome`

规则：
- 单应用改动：先跑对应应用的 `make test`
- 跨应用改动：回到根目录跑 `make test`

## SSO 路径

```text
浏览器
  -> Benbot /login
  -> Benbot /goto/{project_id}
  -> 子应用 /auth/sso?token=...
```

Token 为短时 HMAC-SHA256 签名，子应用负责校验并建立本地会话。共享密钥必须在各项目 `.env` 中显式配置，不能使用弱默认值。

## 目录结构

```text
Ben_cloud/
├── AGENTS.md
├── README.md
├── Makefile
├── Ben.sh
├── Benbot/
├── Benben/
├── Benfer/
├── Benlab/
├── Benome/
├── Benoss/
├── Bensci/
├── Benusy/
├── Benfast/
└── PROJECT_STANDARDS/
```
