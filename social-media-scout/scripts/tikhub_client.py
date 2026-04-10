#!/usr/bin/env python3
"""TikHub MCP API 客户端 - 社交媒体数据通用接口

已知问题与解决方案（实战总结）:
- Windows 控制台 GBK 编码: 已自动处理
- Cloudflare 拦截: 已添加 User-Agent
- 抖音 Web 接口分页深度有限: 获取全部作品请用 App 接口
- 用户搜索数据嵌套在 dynamic_patch.raw_data: 已提供解析函数
- 微信公众号接口: 必须走 REST API 直调，不能用 MCP /tools/call
"""

import json
import sys
import os
import argparse
import urllib.request
import urllib.error
import urllib.parse
import re
import time

# Windows 控制台编码修复
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
GHID_CACHE_PATH = os.path.join(SCRIPT_DIR, "wechat_mp_ghid_cache.json")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def api_request(method, path, data=None):
    """发送 HTTP 请求到 TikHub MCP API"""
    config = load_config()
    url = f"{config['base_url']}{path}"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "User-Agent": "TikHub-Claude-Skill/1.0",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {err_body[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def _tool_name_to_rest_path(tool_name):
    """将 MCP 工具名转换为 REST API 路径

    规则: {platform}_{module}_{method...}
    → /api/v1/{platform}/{module}/{method_joined_by_underscore}

    示例:
    - douyin_search_fetch_user_search → /api/v1/douyin/search/fetch_user_search
    - douyin_web_handler_user_profile → /api/v1/douyin/web/handler_user_profile
    - bilibili_app_fetch_search_by_type → /api/v1/bilibili/app/fetch_search_by_type
    """
    parts = tool_name.split("_", 2)
    if len(parts) < 3:
        return None
    platform, module, method = parts
    return f"/api/v1/{platform}/{module}/{method}"


def _guess_http_method(tool_name):
    """根据工具名推断 HTTP 方法

    搜索类接口用 POST（带 JSON body），其余用 GET（query params）
    """
    if "_search_" in tool_name or tool_name.endswith("_search"):
        return "POST"
    return "GET"


def rest_call(tool_name, arguments=None):
    """直接调用 TikHub REST API（绕过 MCP 代理）

    当 MCP 代理未运行时使用此函数。自动处理:
    - 工具名 → REST 路径映射
    - HTTP 方法推断（搜索=POST，其余=GET）
    - 405 时自动切换 HTTP 方法重试
    """
    path = _tool_name_to_rest_path(tool_name)
    if not path:
        return {"error": f"无法将工具名转换为 REST 路径: {tool_name}"}

    config = load_config()
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "User-Agent": "TikHub-Claude-Skill/1.0",
        "Accept": "application/json",
    }
    args = arguments or {}

    def _do_request(method):
        if method == "POST":
            url = f"https://api.tikhub.io{path}"
            body = json.dumps(args).encode("utf-8")
            return urllib.request.Request(url, data=body, headers=headers, method="POST")
        else:
            qs = urllib.parse.urlencode(args)
            url = f"https://api.tikhub.io{path}?{qs}" if qs else f"https://api.tikhub.io{path}"
            return urllib.request.Request(url, headers=headers, method="GET")

    method = _guess_http_method(tool_name)
    req = _do_request(method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 405:
            # HTTP 方法猜错了，换另一个重试
            alt = "GET" if method == "POST" else "POST"
            req2 = _do_request(alt)
            try:
                with urllib.request.urlopen(req2, timeout=120) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e2:
                err_body = e2.read().decode("utf-8", errors="replace")
                return {"error": f"HTTP {e2.code}: {err_body[:500]}"}
        err_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {err_body[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def call_tool(tool_name, arguments=None):
    """调用指定工具（MCP 优先，自动降级到 REST 直调）

    执行顺序:
    1. 尝试通过 MCP 代理调用（需要 tikhub-mcp-proxy.exe 运行）
    2. 如果 MCP 返回 404/连接失败，自动降级到 REST API 直调
    """
    data = {"tool_name": tool_name, "arguments": arguments or {}}
    result = api_request("POST", "/tools/call", data)

    # MCP 代理不可用时自动降级到 REST
    err = str(result.get("error", ""))
    if err and ("404" in err or "Connection" in err or "URLError" in err
                or "urlopen" in err or "Errno" in err):
        return rest_call(tool_name, arguments)

    return result


def list_tools(keyword=None, platform=None):
    """列出可用工具，支持按关键词或平台过滤"""
    result = api_request("GET", "/tools")
    if "error" in result:
        return result
    tools = result if isinstance(result, list) else result.get("tools", result.get("data", []))
    if platform:
        tools = [t for t in tools if t["name"].startswith(platform)]
    if keyword:
        kw = keyword.lower()
        tools = [t for t in tools if kw in t["name"].lower() or kw in t.get("description", "").lower()]
    return [{"name": t["name"], "description": t.get("description", "")} for t in tools]


# ========== 通用数据提取辅助函数 ==========

def extract_result_data(response):
    """从 API 响应中提取 data 字段（跳过元数据层）"""
    result = response.get("result", response)
    return result.get("data", result)


def parse_user_search_results(response):
    """解析抖音用户搜索结果

    抖音搜索接口的用户数据嵌套在 dynamic_patch.raw_data 中，
    需要二次 JSON 解析。此函数统一处理这个问题。
    """
    data = extract_result_data(response)
    user_list = data.get("user_list", [])
    parsed = []
    for u in user_list:
        # 尝试从 dynamic_patch.raw_data 解析
        raw = u.get("dynamic_patch", {}).get("raw_data", "{}")
        try:
            info = json.loads(raw).get("user_info", {})
        except (json.JSONDecodeError, TypeError):
            info = {}
        # fallback: 直接从 user_info 取
        if not info.get("nickname"):
            info = u.get("user_info", {})
        if info.get("nickname"):
            parsed.append(info)
    return parsed


def extract_video_url(post_data, api_response=None):
    """从作品数据中提取视频下载链接（多重 fallback）

    优先级:
    1. API 返回的高清链接
    2. 原始数据中的 play_addr
    3. 原始数据中的 download_addr
    """
    url = None

    # 从 API 高清接口响应提取
    if api_response:
        data = extract_result_data(api_response)
        if isinstance(data, dict):
            for key in ["video_url", "play_url", "download_url", "url",
                        "video_play_url", "play_addr"]:
                val = data.get(key)
                if not val:
                    continue
                if isinstance(val, str) and val.startswith("http"):
                    url = val
                elif isinstance(val, dict) and val.get("url_list"):
                    url = val["url_list"][0]
                elif isinstance(val, list) and val:
                    url = val[0] if isinstance(val[0], str) else None
                if url:
                    return url

    # 从原始作品数据提取
    if post_data:
        video = post_data.get("video", {})
        for addr_key in ["play_addr", "download_addr", "play_addr_h264"]:
            addr = video.get(addr_key, {})
            url_list = addr.get("url_list", [])
            if url_list:
                return url_list[0]

    return url


def download_file(url, filepath):
    """下载文件到本地"""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.douyin.com/",
    })
    with urllib.request.urlopen(req, timeout=180) as resp:
        with open(filepath, "wb") as f:
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                f.write(chunk)
    return os.path.getsize(filepath)


# ========== 微信公众号模块 ==========
# 微信公众号接口必须直接调用 TikHub REST API，不能走 MCP /tools/call

def _tikhub_rest_get(path, params):
    """直接调用 TikHub REST API（非 MCP），用于微信公众号等接口"""
    config = load_config()
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "User-Agent": "TikHub-Claude-Skill/1.0",
        "Accept": "application/json",
    }
    url = f"https://api.tikhub.io{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {err_body[:500]}"}
    except Exception as e:
        return {"error": str(e)}


def _load_ghid_cache():
    """加载 ghid 本地缓存"""
    if os.path.exists(GHID_CACHE_PATH):
        with open(GHID_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_ghid_cache(cache):
    """保存 ghid 本地缓存"""
    with open(GHID_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def wechat_mp_get_article_detail(article_url):
    """提取微信公众号文章内容

    短链 (mp.weixin.qq.com/s/XXXX) 用 JSON 接口（便宜，返回结构化数据）。
    长链 (?__biz=...) 用 HTML 接口（更贵，但对长链有效）——并将结果归一化为
    与 JSON 接口一致的结构。

    返回: dict，包含 title / author / publish_info / content / datetime
    其中 publish_info.user_id 就是该公众号的 ghid
    """
    is_long_url = "mp.weixin.qq.com/s?" in article_url or "__biz=" in article_url

    if not is_long_url:
        # 短链：JSON 接口
        resp = _tikhub_rest_get(
            "/api/v1/wechat_mp/web/fetch_mp_article_detail_json",
            {"url": article_url},
        )
        if "error" not in resp:
            return resp.get("data", resp)

    # 长链或 JSON 失败：用 HTML 接口，结果归一化
    # 保留 __biz/mid/idx/sn/chksm，去掉 sessionid/scene 等易过期参数
    if is_long_url:
        parsed = urllib.parse.urlparse(article_url)
        qs = urllib.parse.parse_qs(parsed.query)
        keep = {k: v for k, v in qs.items() if k in ("__biz", "mid", "idx", "sn", "chksm")}
        clean_url = (
            f"http://mp.weixin.qq.com/s?{urllib.parse.urlencode({k: v[0] for k, v in keep.items()})}"
            if keep else article_url
        )
    else:
        clean_url = article_url

    resp = _tikhub_rest_get(
        "/api/v1/wechat_mp/web/fetch_mp_article_detail_html",
        {"url": clean_url},
    )
    if "error" in resp:
        return resp

    raw = resp.get("data", resp)
    # 将 HTML 接口返回归一化，使调用方可统一处理
    return {
        "title": raw.get("title", ""),
        "author": raw.get("username", raw.get("author", "")),
        "publish_info": {
            "user_id": raw.get("userid", ""),
            "source": "html",
        },
        "content": {
            "raw_content": [{"type": "p", "text": raw.get("content", "")}],
        },
        "datetime": raw.get("time", ""),
        "_html_source": True,  # 标记来源，方便调试
    }


def wechat_mp_extract_ghid(article_url, account_name=None):
    """从任意一篇该公众号的文章 URL 中提取 ghid，并写入本地缓存

    article_url: 该公众号任意一篇文章的链接
    account_name: 可选，指定后会同时缓存 name → ghid 的映射
    返回: ghid 字符串，失败返回 None
    """
    data = wechat_mp_get_article_detail(article_url)
    ghid = data.get("publish_info", {}).get("user_id", "")
    if ghid and ghid.startswith("gh_"):
        cache = _load_ghid_cache()
        cache[f"_url_{article_url}"] = ghid
        if account_name:
            cache[account_name] = ghid
        _save_ghid_cache(cache)
        return ghid
    return None


def wechat_mp_get_article_list(ghid, offset="", max_pages=1):
    """获取公众号文章列表

    ghid: 公众号 ID（格式 gh_xxxxxxxx）
    offset: 翻页游标，首页传 "" 或 "0"
    max_pages: 最多拉取页数（每页约 10 条）
    返回: list of article dicts，每个包含 Title / ContentUrl / send_time / CoverImgUrl
    """
    articles = []
    current_offset = offset
    for _ in range(max_pages):
        resp = _tikhub_rest_get(
            "/api/v1/wechat_mp/web/fetch_mp_article_list",
            {"ghid": ghid, "offset": current_offset},
        )
        if "error" in resp:
            break
        data = resp.get("data", {})
        batch = data.get("list", [])
        articles.extend(batch)
        next_offset = data.get("offset", "")
        if not next_offset or next_offset == current_offset or not batch:
            break
        current_offset = next_offset
        if max_pages > 1:
            time.sleep(0.5)  # 避免过快请求
    return articles


def _sogou_search_article_url(account_name):
    """尝试通过搜狗微信搜索拿到一篇该公众号的文章链接

    成功返回搜狗跳转链接（str），失败返回 None
    注意：搜狗有反爬，此函数不保证成功
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://weixin.sogou.com/",
    }
    try:
        # 先访问首页获取 cookie
        urllib.request.urlopen(
            urllib.request.Request("https://weixin.sogou.com/", headers=headers),
            timeout=10,
        )
    except Exception:
        pass

    try:
        query = urllib.parse.quote(account_name)
        url = f"https://weixin.sogou.com/weixin?type=2&query={query}&ie=utf8"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("gbk", errors="replace")
        links = re.findall(r'href="(/link\?url=[^"&]+)', html)
        if links:
            return "https://weixin.sogou.com" + links[0]
    except Exception:
        pass
    return None


def _sogou_url_to_mp_url(sogou_url):
    """调用 TikHub 将搜狗跳转链接转换为微信文章链接

    成功返回 mp.weixin.qq.com URL，失败返回 None
    """
    resp = _tikhub_rest_get(
        "/api/v1/wechat_mp/web/fetch_mp_article_url",
        {"sogou_url": sogou_url},
    )
    weixin_url = resp.get("data", {}).get("weixin_url", "")
    if weixin_url and "mp.weixin.qq.com" in weixin_url and "antispider" not in weixin_url:
        return weixin_url
    return None


def wechat_mp_get_ghid(account_name, fallback_article_url=None):
    """根据公众号名称获取 ghid

    查找顺序：
    1. 本地缓存
    2. 搜狗搜索 → TikHub URL 转换 → 提取 ghid（可能因反爬失败）
    3. 如果提供了 fallback_article_url，直接从该文章 URL 提取

    返回: (ghid, source) 或 (None, "not_found")
    source 为 "cache" / "sogou" / "fallback" / "not_found"
    """
    # 1. 查缓存
    cache = _load_ghid_cache()
    if account_name in cache:
        return cache[account_name], "cache"

    # 2. 尝试搜狗路径
    sogou_url = _sogou_search_article_url(account_name)
    if sogou_url:
        mp_url = _sogou_url_to_mp_url(sogou_url)
        if mp_url:
            ghid = wechat_mp_extract_ghid(mp_url, account_name=account_name)
            if ghid:
                return ghid, "sogou"

    # 3. fallback：用户提供的文章 URL
    if fallback_article_url:
        ghid = wechat_mp_extract_ghid(fallback_article_url, account_name=account_name)
        if ghid:
            return ghid, "fallback"

    return None, "not_found"


def wechat_mp_get_articles_by_name(account_name, fallback_article_url=None, max_pages=1):
    """主入口：给定公众号名称，返回文章列表

    account_name: 公众号名称（如"李继刚"）
    fallback_article_url: 若自动查找失败，可提供该公众号任一文章链接
    max_pages: 拉取页数
    返回: {"ghid": str, "source": str, "articles": list} 或 {"error": str}
    """
    ghid, source = wechat_mp_get_ghid(account_name, fallback_article_url)
    if not ghid:
        return {
            "error": (
                f"无法获取「{account_name}」的 ghid。"
                "请在微信中打开该公众号任意一篇文章，复制链接后作为 fallback_article_url 参数传入。"
            )
        }
    articles = wechat_mp_get_article_list(ghid, max_pages=max_pages)
    return {"ghid": ghid, "source": source, "articles": articles}


def wechat_mp_extract_text(article_data):
    """从文章详情数据中提取纯文本内容

    article_data: wechat_mp_get_article_detail() 的返回值
    返回: 纯文本字符串
    """
    content = article_data.get("content", {})
    blocks = content.get("raw_content", [])
    lines = []
    for block in blocks:
        btype = block.get("type", "")
        text = block.get("text", "").strip()
        if btype in ("p", "h5", "section") and text:
            lines.append(text)
        elif btype == "image":
            pass  # 跳过图片
    return "\n\n".join(lines)


# ========== CLI 入口 ==========

def main():
    parser = argparse.ArgumentParser(description="TikHub MCP API 客户端")
    sub = parser.add_subparsers(dest="command")

    ls = sub.add_parser("list", help="列出可用工具")
    ls.add_argument("--keyword", "-k", help="按关键词过滤")
    ls.add_argument("--platform", "-p", help="按平台过滤 (douyin/tiktok/xiaohongshu/...)")

    cl = sub.add_parser("call", help="调用工具（MCP 优先，自动降级 REST）")
    cl.add_argument("tool_name", help="工具名称")
    cl.add_argument("--args", "-a", help="JSON 格式参数", default="{}")

    rc = sub.add_parser("rest-call", help="直接走 REST API 调用（跳过 MCP 代理）")
    rc.add_argument("tool_name", help="工具名称")
    rc.add_argument("--args", "-a", help="JSON 格式参数", default="{}")

    # 微信公众号子命令
    mp = sub.add_parser("wechat-mp", help="微信公众号操作")
    mp_sub = mp.add_subparsers(dest="mp_command")

    # wechat-mp articles: 获取文章列表
    mp_articles = mp_sub.add_parser("articles", help="获取公众号文章列表")
    mp_articles.add_argument("account_name", help="公众号名称")
    mp_articles.add_argument("--url", "-u", help="该公众号任意一篇文章链接（用于首次获取 ghid）")
    mp_articles.add_argument("--pages", "-p", type=int, default=1, help="拉取页数（默认1）")
    mp_articles.add_argument("--ghid", "-g", help="直接指定 ghid（跳过查找步骤）")

    # wechat-mp article: 提取单篇文章内容
    mp_article = mp_sub.add_parser("article", help="提取文章内容")
    mp_article.add_argument("article_url", help="文章链接")
    mp_article.add_argument("--text-only", "-t", action="store_true", help="只输出纯文本")

    # wechat-mp ghid: 查找/缓存 ghid
    mp_ghid = mp_sub.add_parser("ghid", help="获取或缓存公众号 ghid")
    mp_ghid.add_argument("account_name", help="公众号名称")
    mp_ghid.add_argument("--url", "-u", help="该公众号任意一篇文章链接")

    # wechat-mp cache: 查看缓存
    mp_sub.add_parser("cache", help="查看 ghid 缓存")

    args = parser.parse_args()

    if args.command == "list":
        tools = list_tools(keyword=args.keyword, platform=args.platform)
        print(json.dumps(tools, indent=2, ensure_ascii=False))

    elif args.command == "call":
        try:
            tool_args = json.loads(args.args)
        except json.JSONDecodeError:
            print(json.dumps({"error": f"参数 JSON 格式错误: {args.args}"}, ensure_ascii=False))
            sys.exit(1)
        result = call_tool(args.tool_name, tool_args)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "rest-call":
        try:
            tool_args = json.loads(args.args)
        except json.JSONDecodeError:
            print(json.dumps({"error": f"参数 JSON 格式错误: {args.args}"}, ensure_ascii=False))
            sys.exit(1)
        result = rest_call(args.tool_name, tool_args)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "wechat-mp":
        if not args.mp_command:
            mp.print_help()
            return

        if args.mp_command == "articles":
            if args.ghid:
                articles = wechat_mp_get_article_list(args.ghid, max_pages=args.pages)
                result = {"ghid": args.ghid, "source": "manual", "articles": articles}
            else:
                result = wechat_mp_get_articles_by_name(
                    args.account_name,
                    fallback_article_url=args.url,
                    max_pages=args.pages,
                )
            if "error" in result:
                print(result["error"])
                sys.exit(1)
            print(f"ghid: {result['ghid']} (来源: {result['source']})")
            print(f"共 {len(result['articles'])} 篇文章:\n")
            for i, a in enumerate(result["articles"], 1):
                import datetime
                ts = a.get("send_time", 0)
                date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
                print(f"{i:3d}. [{date}] {a.get('Title', '(无标题)')}")
                print(f"     {a.get('ContentUrl', '')}")
                print()

        elif args.mp_command == "article":
            data = wechat_mp_get_article_detail(args.article_url)
            if "error" in data:
                print(json.dumps(data, ensure_ascii=False))
                sys.exit(1)
            if args.text_only:
                print(f"标题: {data.get('title', '')}")
                print(f"作者: {data.get('author', '')}")
                print(f"ghid: {data.get('publish_info', {}).get('user_id', '')}")
                print()
                print(wechat_mp_extract_text(data))
            else:
                print(json.dumps(data, indent=2, ensure_ascii=False))

        elif args.mp_command == "ghid":
            ghid, source = wechat_mp_get_ghid(args.account_name, fallback_article_url=args.url)
            if ghid:
                print(f"ghid: {ghid} (来源: {source})")
            else:
                print(f"未找到「{args.account_name}」的 ghid")
                print("请用 --url 参数提供该公众号的任意一篇文章链接")
                sys.exit(1)

        elif args.mp_command == "cache":
            cache = _load_ghid_cache()
            if not cache:
                print("缓存为空")
            else:
                for name, ghid in cache.items():
                    if not name.startswith("_url_"):
                        print(f"  {name}: {ghid}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
