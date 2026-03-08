# Benvinyl

Benvinyl 是一个黑胶唱片机风格的音频展示站。它每天会从你登记的阿里云 OSS 音频引用里固定随机选出一批节目，对外展示在桌面唱片堆里；管理员可以把唱片拖进垃圾桶下架，也可以从垃圾桶捡回。

## 当前能力

- 每天固定随机上线若干音频节目。
- 公开展示当天节目，点击唱片即可切换唱盘中的当前播放内容。
- 管理员录入新的 OSS 音频引用。
- 管理员下架或恢复唱片，不删除原始引用。
- 支持本地登录与 `Benbot` 的 `/auth/sso` 单点登录。

## 数据边界

- 只保存音频元信息与 OSS 引用：`/Users/ben/Desktop/myapp/Ben_cloud/Benvinyl/data/benvinyl.sqlite`
- 不在本项目落地原始音频文件。
- 日志目录：`/Users/ben/Desktop/myapp/Ben_cloud/Benvinyl/logs/`

## 启动

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benvinyl
./benvinyl.sh init-env
./benvinyl.sh install
./benvinyl.sh start
```

默认地址：`http://127.0.0.1:9400`

## 测试

```bash
cd /Users/ben/Desktop/myapp/Ben_cloud/Benvinyl
make test
```
