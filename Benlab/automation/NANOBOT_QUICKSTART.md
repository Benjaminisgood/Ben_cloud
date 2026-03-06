# Nanobot CLI 快速使用（Benlab）

你当前使用的是命令行版 Nanobot，推荐通过 action mapping 调用 Benlab API。

## 1) 先启动 Benlab API

在 Benlab 项目根目录执行：

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benlab
make dev
```

保持这个终端不要关闭。

## 2) Nanobot 要用的文件

- 专用 action mapping：`/Users/ben/Desktop/myapp/Ben_cloud/Benlab/automation/nanobot_action_mapping.json`
- 通用接口索引：`/Users/ben/Desktop/myapp/Ben_cloud/Benlab/automation/api_index.json`
- OpenAPI：`/Users/ben/Desktop/myapp/Ben_cloud/Benlab/automation/openapi.json`

## 3) 最小可用命令（直接复制）

```bash
nanobot agent -m "
你是本地自动化助手。
请先读取文件 /Users/ben/Desktop/myapp/Ben_cloud/Benlab/automation/nanobot_action_mapping.json。
然后按其中的 publish_post_flow 执行：
1) health_check
2) auth_login（账号: YOUR_USER, 密码: YOUR_PASS）
3) account_me
4) create_post_text（text: Benlab 自动化巡检完成, visibility: private, tags: [nanobot,daily]）
5) list_posts(limit=5)
最后仅返回：新帖子 id、created_at、preview。
"
```

## 4) 先做连通性测试

```bash
nanobot agent -m "请调用exec工具执行: curl -sS http://127.0.0.1:9000/health" --no-markdown
```

预期：`{"status":"ok"}`。

## 5) 常见问题

- `401 Unauthorized`
  - 登录态失效，重新执行 `auth_login`，再执行 `account_me` 验证。
- `连接 127.0.0.1:9000 失败`
  - Benlab API 未启动，回到第 1 步。
- `403 Forbidden`
  - 普通账号调用了 admin 能力。
- `400 direct upload not available`
  - 直传开关未启用（`DIRECT_OSS_UPLOAD_ENABLED=false`）。

## 6) 常用模板

### 模板 A：发帖

```text
读取 /Users/ben/Desktop/myapp/Ben_cloud/Benlab/automation/nanobot_action_mapping.json，
执行 publish_post_flow，登录账号 USER，密码 PASS，
帖子文本为“今天总结：...”，可见性 private，标签 [nanobot,auto]。
返回帖子 id。
```

### 模板 B：评论

```text
读取 /Users/ben/Desktop/myapp/Ben_cloud/Benlab/automation/nanobot_action_mapping.json，
登录后执行 comment_flow，record_id=123，comment_body="收到，已跟进"。
返回评论 id。
```
