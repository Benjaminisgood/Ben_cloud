# Benome OSS 配置指南

## ⚠️ 重要提示

房间媒体功能需要配置阿里云 OSS 才能正常使用。如果未配置 OSS：
- ❌ 无法上传媒体文件
- ❌ 无法显示已上传的媒体
- ❌ 前端会显示"media: download failed"错误

## 📋 配置步骤

### 1. 获取阿里云 OSS 凭证

1. 登录 [阿里云控制台](https://oss.console.aliyun.com/)
2. 进入 OSS 管理控制台
3. 创建 Bucket（如果还没有）：
   - Bucket 名称：`benome`
   - 地域：选择离你服务器最近的（如华东 1-杭州）
   - 读写权限：**公共读**（重要！）
4. 获取 AccessKey：
   - 进入 用户信息管理 → AccessKey 管理
   - 创建 AccessKey（或复用现有的）
   - 记录 `AccessKey ID` 和 `AccessKey Secret`

### 2. 创建 .env 配置文件

在 `/root/Ben_cloud/Benome/` 目录下创建 `.env` 文件：

```bash
cd /root/Ben_cloud/Benome
cp .env.example .env
```

编辑 `.env` 文件，填入你的 OSS 配置：

```bash
# 阿里云 OSS 配置
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_ACCESS_KEY_ID=LTAI5tXXXXXXXXXXXXXXXX
ALIYUN_OSS_ACCESS_KEY_SECRET=XXXXXXXXXXXXXXXXXXXXXXXX
ALIYUN_OSS_BUCKET=benome
```

### 3. 重启服务

```bash
systemctl restart benome.service
```

### 4. 验证配置

```bash
# 检查服务状态
systemctl status benome.service

# 查看日志确认 OSS 配置加载成功
tail -f /root/Ben_cloud/Benome/logs/benome.log | grep -i oss
```

## 🔍 故障排查

### 问题：前端显示"media: download failed"

**原因**：OSS 未配置或配置错误

**解决方法**：
1. 检查 `.env` 文件是否存在
2. 确认 OSS 配置项已填写
3. 重启 Benome 服务
4. 检查 OSS Bucket 权限是否为"公共读"

### 问题：上传失败

**可能原因**：
- OSS 凭证错误
- Bucket 不存在
- 网络问题

**解决方法**：
```bash
# 测试 OSS 连接
python3 << 'EOF'
import oss2
from benome_api.core.config import get_settings

s = get_settings()
print(f"Endpoint: {s.ALIYUN_OSS_ENDPOINT}")
print(f"Bucket: {s.ALIYUN_OSS_BUCKET}")
print(f"AccessKey ID: {s.ALIYUN_OSS_ACCESS_KEY_ID[:10]}...")

try:
    auth = oss2.Auth(s.ALIYUN_OSS_ACCESS_KEY_ID, s.ALIYUN_OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, s.ALIYUN_OSS_ENDPOINT, s.ALIYUN_OSS_BUCKET)
    bucket.get_bucket_info()
    print("✅ OSS 连接成功！")
except Exception as e:
    print(f"❌ OSS 连接失败：{e}")
EOF
```

### 问题：图片无法显示

**检查清单**：
- [ ] OSS Bucket 权限是否为"公共读"
- [ ] 文件是否成功上传到 OSS
- [ ] public_url 是否可以公开访问
- [ ] 浏览器控制台是否有 CORS 错误

**测试 URL 访问**：
```bash
# 替换为你的实际 OSS URL
curl -I "https://benome.oss-cn-hangzhou.aliyuncs.com/test.jpg"
```

应该返回 `HTTP/1.1 200 OK`

## 📝 配置示例

### 开发环境

```bash
# /root/Ben_cloud/Benome/.env
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_ACCESS_KEY_ID=LTAI5tXXXXXXXXXXXXXXXX
ALIYUN_OSS_ACCESS_KEY_SECRET=XXXXXXXXXXXXXXXXXXXXXXXX
ALIYUN_OSS_BUCKET=benome
```

### 生产环境（推荐添加 CDN）

```bash
# /root/Ben_cloud/Benome/.env
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_ACCESS_KEY_ID=LTAI5tXXXXXXXXXXXXXXXX
ALIYUN_OSS_ACCESS_KEY_SECRET=XXXXXXXXXXXXXXXXXXXXXXXX
ALIYUN_OSS_BUCKET=benome

# 如果使用了 CDN，可以自定义 URL
# ALIYUN_OSS_CDN_URL=https://cdn.yourdomain.com
```

## 🔒 安全建议

1. **AccessKey 安全**
   - 不要将 AccessKey 提交到代码仓库
   - 定期轮换 AccessKey
   - 使用 RAM 子账号而非主账号

2. **Bucket 权限**
   - 媒体文件 Bucket 设为"公共读"
   - 不要开启"公共写"
   - 启用 OSS 日志记录

3. **文件上传限制**
   - 限制文件大小（已设置 500MB）
   - 限制文件类型（白名单验证）
   - 启用病毒扫描（可选）

## 📊 监控和计费

### OSS 费用组成
- 存储费用：按占用空间计算
- 流量费用：外网下载流量
- 请求费用：API 调用次数

### 监控指标
- 存储空间使用量
- 外网流出流量
- API 请求次数

### 优化建议
- 启用 CDN 加速（降低流量费用）
- 使用图片压缩（减少存储空间）
- 设置生命周期规则（自动清理旧文件）

## 🆘 获取帮助

- 阿里云 OSS 文档：https://help.aliyun.com/product/31815.html
- OSS SDK 文档：https://www.aliyun.com/product/oss
- Benome 媒体功能文档：`/root/Ben_cloud/Benome/MEDIA_FEATURE.md`

---

**配置完成后，记得重启服务：**
```bash
systemctl restart benome.service
```
