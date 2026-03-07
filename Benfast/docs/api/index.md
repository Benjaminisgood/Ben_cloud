# API 与集成说明

这个页面面向课题组内部维护人员，描述 Benfast 与 Benbot 的集成约定。

## SSO 约定

- Token 签名算法：`HMAC-SHA256`
- 编码格式：`Base64URL`
- 共享密钥：`SSO_SECRET`（Benbot 与 Benfast 必须一致）

## 本地开发验证

```bash
# 启动文档构建
cd /Users/ben/Desktop/Ben_cloud/Benfast
make docs-build

# 本地预览文档站
make docs-serve
```

## 兼容入口（必须保持）

- `GET /health`
- `GET /auth/sso?token=...`
- `GET /portal`
