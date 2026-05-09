# Lunah / Jinny AI Motion Archive

一个用于展示 AI 视频、互动网页、游戏和工具原型的静态作品集网站。

线上地址：

```text
https://19960705.github.io/feishu-website/
```

当前版本先使用仓库内静态资源发布：

- `api/videos.json`：作品数据
- `assets/videos/`：压缩后的视频样片
- `assets/covers/`：作品封面与截图
- `index.html`：响应式前端页面

页面可以直接托管在 GitHub Pages、Vercel 或任意静态网站服务上。

## 本地预览

```bash
cd /Users/mac/Downloads/feishu-website
python3 -m http.server 4178 --bind 127.0.0.1
```

打开：

```text
http://127.0.0.1:4178
```

## 飞书自动刷新

仓库保留了飞书多维表格自动刷新能力。`refresh.py` 会通过飞书 OpenAPI 读取多维表格附件字段，并生成 `api/videos.json`。

GitHub Actions 需要配置四个 Repository secrets：

- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_BASE_TOKEN`
- `LARK_TABLE_ID`

默认字段名：

| 字段名 | 用途 |
| --- | --- |
| 内容 | 作品标题 |
| 样片 | 视频附件 |
| 类型 | 分类筛选 |
| 时长 | 时长 |
| AI工具 | 工具或制作方式 |
| 序号 | 排序 |

如果飞书表格里暂时没有可下载的视频附件，`refresh.py` 会失败退出并保留现有 `api/videos.json`，避免自动任务把静态作品集清空。

## 当前状态

当前静态数据包含 23 个作品卡片，其中 14 个带视频样片，9 个为截图或网页作品预览。

首屏已加入招聘方预览播放器，打开页面后可直接播放精选视频样片。
