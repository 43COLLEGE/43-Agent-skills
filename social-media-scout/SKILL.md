---
name: social-media-scout
description: 跨平台社交媒体数据查询。支持抖音、TikTok、小红书、微博、B站、快手、Instagram、YouTube、Twitter、微信公众号等平台。当需要查询社交媒体账号信息、搜索内容、获取视频/帖子数据、查看评论、解析分享链接、下载视频、获取微信公众号文章列表或提取文章内容时使用此技能。
---

# Social Media Scout — 跨平台社交媒体数据查询

> 作者：43 COLLEGE 凯寓 (KAIYU) 出品
> 版本：v1.0

通过 TikHub API 获取 926+ 个社交媒体接口的数据。

## 首次配置

如果命令报错找不到 config.json、api_key 为占位符、或返回 401，读取本目录下的 `SETUP.md` 并按其中的流程引导用户完成配置。

## 跨平台兼容

| | macOS / Linux | Windows |
|---|---|---|
| Python 命令 | `python3` | `python` |
| Skill 路径 | `~/.claude/skills/social-media-scout/` | `%USERPROFILE%\.claude\skills\social-media-scout\` |
| JSON 参数 | `--args '{"key": "value"}'` | `--args "{\"key\": \"value\"}"` |

## 调用架构（重要，先读这段）

本 skill 有两条调用路径，理解这个是避免踩坑的前提：

| 模式 | 地址 | 依赖 | 适用场景 |
|------|------|------|----------|
| MCP 模式 | `https://mcp.tikhub.io/tools/call` | 需要 `tikhub-mcp-proxy.exe` 在后台运行 | 代理已启动时 |
| REST 直调 | `https://api.tikhub.io/api/v1/...` | 无额外依赖，直接 HTTP 调用 | 代理未运行时（常见） |

`call_tool()` 已实现自动降级：先尝试 MCP，404/连接失败时自动切换 REST。也可用 `rest_call()` 或 CLI `rest-call` 命令直接走 REST。

**工具名 → REST 路径映射规则**：
```
{platform}_{module}_{method} → /api/v1/{platform}/{module}/{method}
```
示例：
- `douyin_search_fetch_user_search` → `/api/v1/douyin/search/fetch_user_search`
- `douyin_web_handler_user_profile` → `/api/v1/douyin/web/handler_user_profile`

**HTTP 方法规则**：搜索类（工具名含 `_search_`）用 POST + JSON body，其余用 GET + query params。如果猜错会自动 405 重试。

## 资源位置

- 脚本目录: `scripts/`（skill 根目录下，相对路径）
- API 配置: `scripts/config.json`（含 API Key、MCP 代理路径）
- MCP 代理（Windows）: 按 `config.json` 中 `mcp_proxy_exe` 路径配置
- MCP 代理（Mac）: 不适用，使用 REST 直调模式即可
- TikHub 文档: https://docs.tikhub.io
- API Key 管理: https://user.tikhub.io

## 使用场景

- 查询用户资料（抖音/TikTok/小红书等）
- 搜索关键词相关的视频、笔记、帖子
- 通过分享链接解析视频数据
- 获取视频评论、用户粉丝/关注列表
- 查看平台热搜榜单
- 下载无水印视频
- 获取微信公众号文章列表（需 ghid）
- 提取微信公众号指定文章内容

## 调用方式

**所有命令必须先 cd 到 skill 根目录再执行。** Python 命令参考跨平台兼容表。

```bash
# macOS/Linux 示例（Windows 将 python3 替换为 python，单引号替换为转义双引号）

# 调用工具（MCP 优先，自动降级 REST）
python3 scripts/tikhub_client.py call <tool_name> --args '{"param": "value"}'

# 直接走 REST API（推荐，跳过 MCP 代理）
python3 scripts/tikhub_client.py rest-call <tool_name> --args '{"param": "value"}'

# 按平台列出工具
python3 scripts/tikhub_client.py list --platform douyin

# 按关键词搜索工具
python3 scripts/tikhub_client.py list --keyword search
```

Python 内联调用（推荐用于复杂任务）:
```python
import os, sys
# 必须用绝对路径，确保从任何 cwd 都能加载
skill_dir = os.path.expanduser("~/.claude/skills/social-media-scout")
sys.path.insert(0, os.path.join(skill_dir, "scripts"))
from tikhub_client import call_tool, rest_call, parse_user_search_results, extract_video_url, download_file
```

## 常用工具速查

### 抖音 (douyin)

搜索类（推荐 `douyin_search_*`，比 `douyin_web_fetch_*_search_*` 更稳定）:

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 综合搜索 | `douyin_search_fetch_general_search_v1` | `keyword`, `cursor`(0), `sort_type`("0") |
| 搜索用户 | `douyin_search_fetch_user_search` | `keyword`, `offset`("0"), `count`("10") |
| 搜索视频 | `douyin_search_fetch_video_search_v1` | `keyword`, `cursor`(0) |

用户资料:

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 用户资料(sec_uid) | `douyin_web_handler_user_profile` | `sec_user_id` |
| 用户资料(uid) | `douyin_web_fetch_user_profile_by_uid` | `uid` |
| 用户资料(抖音号) | `douyin_web_fetch_user_profile_by_short_id` | `short_id` |

作品获取（获取全部作品用 App 接口，Web 接口有分页深度限制约 80 条）:

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 用户作品(App,推荐) | `douyin_app_fetch_user_post_videos` | `sec_user_id`, `max_cursor`("0"), `count`("20") |
| 用户作品(Web) | `douyin_web_fetch_user_post_videos` | `sec_user_id`, `max_cursor`("0"), `count`("50") |
| 单个视频 | `douyin_web_fetch_one_video` | `aweme_id` |
| 分享链接解析 | `douyin_web_fetch_one_video_by_share_url` | `share_url` |
| 高清视频链接 | `douyin_app_fetch_video_high_quality_play_url` | `aweme_id` |

互动数据:

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 视频评论 | `douyin_web_fetch_video_comments` | `aweme_id`, `cursor`("0"), `count`("20") |
| 粉丝列表 | `douyin_web_fetch_user_fans_list` | `sec_user_id`, `max_time`("0"), `count`("20") |
| 关注列表 | `douyin_web_fetch_user_following_list` | `sec_user_id`, `max_time`("0"), `count`("20") |
| 热搜榜 | `douyin_web_fetch_hot_search_result` | 无 |

### 小红书 (xiaohongshu)

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 用户信息 | `xiaohongshu_web_get_user_info` | `user_id` |
| 搜索笔记 | `xiaohongshu_web_search_notes` | `keyword`, `page`(1), `sort`("general") |
| 搜索用户 | `xiaohongshu_web_search_users` | `keyword`, `page`(1) |
| 用户笔记列表(App,推荐) | `xiaohongshu_app_get_user_notes` | `user_id`, `cursor` |
| 用户笔记列表(Web) | `xiaohongshu_web_get_user_notes_v2` | `user_id`, `cursor` |
| 笔记评论 | `xiaohongshu_web_get_note_comments` | `note_id`, `cursor` |

### B站 (bilibili)

**重要：B站接口稳定性差，web 和 app 的用户资料/作品列表接口经常 500。以下是经过实测验证的可靠路径。**

搜索类:

| 场景 | 工具名 | 关键参数 | 备注 |
|------|--------|----------|------|
| 搜索用户 | `bilibili_app_fetch_search_by_type` | `keyword`, `search_type`("bili_user"), `page`("1") | **推荐**，稳定 |
| 搜索视频 | `bilibili_app_fetch_search_by_type` | `keyword`, `search_type`("video"), `page`("1") | 结果混合多个UP主，需按 author 过滤 |
| 综合搜索 | `bilibili_app_fetch_search_all` | `keyword`, `page`("1") | 混合类型 |
| 综合搜索(Web) | `bilibili_web_fetch_general_search` | `keyword`, `search_type`, `page`("1") | 不稳定，常 500 |

用户资料（**获取粉丝数的可靠方法**）:

| 场景 | 工具名 | 关键参数 | 备注 |
|------|--------|----------|------|
| 粉丝/关注数 | `bilibili_web_fetch_user_relation_stat` | `vmid` | **最稳定**，但 TikHub 也可能 500 |
| 用户资料(Web) | `bilibili_web_fetch_user_profile` | `vmid` | 需 wbi 签名，常 500 |
| 用户资料(App) | `bilibili_app_fetch_user_info` | `vmid` | 不稳定 |
| UP主播放/点赞总量 | `bilibili_web_fetch_user_up_stat` | `vmid` | 可能返回空 data |

**如果 TikHub 接口全部 500，可用 Python 直接调 B站公开 API 作为备选**（仅使用内置库，无需安装额外依赖）:
```python
import urllib.request, json
mid = '目标UID'
headers = {'User-Agent': 'Mozilla/5.0 (compatible)', 'Referer': 'https://space.bilibili.com/'}
req = urllib.request.Request(f'https://api.bilibili.com/x/relation/stat?vmid={mid}', headers=headers)
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read())
# data['data']['follower'] = 粉丝数, data['data']['following'] = 关注数
# 此接口无需 wbi 签名，较稳定
```

作品获取（**核心踩坑点**）:

| 场景 | 工具名 | 关键参数 | 备注 |
|------|--------|----------|------|
| ⭐ 用户动态(含视频) | `bilibili_web_fetch_user_dynamic` | `uid`, `offset`("") | **最可靠的获取用户视频列表方式** |
| 用户作品(Web) | `bilibili_web_fetch_user_post_videos` | `mid`, `pn`("1"), `ps`("10") | 经常 500 |
| 用户作品(App) | `bilibili_app_fetch_user_videos` | `vmid`, `pn`("1"), `ps`("10") | 经常 500 |
| 单个视频 | `bilibili_web_fetch_one_video` | `bvid` 或 `aid` | - |

互动数据:

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 视频评论 | `bilibili_web_fetch_video_comments` | `oid`(视频aid), `type`("1"), `pn`("1") |
| 视频评论(App) | `bilibili_app_fetch_video_comments` | `oid`, `type`("1"), `pn`("1") |
| 视频弹幕 | `bilibili_web_fetch_video_danmaku` | `oid`(视频cid) |
| 收藏夹 | `bilibili_web_fetch_collect_folders` | `up_mid` |
| BV转AID | `bilibili_web_bv_to_aid` | `bvid` |
| 热门视频 | `bilibili_web_fetch_com_popular` | `pn`("1"), `ps`("20") |
| 热搜 | `bilibili_web_fetch_hot_search` | 无 |

#### B站推荐工作流

**下载B站视频**（TikHub 不适用，必须用 yt-dlp）:

先检测 yt-dlp 是否已安装：`which yt-dlp`（macOS/Linux）或 `where yt-dlp`（Windows）。

如果未安装，引导用户安装：
```bash
# macOS（需要 Homebrew）
brew install yt-dlp

# Windows（需要 pip）
pip install yt-dlp

# Linux
pip3 install yt-dlp
```

下载命令：
```bash
yt-dlp \
  --output "/目标目录/文件名.%(ext)s" \
  --format "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" \
  --no-playlist \
  "https://www.bilibili.com/video/BVxxx"
```

> 1080P 60帧需要大会员 cookie（`--cookies-from-browser chrome`），普通 1080P 无需登录。

**查询UP主信息的标准流程**（避免踩坑）:

1. **搜索用户** → `bilibili_app_fetch_search_by_type`（search_type="bili_user"）
   - 返回结果中：`item[0].param` = UID，`item[0].author_new.fans` = 粉丝数（可能不精确）
2. **获取精确粉丝数** → `bilibili_web_fetch_user_relation_stat`（vmid=UID）
   - 如果 500，备选直接 requests 调 `api.bilibili.com/x/relation/stat`
3. **获取最新视频** → `bilibili_web_fetch_user_dynamic`（uid=UID, offset=""）
   - **不要用** `bilibili_web_fetch_user_post_videos` 或 `bilibili_app_fetch_user_videos`，它们经常 500
   - 动态接口每页约 12 条，用返回的 `data.offset` 翻页
   - 视频数据在 `item.modules.module_dynamic.major.archive` 中
4. **解析动态中的视频数据**:
```python
items = resp['result']['data']['data']['items']
for item in items:
    archive = item['modules']['module_dynamic']['major'].get('archive', {})
    if archive:  # 跳过纯文字/转发动态
        title = archive['title']
        bvid = archive['bvid']
        stat = archive['stat']  # play, danmaku
        duration = archive['duration_text']
        pub_time = item['modules']['module_author']['pub_time']
```

### TikTok

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 用户资料 | `tiktok_web_fetch_user_profile` | `uniqueId` |
| 用户作品 | `tiktok_web_fetch_user_post` | `secUid`, `cursor`("0"), `count`("20") |
| 单个视频 | `tiktok_web_fetch_post_detail` | `aweme_id` |
| 搜索视频 | `tiktok_web_fetch_search_video` | `keyword`, `cursor`("0"), `count`("20") |
| 视频评论 | `tiktok_web_fetch_post_comment` | `aweme_id`, `cursor`("0"), `count`("20") |

### 通用

| 场景 | 工具名 | 关键参数 |
|------|--------|----------|
| 混合解析(任意链接) | `hybrid_video_data` | `url` |

### 微信公众号 (wechat_mp)

**重要：TikHub 的微信公众号接口必须直接调用 REST API，不能走 MCP 工具系统（/tools 端点返回 404）。**

**调用方式（固定模板）**：
```python
import urllib.request, json, urllib.parse, os

# 从 config.json 读取 API Key
skill_dir = os.path.expanduser("~/.claude/skills/social-media-scout")
with open(os.path.join(skill_dir, "scripts", "config.json")) as f:
    api_key = json.load(f)["api_key"]

headers = {'Authorization': f'Bearer {api_key}', 'User-Agent': 'TikHub/1.0'}

def wechat_mp_get(path, params):
    url = f'https://api.tikhub.io{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())
```

**接口列表**：

| 场景 | 路径 | 关键参数 |
|------|------|----------|
| 获取公众号文章列表 | `/api/v1/wechat_mp/web/fetch_mp_article_list` | `ghid`（必填）, `offset`（翻页） |
| 提取文章内容(JSON，便宜) | `/api/v1/wechat_mp/web/fetch_mp_article_detail_json` | `url`（**仅支持短链** mp.weixin.qq.com/s/XXXX） |
| 提取文章内容(HTML，贵) | `/api/v1/wechat_mp/web/fetch_mp_article_detail_html` | `url`（短链/长链均支持，文章列表 ContentUrl 必须用此接口） |
| 获取文章评论 | `/api/v1/wechat_mp/web/fetch_mp_article_comment_list` | `url`, `comment_id`, `buffer` |
| 搜狗URL转微信URL | `/api/v1/wechat_mp/web/fetch_mp_article_url` | `sogou_url` |
| 获取相关文章 | `/api/v1/wechat_mp/web/fetch_mp_related_articles` | `url` |

**文章列表返回结构**：
```python
data = resp['data']
articles = data['list']   # 文章数组
next_offset = data['offset']  # 翻页游标，传给下次请求的 offset 参数

for a in articles:
    title = a['Title']
    url = a['ContentUrl']       # 文章长链，传给 fetch_mp_article_detail_html（JSON 接口不支持长链）
    send_time = a['send_time']  # Unix 时间戳
    cover = a['CoverImgUrl']
```

**文章详情返回结构**：
```python
data = resp['data']
title = data['title']
author = data['author']
ghid = data['publish_info']['user_id']   # 这就是公众号 ghid！
pub_time = data['publish_info'].get('type', '')
content_blocks = data['content']['raw_content']  # 结构化内容块列表
# 每个 block 有 type(p/h5/image/section) 和 text 字段
```

#### 微信公众号标准工作流

**已知文章 URL → 完整流程**（推荐入口）:

1. **提取 ghid**：调用 `fetch_mp_article_detail_json`，从 `data.publish_info.user_id` 拿到 ghid
2. **获取文章列表**：调用 `fetch_mp_article_list`（ghid=上一步结果）
3. **提取指定文章**：对目标文章 URL 调用 `fetch_mp_article_detail_json`

**只有公众号名称 → 获取 ghid 的变通路径**（有风险，搜狗可能反爬）:

1. 在微信 app 里打开该公众号任意一篇文章，复制链接
2. 将链接传给 Claude，执行步骤 1

**注意**：TikHub 无"按公众号名称搜索"的接口，必须从一篇该公众号的文章 URL 中提取 ghid。

## 工作流程

1. 识别目标平台
2. 根据需求选择工具（搜索/资料/作品/评论/下载）
3. 分享链接优先用 `*_by_share_url` 或 `hybrid_video_data`
4. 不确定参数名时用 `list --keyword` 查找
5. 调用工具并格式化输出

## 踩坑记录（重要）

以下为正文未覆盖的补充经验，已去除与前文重复的内容。

### 通用

1. **参数类型**: 大部分参数需要传字符串（如 `"0"` 而非 `0`）
2. **API 计费**: 每次成功调用都会计费，避免不必要的重复请求。响应中有 `cache_url` 可免费重复访问（24h 有效）
3. **分页去重通用策略**: 所有平台批量抓取时，用 dict/set 按 ID 去重，并设置"连续 N 页无新数据则停止"的安全机制
4. **Windows 内联 Python 编码**: 处理中文/emoji 时，在脚本开头加 `import sys; sys.stdout.reconfigure(encoding='utf-8')`，或用 `python -X utf8` 启动。`tikhub_client.py` 已内置此处理

### 抖音

5. **用户搜索数据结构特殊**: `douyin_search_fetch_user_search` 返回的用户信息嵌套在 `dynamic_patch.raw_data`（JSON 字符串）中，必须用 `parse_user_search_results()` 解析
6. **视频下载链接字段不统一**: 不同接口返回字段名不同（video_url/play_url/play_addr 等），用 `extract_video_url()` 统一处理

### 小红书

7. **Web 接口分页重复严重**: `xiaohongshu_web_get_user_notes_v2` 分页有约 60% 重复率。获取全部笔记必须用 `xiaohongshu_app_get_user_notes`（App 接口），cursor 取每页最后一条笔记的 `cursor` 字段

### B站

8. **搜索结果混合多个UP主**: `bilibili_app_fetch_search_by_type` 搜索视频时，结果包含多个UP主，必须按 `item.av.author` 和 `item.av.mid` 过滤目标UP主
9. **UID 有两种格式**: `item.param` 是新版长 UID（如 3546620310326128），`item.author_new.mid` 是旧版短 mid（如 1680175）。调用其他接口时统一用长 UID（param 字段）
10. **动态数据解析路径**: `result.data.data.items[]`，视频在 `modules.module_dynamic.major.archive`（含 title/bvid/stat/duration_text），作者在 `modules.module_author`。纯文字/转发动态没有 archive 字段，需跳过

### 微信公众号

11. **接口必须走 REST API**: 微信公众号接口无法通过 MCP `/tools` 端点调用（返回 404），必须直接 HTTP 请求
12. **无法按名称搜索**: 必须传 `ghid`（格式 `gh_xxxxxxxx`），从文章详情的 `data.publish_info.user_id` 获取
13. **搜狗微信反爬严重**: 通过搜狗自动化获取 ghid 不可靠，最可靠方式是用户手动提供一篇文章链接
14. **文章 URL 格式影响接口选择**: `fetch_mp_article_detail_json` 只接受短链（`mp.weixin.qq.com/s/XXXXX`），长链必须用 `fetch_mp_article_detail_html`。`wechat_mp_get_article_detail()` 已自动处理

## 辅助函数说明

`tikhub_client.py` 提供以下辅助函数:

- `call_tool(name, args)` - 调用任意 TikHub 工具（MCP 优先，自动降级 REST）
- `rest_call(name, args)` - 直接走 REST API 调用（跳过 MCP 代理）
- `list_tools(keyword, platform)` - 搜索可用工具
- `parse_user_search_results(response)` - 解析抖音用户搜索的嵌套数据
- `extract_video_url(post_data, api_response)` - 从多种数据结构中提取视频链接
- `download_file(url, filepath)` - 下载文件到本地
- `extract_result_data(response)` - 从 API 响应中提取 data 字段
