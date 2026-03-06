# Benome 房间媒体功能使用指南

## 功能概述

Benome 民宿系统现已支持为每个房间上传**图片和视频**，让客人更直观地了解房间情况。

## 配置要求

### 阿里云 OSS 配置

在 `/root/Ben_cloud/Benome/.env` 文件中添加以下配置：

```bash
# 阿里云 OSS 配置（与其他 Ben_cloud 项目共用凭证，bucket 独立）
ALIYUN_OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
ALIYUN_OSS_ACCESS_KEY_ID=your_access_key_id
ALIYUN_OSS_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_OSS_BUCKET=benome
```

> **注意**：
> - OSS 凭证与其他 Ben_cloud 项目（Benlab、Benusy 等）相同
> - Bucket 名称固定为 `benome`（遵循项目命名规则）
> - 如果未配置 OSS，上传功能将不可用

## 管理员操作指南

### 1. 访问管理后台

1. 打开浏览器访问：`http://your-domain:8200`
2. 通过 Benbot SSO 登录（需要 admin 角色）
3. 进入管理后台：`/admin/dashboard`

### 2. 管理房间媒体

#### 方法一：从管理控制台进入

1. 在管理后台首页，找到"📸 房间媒体管理"卡片
2. 点击要管理的房间卡片
3. 进入媒体管理页面

#### 方法二：直接访问

访问 URL：`/admin/properties/{property_id}/media`

例如：`/admin/properties/1/media`

### 3. 上传媒体文件

1. **拖拽上传**：直接将文件拖到虚线框内
2. **点击上传**：点击虚线框选择文件
3. **填写信息**（可选）：
   - 标题：简短描述（如"客厅全景"）
   - 描述：详细说明（如"朝南落地窗，采光极佳"）
   - 设为封面：勾选后该图片将作为房间封面
4. **点击"上传媒体"**按钮

### 4. 管理已上传的媒体

- **设为封面**：点击"设为封面"按钮
- **删除**：点击"删除"按钮（不可恢复）
- **预览**：点击图片或视频可预览

## 客人视角

### 查看房间媒体

1. 访问房间详情页：`/properties/{property_id}`
2. 滚动到"房间展示"区域
3. 查看所有图片和视频

### 媒体画廊功能

- **网格展示**：所有媒体以网格形式展示
- **封面标识**：封面图片有"📸 封面"标识
- **类型标识**：右下角显示"🖼️ 图片"或"🎬 视频"
- **灯箱模式**：点击任何媒体可全屏查看
  - 图片：直接显示大图
  - 视频：自动播放，带控制条
- **键盘操作**：按 ESC 键关闭灯箱

## API 使用（开发者）

### 上传媒体

```bash
curl -X POST "http://localhost:8200/api/properties/1/media/upload" \
  -H "Cookie: session=your_session_cookie" \
  -F "file=@/path/to/image.jpg" \
  -F "title=客厅全景" \
  -F "description=朝南落地窗" \
  -F "is_cover=true"
```

### 获取媒体列表

```bash
curl "http://localhost:8200/api/properties/1/media"
```

响应示例：

```json
[
  {
    "id": 1,
    "property_id": 1,
    "media_type": "image",
    "oss_key": "benome/properties/1/abc123.jpg",
    "public_url": "https://benome.oss-cn-hangzhou.aliyuncs.com/benome/properties/1/abc123.jpg",
    "file_size": 1024000,
    "mime_type": "image/jpeg",
    "title": "客厅全景",
    "description": "朝南落地窗",
    "sort_order": 0,
    "is_cover": true,
    "is_active": true,
    "created_at": "2026-03-02T09:00:00",
    "updated_at": "2026-03-02T09:00:00"
  }
]
```

### 设为封面

```bash
curl -X POST "http://localhost:8200/api/properties/1/media/1/set-cover" \
  -H "Cookie: session=your_session_cookie"
```

### 删除媒体

```bash
curl -X DELETE "http://localhost:8200/api/media/1" \
  -H "Cookie: session=your_session_cookie"
```

## 技术细节

### 文件存储结构

OSS 中的文件路径格式：
```
benome/properties/{property_id}/{uuid}.{ext}
```

例如：
```
benome/properties/1/a1b2c3d4e5f6.jpg
benome/properties/1/b2c3d4e5f6a7.mp4
```

### 支持的文件类型

**图片**：
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)

**视频**：
- MP4 (.mp4)
- QuickTime (.mov)
- AVI (.avi)

### 文件大小限制

- 最大：500 MB
- 推荐图片：< 5 MB
- 推荐视频：< 100 MB

### 数据库表结构

```sql
CREATE TABLE property_media (
    id INTEGER PRIMARY KEY,
    property_id INTEGER NOT NULL,
    media_type VARCHAR(20) NOT NULL,  -- 'image' or 'video'
    oss_key VARCHAR(512) NOT NULL UNIQUE,
    public_url VARCHAR(1024),
    file_size INTEGER,
    mime_type VARCHAR(100),
    title VARCHAR(200),
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_cover BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);
```

## 故障排查

### 上传失败

1. 检查 OSS 配置是否正确
2. 确认文件大小不超过 500MB
3. 检查文件格式是否支持
4. 查看日志：`tail -f /root/Ben_cloud/Benome/logs/benome.log`

### 媒体无法显示

1. 检查 OSS bucket 权限是否为"公共读"
2. 确认 public_url 可以公开访问
3. 检查浏览器控制台是否有 CORS 错误

### 服务启动失败

1. 确认已安装 oss2 依赖：`pip show oss2`
2. 检查数据库迁移是否完成：`alembic current`
3. 查看服务状态：`systemctl status benome.service`

## 最佳实践

1. **图片优化**：
   - 使用 WebP 格式（更小体积，更好质量）
   - 分辨率建议：1920x1080 或更高
   - 压缩图片以减少加载时间

2. **视频优化**：
   - 使用 H.264 编码的 MP4 格式
   - 分辨率建议：1080p 或 720p
   - 时长控制在 30 秒以内

3. **内容组织**：
   - 每个房间上传 5-10 张图片
   - 包含所有重要区域（客厅、卧室、厨房、卫生间等）
   - 上传 1-2 个视频展示整体布局

4. **封面选择**：
   - 选择最能代表房间的图片
   - 确保光线充足、构图良好
   - 避免人物出现在封面中

## 更新日志

- **2026-03-02**: 初始版本发布
  - ✅ 支持图片和视频上传
  - ✅ 阿里云 OSS 存储
  - ✅ 媒体画廊展示
  - ✅ 灯箱模式预览
  - ✅ 封面设置功能
