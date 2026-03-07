# Benfer

Benfer 是 Ben_cloud 的剪贴板与文件中转子应用，负责文本分享、文件上传、分片传输和 OSS 对接，并支持 Benbot SSO 登录。

## 主要能力

- 文本剪贴板保存与分享
- 文件上传与分片上传
- 过期控制与下载访问
- OSS 存储对接
- Benbot SSO 登录接入

## 快速开始

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfer
./benfer.sh install
./benfer.sh start
./benfer.sh status
```

默认地址：
- Web: [http://127.0.0.1:8500](http://127.0.0.1:8500)
- Health: [http://127.0.0.1:8500/health](http://127.0.0.1:8500/health)

停止与日志：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfer
./benfer.sh stop
./benfer.sh logs
```

## Makefile 命令

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfer
make install
make test
make check
make db-current
make db-upgrade
```

## 关键配置

推荐从 `.env.example` 复制：

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfer
cp .env.example .env
```

重点变量：
- `PORT=8500`
- `DATABASE_URL=sqlite:///./data/benfer.db`
- `SSO_SECRET=replace_with_shared_sso_secret`
- `NANOBOT_API_TOKEN=replace_with_random_api_token`
- `MAX_FILE_SIZE_BYTES`
- `ALLOWED_FILE_CONTENT_TYPES`
- `CLIPBOARD_STORAGE_PATH`

安全要求：
- `SSO_SECRET` 必须与 Benbot 完全一致
- 所有密钥必须显式配置，不能使用弱默认值
- 文件大小、类型白名单和 owner check 不能绕过

## 目录结构

```text
Benfer/
├── app.py
├── benfer.sh
├── Makefile
├── AGENTS.md
├── apps/
│   ├── api/
│   │   ├── src/benfer_api/
│   │   └── alembic/
│   └── web/
├── tests/
├── data/
└── logs/
```

## 更多文档

- 执行边界与修改约束：`/Users/ben/Desktop/Ben_cloud/Benfer/AGENTS.md`
