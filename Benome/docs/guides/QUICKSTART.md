# Benome 房间媒体功能 - 快速开始

## 🎉 功能已就绪！

Benome 房间媒体功能已开发完成，现在可以为每个房间上传图片和视频了。

## ⚡ 3 分钟快速配置

### 步骤 1：配置阿里云 OSS（2 分钟）

```bash
# 进入项目目录
cd /root/Ben_cloud/Benome

# 创建配置文件
cat > .env << 'EOF'
# 阿里云 OSS 配置
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_ACCESS_KEY_ID=你的 AccessKey ID
ALIYUN_OSS_ACCESS_KEY_SECRET=你的 AccessKey Secret
ALIYUN_OSS_BUCKET=benome
EOF
```

> 💡 还没有 OSS 凭证？
> 1. 访问 https://oss.console.aliyun.com/
> 2. 创建 Bucket（名称：`benome`，权限：**公共读**）
> 3. 获取 AccessKey（用户信息管理 → AccessKey 管理）

### 步骤 2：重启服务（30 秒）

```bash
systemctl restart benome.service
```

### 步骤 3：验证配置（30 秒）

```bash
# 检查服务状态
systemctl is-active benome.service

# 应该返回：active
```

## 🚀 开始使用

### 管理员上传媒体

1. 访问管理后台：`http://your-domain:8200/admin/dashboard`
2. 通过 Benbot SSO 登录（需要 admin 角色）
3. 在"📸 房间媒体管理"卡片中选择房间
4. 拖拽文件上传或点击选择文件
5. 填写标题、描述，可勾选"设为封面"
6. 点击"上传媒体"

### 查看房间媒体

访问房间详情页：`http://your-domain:8200/properties/{房间 ID}`

- 查看所有图片和视频
- 点击媒体全屏查看（灯箱模式）
- 视频自动播放

## 📋 支持的文件格式

### 图片
- ✅ JPG / JPEG
- ✅ PNG
- ✅ GIF
- ✅ WebP

### 视频
- ✅ MP4
- ✅ MOV
- ✅ AVI

**文件大小限制**：最大 500MB

## 🔧 技术细节

- **存储位置**：阿里云 OSS（bucket: `benome`）
- **文件路径**：`benome/properties/{房间 ID}/{UUID}.{ext}`
- **访问方式**：公开读（CDN 加速可选）
- **数据库表**：`property_media`

## 📚 完整文档

| 文档 | 路径 | 说明 |
|------|------|------|
| OSS 配置指南 | `/root/Ben_cloud/Benome/OSS_CONFIG.md` | 详细配置步骤和故障排查 |
| 媒体功能使用 | `/root/Ben_cloud/Benome/MEDIA_FEATURE.md` | 完整功能说明和 API 文档 |
| 实现总结 | `/root/Ben_cloud/Benome/IMPLEMENTATION_SUMMARY.md` | 技术实现细节 |
| 项目 README | `/root/Ben_cloud/Benome/README.md` | 项目总体说明 |

## 🎯 API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/api/properties/{id}/media` | 所有人 | 获取媒体列表 |
| POST | `/api/properties/{id}/media/upload` | admin | 上传媒体 |
| DELETE | `/api/media/{id}` | admin | 删除媒体 |
| POST | `/api/properties/{id}/media/{id}/set-cover` | admin | 设为封面 |

完整 API 文档：`http://your-domain:8200/docs`

## ❓ 常见问题

### Q: 显示"media: download failed"
**A**: OSS 未配置。请按步骤 1 配置 `.env` 文件并重启服务。

### Q: 上传失败
**A**: 检查：
- OSS 凭证是否正确
- Bucket 是否存在且为"公共读"权限
- 文件大小是否超过 500MB

### Q: 图片无法显示
**A**: 检查：
- OSS Bucket 权限是否为"公共读"
- 浏览器控制台是否有 CORS 错误
- 文件是否成功上传到 OSS

### Q: 如何批量上传？
**A**: 当前版本支持单文件上传，批量上传功能开发中。

## 🎊 功能亮点

- ✅ 拖拽上传，简单易用
- ✅ 灯箱模式，全屏查看
- ✅ 封面设置，突出展示
- ✅ 视频支持，生动展示
- ✅ 响应式设计，移动端友好
- ✅ CDN 加速，快速加载（可选）

## 📞 技术支持

遇到问题？查看：
- 服务日志：`tail -f /root/Ben_cloud/Benome/logs/benome.log`
- API 文档：`http://your-domain:8200/docs`
- 故障排查：`/root/Ben_cloud/Benome/OSS_CONFIG.md`

---

**祝使用愉快！** 🏠📸
