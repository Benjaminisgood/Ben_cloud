# Benome OSS 配置快速指南

## 📍 配置文件位置

```
/root/Ben_cloud/Benome/.env
```

## 🔑 需要填写的配置

打开 `.env` 文件，替换以下两个值为你的实际阿里云 OSS 凭证：

```bash
# ❌ 示例值（需要替换）
ALIYUN_OSS_ACCESS_KEY_ID=your-access-key-id
ALIYUN_OSS_ACCESS_KEY_SECRET=your-access-key-secret

# ✅ 替换为你的真实凭证
ALIYUN_OSS_ACCESS_KEY_ID=LTAI5tXXXXXXXXXXXXXXXX
ALIYUN_OSS_ACCESS_KEY_SECRET=XXXXXXXXXXXXXXXXXXXXXXXX
```

## 📋 完整配置说明

```bash
# 阿里云 OSS 配置
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com    # OSS 端点（杭州）
ALIYUN_OSS_ACCESS_KEY_ID=你的 AccessKey ID           # 需要替换
ALIYUN_OSS_ACCESS_KEY_SECRET=你的 AccessKey Secret   # 需要替换
ALIYUN_OSS_BUCKET=benome                            # Bucket 名称
ALIYUN_OSS_PREFIX=benome                            # 文件前缀路径

# 可选：公共访问 URL（如果 Bucket 是公共读）
# ALIYUN_OSS_PUBLIC_BASE_URL=https://benome.oss-cn-hangzhou.aliyuncs.com

# OSS 直传配置
OSS_DIRECT_UPLOAD_ENABLED=1                         # 启用直传
OSS_DIRECT_UPLOAD_EXPIRES_SECONDS=900               # 过期时间（15 分钟）
OSS_DIRECT_UPLOAD_TOKEN_MAX_AGE_SECONDS=1800        # Token 最大有效期（30 分钟）

# 回源配置
OSS_REMOTE_FAILOVER_LOCAL=1                         # 远程失败时回源到本地

# 文件大小限制
MAX_CONTENT_LENGTH=1073741824                       # 最大 1GB
```

## 🔐 如何获取 OSS 凭证

### 步骤 1：登录阿里云控制台

访问：https://ram.console.aliyun.com/

### 步骤 2：创建 AccessKey

1. 在左侧菜单选择"身份管理" → "用户"
2. 点击"创建用户"
3. 填写用户名（如：benome-oss）
4. 访问方式选择"OpenAPI 调用访问"
5. 点击"确定"
6. 保存生成的 AccessKey ID 和 AccessKey Secret

### 步骤 3：授予 OSS 权限

1. 在用户列表中找到刚创建的用户
2. 点击"添加权限"
3. 选择"系统策略"
4. 搜索并选择"AliyunOSSFullAccess"
5. 点击"确定"

### 步骤 4：创建 OSS Bucket

1. 访问：https://oss.console.aliyun.com/
2. 点击"创建 Bucket"
3. Bucket 名称：`benome`
4. 地域：选择离你最近的（如：华东 1 杭州）
5. 读写权限：私有（推荐）
6. 点击"确定"

## ✅ 验证配置

### 1. 重启服务

```bash
systemctl restart benome.service
```

### 2. 检查日志

```bash
tail -f /root/Ben_cloud/Benome/logs/benome.log
```

应该看到服务正常启动，没有 OSS 配置错误。

### 3. 测试上传

1. 访问：`http://your-domain:8200/admin/dashboard`
2. 进入媒体管理页面
3. 拖拽一个文件上传
4. 如果成功，说明 OSS 配置正确！

## 🔍 故障排查

### 问题：上传失败，提示 OSS 配置错误

**解决方法：**
1. 检查 `.env` 文件是否存在
2. 确认 AccessKey ID 和 Secret 填写正确
3. 确认 Bucket 名称正确
4. 检查网络是否能访问 OSS

### 问题：权限错误

**解决方法：**
1. 确认 AccessKey 有 OSS 权限
2. 检查 Bucket 是否存在
3. 确认 Bucket 地域与 Endpoint 匹配

### 问题：文件上传成功但无法访问

**解决方法：**
1. 如果 Bucket 是私有的，需要配置 CDN 或签名 URL
2. 如果 Bucket 是公共读的，检查文件 URL 是否正确
3. 检查 OSS_PREFIX 配置

## 📚 相关文档

- 阿里云 OSS 文档：https://help.aliyun.com/product/31815.html
- Benome 上传指南：`UPLOAD_GUIDE.md`
- Benome 模板结构：`TEMPLATE_STRUCTURE.md`

---

**更新时间**: 2026-03-02 09:54  
**状态**: ⚠️ 等待填写真实 OSS 凭证
