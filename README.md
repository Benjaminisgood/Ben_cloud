# Ben_cloud

Ben_cloud 是一个多应用工作区。根目录负责统一调度、联合测试、跨项目规则和项目清单同步；具体业务实现与执行细则以各子应用自己的 `AGENTS.md` 和 `README.md` 为准。

工作区根路径：

```text
/Users/ben/Desktop/myapp/Ben_cloud
```

## 根目录职责

- `AGENTS.md`：根级调度入口、路由策略、跨项目强制规则
- `README.md`：工作区总览、统一命令、当前项目清单
- `Ben.sh`：统一启停脚本，自动发现所有带 `<dirname>.sh` 的子应用
- `Makefile`：跨项目 `test` / `check` / `ci` / `migrate-smoke` 聚合入口
- `PROJECT_STANDARDS/`：仅用于未来新项目搭建或重建级改造

## 当前应用清单

| 应用 | 默认端口 | SSO | 主要职责 | 启动脚本 | 文档入口 |
|------|----------|-----|----------|----------|----------|
| `Benbot` | `80` | 中枢 | 统一门户、SSO、健康监控、子应用控制 | `Benbot/benbot.sh` | `Benbot/AGENTS.md`、`Benbot/README.md` |
| `Benoss` | `8000` | 是 | 学习小组记录系统、文件存档与 AI 摘要 | `Benoss/benoss.sh` | `Benoss/AGENTS.md`、`Benoss/README.md` |
| `Benusy` | `8100` | 是 | 达人运营协作平台，覆盖任务、审核、结算 | `Benusy/benusy.sh` | `Benusy/AGENTS.md`、`Benusy/README.md` |
| `Benome` | `8200` | 是 | 民宿房源、预订、入住管理 | `Benome/benome.sh` | `Benome/AGENTS.md`、`Benome/README.md` |
| `Bensci` | `8300` | 是 | 文献元信息提取、聚合、导出与补全任务调度 | `Bensci/bensci.sh` | `Bensci/AGENTS.md`、`Bensci/README.md` |
| `Benfer` | `8500` | 是 | 剪贴板与文件中转，支持上传与断点续传 | `Benfer/benfer.sh` | `Benfer/AGENTS.md`、`Benfer/README.md` |
| `Benben` | `8600` | 是 | Markdown 在线编辑、模板写作、导出 | `Benben/benben.sh` | `Benben/AGENTS.md`、`Benben/README.md` |
| `Benfast` | `8700` | 是 | 文档站、RBAC、FastAPI 后端模板 | `Benfast/benfast.sh` | `Benfast/AGENTS.md`、`Benfast/README.md` |
| `Benprefs` | `8800` | 是 | 偏好档案、网站习惯、偏好确认板 | `Benprefs/benprefs.sh` | `Benprefs/AGENTS.md`、`Benprefs/README.md` |
| `Benhealth` | `8900` | 是 | 健康仪表、运动轨迹、身体指标、健康观察 | `Benhealth/benhealth.sh` | `Benhealth/AGENTS.md`、`Benhealth/README.md` |
| `Benlab` | `9000` | 是 | 实验室管理、成员、活动与物资 | `Benlab/benlab.sh` | `Benlab/AGENTS.md`、`Benlab/README.md` |
| `Benfinance` | `9100` | 是 | 财务洞察、账户、流水、预算与资金决策 | `Benfinance/benfinance.sh` | `Benfinance/AGENTS.md`、`Benfinance/README.md` |
| `Benjournal` | `9200` | 是 | 语音日记、归档合并、自动转写 | `Benjournal/benjournal.sh` | `Benjournal/AGENTS.md` |
| `Benphoto` | `9300` | 是 | OSS 照片展示、每日随机桌面、垃圾桶回收 | `Benphoto/benphoto.sh` | `Benphoto/AGENTS.md`、`Benphoto/README.md` |
| `Benvinyl` | `9400` | 是 | 音频节目展示、每日黑胶节目单 | `Benvinyl/benvinyl.sh` | `Benvinyl/AGENTS.md`、`Benvinyl/README.md` |
| `Benreel` | `9500` | 是 | 视频放映站、每日胶卷节目单 | `Benreel/benreel.sh` | `Benreel/AGENTS.md`、`Benreel/README.md` |
| `Bencred` | `9600` | 否 | 凭证保险箱，管理密钥、密码、令牌 | `Bencred/bencred.sh` | `Bencred/AGENTS.md` |
| `Benlink` | `9700` | 否 | 链接收藏、网页整理与追踪 | `Benlink/benlink.sh` | `Benlink/AGENTS.md` |
| `Benself` | `9800` | 是 | 数字我闭环、agent context、confirmed facts、Graphiti | `Benself/benself.sh` | `Benself/AGENTS.md`、`Benself/README.md` |

说明：

- `Ben.sh` 当前可自动发现以上 19 个项目，因为它们都提供了根目录启动脚本。
- `Benjournal`、`Bencred`、`Benlink` 当前以 `AGENTS.md` 为主要项目说明入口；如果后续补齐 `README.md`，应同步更新本表。
- `Benfer` 的运行脚本与 `.env.example` 默认端口是 `8500`，但 `Benbot` 注册表默认 URL 仍是 `8400`；若调整门户跳转或健康检查，必须同步两边配置。

## 文档优先级

1. 根级调度与跨项目规则：`AGENTS.md`
2. 子应用执行细则：各项目目录下 `AGENTS.md`
3. 子应用使用说明：各项目目录下 `README.md`
4. 工作区总览与统一命令：本文件
5. `PROJECT_STANDARDS/` 仅用于新项目搭建或重建级改造

## 统一运维

统一调度命令：

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud
./Ben.sh start all
./Ben.sh status all
./Ben.sh restart benome
./Ben.sh logs benbot
./Ben.sh ip benfinance
./Ben.sh open
```

`Ben.sh` 的当前行为：

- 自动发现根目录下所有满足 `<DirName>/<dirname>.sh` 的子项目
- 启动 `all` 时，非 `Benbot` 项目先启动，`Benbot` 最后启动
- `start all` 完成后自动打开 `Benbot` 门户
- `status all` 会汇总各项目状态、端口和 PID

单项目开发：

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/<project>
make install
make db-upgrade
make dev
```

补充：

- 并非每个项目都把 `Makefile` 放在项目根目录。`Bencred` 和 `Benlink` 的测试入口目前位于各自 `apps/api` 子目录。
- 具体端口、环境变量、脚本命令，以子项目文档和 `.env.example` 为准。

## Benbot 注册表

`Benbot` 当前注册表文件：

```text
Benbot/apps/api/src/benbot_api/core/config.py
```

当前已注册的 18 个子应用：

- `benoss`
- `benlab`
- `benusy`
- `benome`
- `bensci`
- `benfer`
- `benben`
- `benfast`
- `bencred`
- `benlink`
- `benprefs`
- `benhealth`
- `benfinance`
- `benself`
- `benjournal`
- `benphoto`
- `benvinyl`
- `benreel`

注册表注意事项：

- 除 `Bencred`、`Benlink` 外，其余已注册子应用当前都以 `/auth/sso` 作为默认 SSO 入口。
- `Bencred`、`Benlink` 当前在 `Benbot` 中配置为非 SSO 直达入口。
- 新增项目时，除了补文档，还必须同步更新这里的 `get_projects()`。

## SSO 路径

当前默认 SSO 流程：

```text
浏览器
  -> Benbot /login
  -> Benbot /goto/{project_id}
  -> 子应用 /auth/sso?token=...
```

说明：

- `Benbot` 负责生成短时 HMAC-SHA256 签名 token，子应用负责校验并建立本地会话。
- `Bencred`、`Benlink` 当前不走这条默认 SSO 路径，而是按注册表配置走非 SSO 直达入口。
- 共享密钥必须在各项目 `.env` 中显式配置，不能使用弱默认值。

## 测试与 CI

根目录命令：

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud
make test
make check
make ci
make migrate-smoke
```

当前根 `Makefile` 的真实覆盖范围：

- `make test`：覆盖全部 19 个项目；其中 `Bencred` 走 `Bencred/apps/api test`，`Benlink` 走 `Benlink/apps/api test`
- `make check`：当前覆盖 17 个项目，暂未包含 `Bencred`、`Benlink`
- `make migrate-smoke`：当前覆盖 13 个已标准化迁移入口的项目
- `make ci`：等于 `make check && make migrate-smoke`

执行规则：

- 单应用改动：优先执行该项目文档要求的测试命令，通常为项目根 `make test`
- 根级改动或跨应用改动：回到根目录执行 `make test`
- `make check` 适合作为快速自检，不能替代 `make test`

## 新增项目后需要同步的地方

新增、移除或重命名子应用时，至少同步以下位置：

1. 根 `AGENTS.md` 的路由表和项目清单
2. 本文件的应用总览、测试矩阵、目录结构
3. `Benbot/apps/api/src/benbot_api/core/config.py` 的注册表
4. 根 `Makefile` 的聚合目标
5. 子项目自己的 `AGENTS.md`、`README.md`、`.env.example`
6. 若提供统一启停能力，确保 `<project>/<project>.sh` 可被 `Ben.sh` 自动发现

## 目录结构

```text
Ben_cloud/
├── AGENTS.md
├── README.md
├── Makefile
├── Ben.sh
├── Benben/
├── Benbot/
├── Bencred/
├── Benfast/
├── Benfer/
├── Benfinance/
├── Benhealth/
├── Benjournal/
├── Benlab/
├── Benlink/
├── Benome/
├── Benoss/
├── Benphoto/
├── Benprefs/
├── Benreel/
├── Bensci/
├── Benself/
├── Benusy/
├── Benvinyl/
└── PROJECT_STANDARDS/
```
