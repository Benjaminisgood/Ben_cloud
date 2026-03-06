# Benoss API 自动化调用指南（OpenClaw / Nanobot）

本项目 API 可以被本地自动化工具直接调用，推荐流程是：

1. 登录获取 `session` Cookie
2. 复用同一 Cookie 发起后续 `/api/*` 请求
3. 遇到 `401` 自动重新登录后重试

- 基础地址：`http://127.0.0.1:8000`
- 健康检查：`GET /health`
- 机器索引：`automation/api_index.json`
- 全量规范：`automation/openapi.json`

## 1. 认证方式

当前是 **Session Cookie 认证**（不是 Bearer Token）。

### 登录（必须先做）

```bash
curl -i -c /tmp/benoss.cookie \
  -X POST 'http://127.0.0.1:8000/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'username=YOUR_USER&password=YOUR_PASS&next=/'
```

成功时通常返回 `302`，并在 Cookie Jar 中写入 `session`。

### 认证态请求

```bash
curl -b /tmp/benoss.cookie 'http://127.0.0.1:8000/api/account'
```

### 退出

```bash
curl -b /tmp/benoss.cookie 'http://127.0.0.1:8000/logout'
```

## 2. 发帖子（核心）

### 发文本帖子

```bash
curl -b /tmp/benoss.cookie \
  -X POST 'http://127.0.0.1:8000/api/records' \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "这是由自动化工具发布的帖子",
    "visibility": "public",
    "tags": ["automation", "nanobot"]
  }'
```

说明：
- `text`：必填（若不传文件）
- `visibility`：`public` 或 `private`，默认 `private`
- `tags`：可传数组或逗号分隔字符串

### 拉取帖子列表

```bash
curl -b /tmp/benoss.cookie \
  'http://127.0.0.1:8000/api/records?limit=20'
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
curl -b /tmp/benoss.cookie \
  -X PATCH 'http://127.0.0.1:8000/api/records/123' \
  -H 'Content-Type: application/json' \
  -d '{"visibility":"private","tags":["updated"]}'
```

### 删除帖子

```bash
curl -b /tmp/benoss.cookie \
  -X DELETE 'http://127.0.0.1:8000/api/records/123'
```

## 3. 评论自动化

### 发评论

```bash
curl -b /tmp/benoss.cookie \
  -X POST 'http://127.0.0.1:8000/api/records/123/comments' \
  -H 'Content-Type: application/json' \
  -d '{"body":"自动评论内容"}'
```

### 拉评论

```bash
curl -b /tmp/benoss.cookie \
  'http://127.0.0.1:8000/api/records/123/comments'
```

## 4. 文件帖子（两种方式）

- 方式 A（简单）：`POST /api/records` 走 `multipart/form-data`，直接带 `file`
- 方式 B（大文件）：
  1. `GET /api/direct-upload/token`
  2. 用返回的 `put_url` 上传对象
  3. `POST /api/direct-upload/confirm` 完成入库

工具侧建议：小文件走 A，大文件走 B。

## 5. 管理员能力（仅 admin）

- `GET/PUT /api/admin/settings`
- `POST /api/digest/daily`
- `POST /api/vector/rebuild`

普通账号调用会得到 `403`。

## 6. OpenClaw / Nanobot 推荐执行策略

1. 启动前先探活 `GET /health`。
2. 每轮任务先验证认证：调用 `GET /api/account`。
3. 如果收到 `401`，自动重新登录一次再重试。
4. 写操作（POST/PATCH/DELETE）要记录响应里的 `id`，用于回滚和审计。
5. 对分页接口循环直到 `has_more=false`。

## 7. 常见错误码

- `400` 参数错误
- `401` 未登录或会话失效
- `403` 权限不足
- `404` 资源不存在
- `500` 服务内部错误
