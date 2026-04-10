#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书 OAuth 2.0 授权服务器
运行此脚本以获取用户授权 Token。

作者：凯寓 (KAIYU)
"""

import json
import sys
import time
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

# ─── 路径定义 ───────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPTS_DIR / "config.json"
CACHE_DIR = SCRIPTS_DIR / "cache"
USER_TOKEN_PATH = CACHE_DIR / "user_token.json"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """处理 OAuth 回调"""

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body style='text-align:center;padding-top:80px;font-family:sans-serif'>"
                "<h1>授权成功！</h1>"
                "<p>你可以关闭这个页面，回到终端继续操作。</p>"
                "</body></html>".encode("utf-8")
            )
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body style='text-align:center;padding-top:80px;font-family:sans-serif'>"
                "<h1>授权失败</h1>"
                "<p>没有收到授权码，请重试。</p>"
                "</body></html>".encode("utf-8")
            )

    def log_message(self, format, *args):
        pass


def get_user_access_token(app_id: str, app_secret: str, code: str) -> dict:
    """用授权码换取用户 Token"""
    # Step 1: 获取 app_access_token
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    data = r.json()
    if data.get("code") != 0:
        raise Exception(f"获取应用凭证失败: {data.get('msg')}")

    # Step 2: 用 code 换 user_access_token
    r = requests.post(
        "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token",
        json={"grant_type": "authorization_code", "code": code},
        headers={
            "Authorization": f"Bearer {data['app_access_token']}",
            "Content-Type": "application/json",
        },
    )
    result = r.json()
    if result.get("code") != 0:
        raise Exception(f"获取用户 Token 失败: {result.get('msg')} (code: {result.get('code')})")

    return result.get("data", {})


def main():
    # 加载配置
    if not CONFIG_PATH.exists():
        print(f"错误: 未找到 config.json，请先运行 setup.py")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    app_id = config["app_id"]
    app_secret = config["app_secret"]
    redirect_uri = "http://127.0.0.1:8080/callback"
    scopes = config.get("oauth_scopes", "docx:document docx:document:readonly wiki:wiki:readonly")

    print()
    print("=" * 56)
    print("  飞书 OAuth 授权")
    print("=" * 56)
    print()
    print("  确保已在飞书开放平台 → 安全设置 → 重定向 URL 中添加：")
    print(f"  {redirect_uri}")
    print()
    print("  正在启动本地服务并打开浏览器...")

    # 启动本地回调服务
    server = HTTPServer(("127.0.0.1", 8080), OAuthCallbackHandler)
    server.auth_code = None

    auth_url = (
        f"https://open.feishu.cn/open-apis/authen/v1/authorize?"
        f"app_id={app_id}&redirect_uri={redirect_uri}&scope={scopes}&state=oauth"
    )

    webbrowser.open(auth_url)
    print("  等待你在浏览器中完成授权...")

    while server.auth_code is None:
        server.handle_request()

    print("  授权码已收到，正在换取 Token...")

    token_data = get_user_access_token(app_id, app_secret, server.auth_code)
    token_data["_token_time"] = time.time()

    # 保存 Token
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)

    print()
    print(f"  授权成功！Token 已保存到 {USER_TOKEN_PATH}")
    print(f"  Access Token 有效期: {token_data.get('expires_in', 7200)} 秒（过期自动刷新）")
    print(f"  Refresh Token 有效期: {token_data.get('refresh_expires_in', 2592000)} 秒（约 30 天）")
    print()


if __name__ == "__main__":
    main()
