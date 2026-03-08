# Benreel

Benreel 是一个独立的视频放映站，用老电视 / 胶卷的视觉隐喻来展示阿里云 OSS 上的视频素材。站点每天固定上线几卷视频，访客可以切换观看；管理员可以把胶卷拖进垃圾桶下线，也可以从垃圾桶捡回。

## 当前能力

- 读取 `VIDEO_LIBRARY_PATH` 指向的 JSON 清单，同步公开视频库。
- 每天按固定数量生成“今日节目”，并保持同一天内的排序稳定。
- 支持本地登录与 `Benbot` 的 `/auth/sso` 单点登录。
- 管理员可通过 `PATCH /api/videos/{id}` 下线或恢复视频。
- 提供复古放映室 HTML UI、`/api/dashboard`、`/api/videos` 与健康检查接口。

## 数据边界

- 视频源清单：`VIDEO_LIBRARY_PATH` 指向的本地 JSON 文件，内容填写 OSS 公开 URL。
- 本站运行数据：`/Users/ben/Desktop/myapp/Ben_cloud/Benreel/data/benreel.sqlite`
- 日志目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benreel/logs/`

## 视频清单格式

```json
{
  "videos": [
    {
      "id": "night-train",
      "title": "夜班列车",
      "url": "https://your-bucket.oss-cn-shanghai.aliyuncs.com/videos/night-train.mp4",
      "poster_url": "https://your-bucket.oss-cn-shanghai.aliyuncs.com/posters/night-train.jpg",
      "summary": "深夜车窗外掠过的城市灯带。",
      "duration_label": "02:14"
    }
  ]
}
```

## 启动

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benreel
make install
make db-upgrade
make dev
```

默认地址：`http://127.0.0.1:9500`

## 测试

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benreel
make test
```
