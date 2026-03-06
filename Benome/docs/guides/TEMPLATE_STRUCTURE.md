# Benome 模板结构说明

## 📁 模板文件组织

Benome 项目采用**管理员与普通用户界面分离**的设计原则，确保不同角色的用户体验清晰独立。

## 🗂️ 模板文件列表

### 管理员界面（Admin Templates）

| 模板文件 | 路径 | 用途 | 访问权限 |
|---------|------|------|---------|
| `admin_dashboard.html` | `/apps/web/templates/` | 管理员控制台 | admin 角色 |
| `admin_media_manage.html` | `/apps/web/templates/` | 媒体管理页面 | admin 角色 |

### 普通用户界面（User Templates）

| 模板文件 | 路径 | 用途 | 访问权限 |
|---------|------|------|---------|
| `index.html` | `/apps/web/templates/` | 首页 | 所有人 |
| `dashboard.html` | `/apps/web/templates/` | 用户仪表盘 | customer 角色 |
| `property_detail.html` | `/apps/web/templates/` | 房间详情页 | 所有人 |

## 🔄 路由映射

### 管理员路由

```python
GET /admin/dashboard          → admin_dashboard.html
GET /admin/properties/{id}/media → admin_media_manage.html
```

### 用户路由

```python
GET /                         → index.html
GET /dashboard                → dashboard.html
GET /properties/{id}          → property_detail.html
```

## 🎯 功能对比

### admin_media_manage.html（管理员）

**功能：**
- ✅ 上传新媒体（拖拽/点击）
- ✅ 查看媒体列表
- ✅ 编辑媒体信息（标题、描述、封面）
- ✅ 删除媒体
- ✅ 设置封面
- ✅ 查看房间页面（跳转）

**特点：**
- 完整的 CRUD 操作
- 表单提交功能
- JavaScript 交互
- Flash 消息提示
- 模态框编辑

### property_detail.html（用户）

**功能：**
- ✅ 查看房间信息
- ✅ 浏览媒体画廊
- ✅ 灯箱模式全屏查看
- ✅ 视频播放
- ✅ 响应式布局

**特点：**
- 只读展示
- 美观的画廊布局
- 流畅的交互体验
- 无编辑功能

## 🔒 权限控制

### 管理员页面保护

所有管理员页面都通过 `get_session_user()` 进行权限验证：

```python
@router.get("/admin/properties/{property_id}/media")
def admin_media_manage_page(property_id: int, request: Request, db=Depends(get_db)):
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    # ... 渲染管理员页面
```

### 用户页面访问

用户页面对所有人开放（部分功能可能需要登录）：

```python
@router.get("/properties/{property_id}")
def property_detail_page(property_id: int, request: Request, db=Depends(get_db)):
    user = get_session_user(request, db)  # 可选，用于显示用户信息
    
    # ... 渲染用户页面
```

## 🎨 设计差异

### 管理员界面设计

- **风格**：功能导向，注重操作效率
- **布局**：表单 + 列表 + 操作按钮
- **交互**：丰富的 JavaScript 功能
- **颜色**：主色调 + 功能色（成功/危险/警告）

### 用户界面设计

- **风格**：视觉导向，注重展示效果
- **布局**：大图展示 + 网格画廊
- **交互**：灯箱效果 + 平滑过渡
- **颜色**：温馨舒适的配色

## 📊 数据流

### 管理员上传流程

```
1. 管理员访问 /admin/properties/{id}/media
2. 选择文件并填写信息
3. POST /api/properties/{id}/media/upload
4. 后端处理：
   - 验证文件
   - 上传到 OSS
   - 创建数据库记录
5. 返回成功响应
6. 前端刷新媒体列表
```

### 用户浏览流程

```
1. 用户访问 /properties/{id}
2. GET /api/properties/{id}/media
3. 后端返回媒体列表（只读数据）
4. 前端渲染画廊
5. 用户点击全屏查看（灯箱模式）
```

## 🛠️ 开发指南

### 添加新的管理员页面

1. 创建模板文件：`admin_xxx.html`
2. 添加路由：`/admin/xxx`
3. 添加权限检查：`get_session_user()`
4. 确保角色验证：`user.role == "admin"`

### 添加新的用户页面

1. 创建模板文件：`xxx.html`
2. 添加路由：`/xxx`
3. 可选登录检查：`get_session_user()`
4. 渲染页面展示数据

## 📝 最佳实践

### 管理员界面

- ✅ 提供清晰的操作反馈
- ✅ 使用确认对话框防止误操作
- ✅ 支持批量操作（如需要）
- ✅ 提供返回导航
- ✅ 显示操作历史记录

### 用户界面

- ✅ 注重视觉效果
- ✅ 优化加载速度
- ✅ 支持移动端
- ✅ 提供分享功能
- ✅ 添加收藏/预订功能

## 🔍 故障排查

### 问题：管理员看不到上传按钮

**检查：**
1. 是否使用 admin 账号登录
2. 访问的 URL 是否正确（应该是 `/admin/...`）
3. 浏览器缓存是否需要清除

### 问题：用户能看到编辑功能

**检查：**
1. 确认访问的是 `/properties/{id}` 而不是 `/admin/...`
2. 检查权限验证逻辑
3. 确认模板文件没有混淆

## 📚 相关文件

- 管理员模板：`/root/Ben_cloud/Benome/apps/web/templates/admin_media_manage.html`
- 用户模板：`/root/Ben_cloud/Benome/apps/web/templates/property_detail.html`
- 路由定义：`/root/Ben_cloud/Benome/apps/api/src/benome_api/web/routes/pages.py`
- 权限验证：`/root/Ben_cloud/Benome/apps/api/src/benome_api/web/deps.py`

---

**更新时间**: 2026-03-02 09:45  
**版本**: v2.0 (管理员/用户界面分离)
