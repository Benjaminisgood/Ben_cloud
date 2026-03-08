# Benphoto

Benphoto 是一个个人照片桌面展示站。它把你放在阿里云 OSS 的照片当成拍立得相纸，每天随机挑出固定数量散落在桌面上，并允许管理员把不满意的照片扔进垃圾桶后再捡回来。

## 当前能力

- 支持录入完整 OSS 公网 URL，或在配置了 `ALIYUN_OSS_PUBLIC_BASE_URL` 后录入对象 key。
- 每天固定随机展示 `DAILY_PHOTO_COUNT` 张照片，保持当天展示集合稳定。
- 支持本地登录与 `Benbot` 的 `/auth/sso` 单点登录。
- 支持新增照片、扔进垃圾桶、从垃圾桶恢复。
- 暴露 HTML UI、`/api/dashboard`、`/api/photos` 和健康检查接口。

## 数据边界

- 本站运行数据：`/Users/ben/Desktop/myapp/Ben_cloud/Benphoto/data/benphoto.sqlite`
- 日志目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benphoto/logs/`
- 图片文件本身不落地到本项目，只保存 OSS 引用。

## 页面结构

- 首页：卡通木桌场景、随机堆叠拍立得、垃圾桶回收区、加图表单
- 登录页：本地账号密码登录
- SSO 入口：`/auth/sso`

## 启动

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benphoto
./benphoto.sh init-env
./benphoto.sh install
./benphoto.sh start
```

默认地址：`http://127.0.0.1:9300`

## 测试

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benphoto
make test
```
