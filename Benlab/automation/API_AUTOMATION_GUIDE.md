# Benlab API 自动化调用指南（OpenClaw / Nanobot）

本项目 API 可以被本地自动化工具直接调用，推荐流程是：

1. 登录获取 `session` Cookie
2. 复用同一 Cookie 发起后续 `/api/*` 请求
3. 每轮任务先调用 `/api/account` 验证登录态
4. 遇到 `401` 自动重新登录后重试

- 基础地址：`http://127.0.0.1:9000`
- 健康检查：`GET /health`
- 机器索引：`automation/api_index.json`
- 全量规范：`automation/openapi.json`

## 1. 认证方式

当前是 **Session Cookie 认证**（不是 Bearer Token）。

### 登录（必须先做）

```bash
curl -i -c /tmp/benlab.cookie \
  -X POST 'http://127.0.0.1:9000/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'username=YOUR_USER&password=YOUR_PASS&next=/'
```

Benlab 登录成功通常返回 `303`，并在 Cookie Jar 中写入 `session`。

### 认证态请求

```bash
curl -b /tmp/benlab.cookie 'http://127.0.0.1:9000/api/account'
```

### 退出

```bash
curl -b /tmp/benlab.cookie 'http://127.0.0.1:9000/logout'
```

## 2. 发帖子（核心）

### 发文本帖子

```bash
curl -b /tmp/benlab.cookie \
  -X POST 'http://127.0.0.1:9000/api/records' \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "这是由自动化工具发布到 Benlab 的帖子",
    "visibility": "private",
    "tags": ["automation", "nanobot"]
  }'
```

说明：
- `text`：必填（若不传文件）
- `visibility`：`public` 或 `private`，默认 `private`
- `tags`：可传数组或逗号分隔字符串

### 拉取帖子列表

```bash
curl -b /tmp/benlab.cookie \
  'http://127.0.0.1:9000/api/records?limit=20'
```

返回统一结构：

```json
{
  "items": [...],
  "has_more": true
}
```

翻页使用 `before_id=<last_id>`。

### 更新帖子

```bash
curl -b /tmp/benlab.cookie \
  -X PATCH 'http://127.0.0.1:9000/api/records/123' \
  -H 'Content-Type: application/json' \
  -d '{"text":"更新后的文本","tags":["updated"]}'
```

### 删除帖子

```bash
curl -b /tmp/benlab.cookie \
  -X DELETE 'http://127.0.0.1:9000/api/records/123'
```

## 3. 评论自动化

### 发评论

```bash
curl -b /tmp/benlab.cookie \
  -X POST 'http://127.0.0.1:9000/api/records/123/comments' \
  -H 'Content-Type: application/json' \
  -d '{"body":"自动评论内容"}'
```

### 拉评论

```bash
curl -b /tmp/benlab.cookie \
  'http://127.0.0.1:9000/api/records/123/comments'
```

## 4. 通知聚合接口

### 拉取通知记录

```bash
curl -b /tmp/benlab.cookie \
  'http://127.0.0.1:9000/api/notice/records?limit=50'
```

### 渲染通知 HTML

```bash
curl -b /tmp/benlab.cookie \
  'http://127.0.0.1:9000/api/notice/render'
```

## 5. 直传能力（默认关闭）

Benlab 默认 `DIRECT_OSS_UPLOAD_ENABLED=false`，此时：
- `GET /api/direct-upload/token` 返回 `400`
- `POST /api/direct-upload/confirm` 返回 `400`

启用后可走：
1. `GET /api/direct-upload/token`
2. 客户端执行对象上传（按返回 `put_url`）
3. `POST /api/direct-upload/confirm`

## 6. 管理员能力（仅 admin）

- `GET /api/admin/settings`
- `PUT /api/admin/settings`

普通账号调用会得到 `403`。

## 7. OpenClaw / Nanobot 推荐执行策略

1. 启动前先探活 `GET /health`。
2. 每轮任务先调用 `GET /api/account` 验证认证。
3. 如果收到 `401`，自动重新登录一次再重试。
4. 写操作（POST/PATCH/DELETE）记录响应里的 `id`，用于回滚和审计。
5. 分页接口循环直到 `has_more=false`。

## 8. 常见错误码

- `400 Bad Request`：参数不合法（例如评论为空、token 无效、直传未启用）。
- `401 Unauthorized`：未登录或会话失效。
- `403 Forbidden`：权限不足（常见于 admin 接口）。
- `404 Not Found`：资源不存在或对当前用户不可见。
