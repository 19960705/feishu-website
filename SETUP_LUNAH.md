# 飞书作品集网站配置清单

这个仓库不是 Codex skill，而是一个静态作品集网站模板：

- 飞书多维表格负责存视频与字段
- `refresh.py` 负责用飞书 OpenAPI 生成 `api/videos.json`
- GitHub Actions 每 12 小时自动刷新一次临时视频链接
- GitHub Pages 负责上线网站

## 1. 飞书多维表格字段

默认字段名必须和脚本一致：

| 字段名 | 推荐类型 | 用途 |
| --- | --- | --- |
| 内容 | 文本 | 网站卡片标题 |
| 样片 | 附件 | 上传视频文件 |
| 类型 | 多选或单选 | 分类筛选 |
| 时长 | 文本 | 例如 7秒、30秒、1分20秒 |
| AI工具 | 文本、多选或单选 | 展示生成工具 |
| 序号 | 数字 | 排序，越小越靠前 |

如果你已经建好了不同字段名，不用改表也可以：把 `.env.example` 复制成 `.env.local`，修改 `FIELD_TITLE`、`FIELD_VIDEO` 等映射。

## 2. 飞书机器人/自建应用还要做的事

你已经创建了飞书机器人，继续检查这些项：

- 在飞书开放平台拿到 `App ID` 和 `App Secret`
- 已完成：在权限管理里开通 `bitable:app`、`bitable:app:readonly`、`wiki:node:read`、`wiki:wiki:readonly`
- 已完成：发布版本 `1.0.0`，应用状态为 `Enabled`
- 已确认：OpenAPI 可以读取当前多维表格记录
- 待处理：OpenAPI 暂时没有写入/建字段权限，不能自动把本地视频回填进附件字段

## 3. 取两个表格参数

当前已确认参数：

- 飞书页面链接：`https://my.feishu.cn/wiki/KRJrwfmA0io4A1kqYnscyCHInWh?from=from_copylink`
- `LARK_BASE_TOKEN`：`G39rb6ExqabdtIs1026cC4uBnCb`
- `LARK_TABLE_ID`：`tblk0b7kJIupqsYP`
- 表名：`数据表`

注意：页面链接里的 wiki token 和 Bitable app token 不一样；脚本必须使用上面的 `LARK_BASE_TOKEN`。

## 4. 本地测试

```bash
cd /Users/mac/Downloads/feishu-website
cp .env.example .env.local
# 填好 .env.local 后运行：
python3 refresh.py
python3 -m http.server 4178 --bind 127.0.0.1
```

浏览器打开：

```text
http://127.0.0.1:4178
```

如果成功，`api/videos.json` 会变成你自己飞书表里的作品数据。

目前表格里还没有附件字段 `样片`，所以脚本会读取到 23 条记录但找不到可下载视频；这种情况下脚本会退出并保留现有 `api/videos.json`，避免 GitHub Actions 把静态作品集清空。

## 5. 当前临时发布方案

为了先发布可展示版本，已把本地作品转成静态资源放进仓库：

- 视频：`assets/videos/`
- 封面：`assets/covers/`
- 数据：`api/videos.json`

当前静态数据包含 23 个作品卡片，其中 14 个带视频样片，9 个是截图/网页作品预览。后续如果飞书表格补好附件字段，再切回 OpenAPI 自动刷新即可。

## 6. GitHub 上线

把这个项目推到你自己的 GitHub 仓库后：

- Settings -> Secrets and variables -> Actions
- 新增 `LARK_APP_ID`
- 新增 `LARK_APP_SECRET`
- 新增 `LARK_BASE_TOKEN`
- 新增 `LARK_TABLE_ID`
- Settings -> Pages -> Deploy from a branch -> `main` / root
- Actions -> Auto Refresh Feishu Videos -> Run workflow

## 7. 域名

原仓库自带的 `CNAME` 是作者域名，已经挪到 `CNAME.example`。

如果暂时不用自定义域名，不需要创建 `CNAME`。

如果要绑定自己的域名，新建 `CNAME` 文件，里面只写一行你的域名。
