# Ben_cloud

Ben_cloud 是一个多应用工作区。根目录负责统一调度、联合测试与跨项目规范；各子应用独立开发与运维。

> 文档状态：2026-03-06（已按仓库内 `AGENTS.md`、`*.sh`、`Makefile`、代码入口核对）

## 子应用矩阵（当前）

| 应用 | 端口（默认） | 主要职责 | 主要入口 |
|------|--------------|----------|----------|
| `Benbot` | `80` | 门户、SSO 中枢、健康监控、子应用控制 | `Benbot/benbot.sh` |
| `Benoss` | `8000` | 学习协作与记录 | `Benoss/benoss.sh` |
| `Benusy` | `8100` | 达人运营任务/审核/结算 | `Benusy/benusy.sh` |
| `Benome` | `8200` | 民宿房源与预订 | `Benome/benome.sh` |
| `Bensci` | `8300` | 文献元信息聚合与任务处理 | `Bensci/bensci.sh` |
| `Benfer` | `8500` | 剪贴板与文件中转 | `Benfer/benfer.sh` |
| `Benben` | `8600` | Markdown 编辑与模板写作 | `Benben/benben.sh` |
| `Benlab` | `9000` | 实验室管理 | `Benlab/benlab.sh` |

补充：
- `Benbot` 的项目注册表（`Benbot/apps/api/src/benbot_api/core/config.py`）当前已包含：`Benoss/Benusy/Benome/Bensci/Benfer/Benben/Benlab`。
- `Benfer/.env` 当前设置 `PORT=8400`，与 `Benbot` 默认 `BENFER_*_URL` 的 `8500` 存在差异；如需门户跳转与健康检查一致，需对齐端口。

## SSO 路径（当前）

```text
浏览器
  -> Benbot /login
  -> Benbot /goto/{project_id}
  -> 子应用 /auth/sso?token=...
```

token 为短时 HMAC-SHA256 签名（默认 30 秒），子应用自行校验并建立本地会话。

## 启动与运维

根级统一调度（推荐）：

```bash
cd /Users/ben/Desktop/Ben_cloud
./Ben.sh start all
./Ben.sh status all
./Ben.sh restart benome
./Ben.sh logs benbot
./Ben.sh ip benusy
./Ben.sh open
```

子应用单独开发（有 Makefile 的项目）：

```bash
cd /Users/ben/Desktop/Ben_cloud/<Benbot|Benlab|Benoss|Benusy|Benome>
make install
make db-upgrade
make dev
```

无根级 Makefile 接入的项目：

```bash
# Benben
cd /Users/ben/Desktop/Ben_cloud/Benben
./benben.sh install && ./benben.sh start

# Benfer
cd /Users/ben/Desktop/Ben_cloud/Benfer
./benfer.sh install && ./benfer.sh start

# Bensci
cd /Users/ben/Desktop/Ben_cloud/Bensci
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./bensci.sh start
```

## 测试与 CI（当前真实范围）

根目录：

```bash
cd /Users/ben/Desktop/Ben_cloud
make test
make ci
```

当前根 `Makefile` 仅覆盖 5 个应用：`Benbot`、`Benlab`、`Benoss`、`Benusy`、`Benome`。

其余应用当前建议：
- `Benben`：`cd Benben && make test`
- `Bensci`：`cd Bensci && pytest -q`（需本地具备 pytest）
- `Benfer`：当前无内置自动化测试目标，至少执行启动与 `/health` 冒烟检查

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
└── PROJECT_STANDARDS/
```

## 文档与规则优先级

1. 根级调度与通用规则：`/Users/ben/Desktop/Ben_cloud/AGENTS.md`
2. 子应用执行细则：各项目目录下 `AGENTS.md`
3. `PROJECT_STANDARDS/` 仅用于新项目搭建或重建级改造，不覆盖现有项目本地规则
