#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书助手 · 安装引导 v2
借鉴 lark-cli 的丝滑配置体验，用户只需点几次链接即可完成全部配置。
无 npm 环境时自动 fallback 到手动配置流程。

作者：凯寓 (KAIYU)
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ─── 路径定义 ───────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent
CONFIG_PATH = SCRIPTS_DIR / "config.json"
CACHE_DIR = SCRIPTS_DIR / "cache"
USER_TOKEN_PATH = CACHE_DIR / "user_token.json"
CONTACTS_CACHE_PATH = CACHE_DIR / "contacts.json"
SPACES_CACHE_PATH = CACHE_DIR / "wiki_spaces.json"
LARK_CLI_CONFIG = Path.home() / ".lark-cli" / "config.json"


# ─── 工具函数 ────────────────────────────────────────────────
def check_python_version():
    if sys.version_info < (3, 8):
        print(f"\n  Python 版本太低（当前 {sys.version_info.major}.{sys.version_info.minor}），需要 3.8+")
        print("  请到 https://www.python.org/downloads/ 下载安装。\n")
        sys.exit(1)


def ensure_requests():
    try:
        import requests  # noqa: F401
    except ImportError:
        print("\n  正在安装 requests 库...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "requests", "-q"],
            stdout=subprocess.DEVNULL,
        )
        print("  ✅ requests 已安装")


def ensure_utf8():
    if sys.platform == "win32":
        os.system("")
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")


def is_headless():
    """检测是否为无头环境（服务器/Docker/无 DISPLAY）"""
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return True
    if sys.platform == "linux" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return True
    if os.path.exists("/.dockerenv"):
        return True
    return False


def safe_open_url(url):
    """打开 URL，无头环境下只打印链接"""
    if is_headless():
        print(f"  请在浏览器中打开：{url}")
    else:
        webbrowser.open(url)


def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")


def print_header(title, step=None, total=None):
    print()
    print("=" * 56)
    if step and total:
        print(f"  第 {step} 步（共 {total} 步）：{title}")
    else:
        print(f"  {title}")
    print("=" * 56)
    print()


def ask(prompt, default="", required=True):
    while True:
        hint = f"  {prompt}"
        if default:
            hint += f"（直接回车使用: {default}）"
        hint += ": "
        try:
            value = input(hint).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  已取消安装。\n")
            sys.exit(0)
        if not value and default:
            return default
        if not value and required:
            print("  ⚠ 不能为空，请重新输入。\n")
            continue
        return value


def ask_yes_no(prompt, default_yes=True):
    hint = "Y/n" if default_yes else "y/N"
    try:
        value = input(f"  {prompt} [{hint}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n\n  已取消安装。\n")
        sys.exit(0)
    if not value:
        return default_yes
    return value in ("y", "yes", "是")


def run_blocking_cmd(cmd, extract_url_pattern=None, timeout=300):
    """运行阻塞命令，实时打印输出，可选提取 URL。返回 (exit_code, full_output)"""
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    output_lines = []
    url_found = None
    start = time.time()

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if time.time() - start > timeout:
            process.kill()
            break
        if line:
            output_lines.append(line)
            # 提取 URL
            if extract_url_pattern and not url_found:
                match = re.search(extract_url_pattern, line)
                if match:
                    url_found = match.group(0)
                    print(f"\n  请在浏览器中打开以下链接：\n")
                    print(f"  {url_found}\n")

    return process.returncode, "".join(output_lines), url_found


# ─── OAuth 回调 ──────────────────────────────────────────────
class _OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "<html><body style='text-align:center;padding-top:80px;font-family:sans-serif'>"
                "<h1>✅ 授权成功！</h1>"
                "<p>你可以关闭这个页面，回到终端继续操作。</p>"
                "</body></html>".encode("utf-8")
            )
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Failed</h1></body></html>")

    def log_message(self, format, *args):
        pass


def do_oauth(app_id, app_secret, scopes):
    """执行 OAuth 授权流程，返回 token 数据"""
    import requests

    redirect_uri = "http://127.0.0.1:8080/callback"
    auth_url = (
        f"https://open.feishu.cn/open-apis/authen/v1/authorize?"
        f"app_id={app_id}&redirect_uri={redirect_uri}&scope={scopes}&state=setup"
    )

    print("  正在打开浏览器...")
    print(f"  如果没有自动打开，请手动访问：\n  {auth_url}\n")
    safe_open_url(auth_url)

    server = HTTPServer(("127.0.0.1", 8080), _OAuthHandler)
    server.auth_code = None

    print("  等待授权...")
    while server.auth_code is None:
        server.handle_request()

    # 用 code 换 token
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    app_token_data = r.json()
    if app_token_data.get("code") != 0:
        raise Exception(f"获取应用凭证失败: {app_token_data.get('msg')}")

    r = requests.post(
        "https://open.feishu.cn/open-apis/authen/v1/oidc/access_token",
        json={"grant_type": "authorization_code", "code": server.auth_code},
        headers={
            "Authorization": f"Bearer {app_token_data['app_access_token']}",
            "Content-Type": "application/json",
        },
    )
    data = r.json()
    if data.get("code") != 0:
        raise Exception(f"授权失败: {data.get('msg')}")

    token_data = data.get("data", {})
    token_data["_token_time"] = time.time()
    return token_data


def fetch_contacts(app_id, app_secret):
    """拉取通讯录"""
    import requests
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    data = r.json()
    if data.get("code") != 0:
        return None, f"获取凭证失败: {data.get('msg')}"

    r = requests.get(
        "https://open.feishu.cn/open-apis/contact/v3/users",
        headers={"Authorization": f"Bearer {data['tenant_access_token']}"},
        params={"department_id": "0", "page_size": 50},
    )
    data = r.json()
    if data.get("code") != 0:
        return None, f"获取通讯录失败: {data.get('msg')}"

    items = data.get("data", {}).get("items", [])
    contacts = [
        {
            "name": u.get("name", ""),
            "open_id": u.get("open_id", ""),
            "mobile": u.get("mobile", ""),
            "status": "已激活" if u.get("status", {}).get("is_activated") else "未激活",
        }
        for u in items
    ]
    return contacts, None


def fetch_wiki_spaces(user_token):
    """拉取知识库空间列表"""
    import requests
    all_spaces = []
    page_token = None
    while True:
        params = {"page_size": 50}
        if page_token:
            params["page_token"] = page_token
        r = requests.get(
            "https://open.feishu.cn/open-apis/wiki/v2/spaces",
            headers={"Authorization": f"Bearer {user_token}"},
            params=params,
        )
        data = r.json()
        if data.get("code") != 0:
            return None, f"获取知识库失败: {data.get('msg')}"
        items = data.get("data", {}).get("items", [])
        for s in items:
            all_spaces.append({
                "name": s.get("name", ""),
                "space_id": s.get("space_id", ""),
                "description": s.get("description", ""),
            })
        if not data.get("data", {}).get("has_more"):
            break
        page_token = data.get("data", {}).get("page_token")
    return all_spaces, None


# ─── lark-cli 检测与安装 ─────────────────────────────────────
def ensure_node():
    """确保 Node.js 已安装。没有时尝试自动安装。"""
    if shutil.which("node"):
        return True

    print("  未检测到 Node.js，尝试自动安装...")

    # macOS: 优先 brew
    if sys.platform == "darwin" and shutil.which("brew"):
        try:
            print("  通过 Homebrew 安装 Node.js...")
            subprocess.run(["brew", "install", "node"], check=True, timeout=300)
            if shutil.which("node"):
                print("  ✅ Node.js 已安装")
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # Linux: apt / yum / dnf
    if sys.platform == "linux":
        for pkg_mgr, cmd in [
            ("apt", ["sudo", "apt", "install", "-y", "nodejs", "npm"]),
            ("dnf", ["sudo", "dnf", "install", "-y", "nodejs", "npm"]),
            ("yum", ["sudo", "yum", "install", "-y", "nodejs", "npm"]),
        ]:
            if shutil.which(pkg_mgr):
                try:
                    print(f"  通过 {pkg_mgr} 安装 Node.js...")
                    subprocess.run(cmd, check=True, timeout=300)
                    if shutil.which("node"):
                        print("  ✅ Node.js 已安装")
                        return True
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    pass
                break

    # Windows: winget
    if sys.platform == "win32" and shutil.which("winget"):
        try:
            print("  通过 winget 安装 Node.js...")
            subprocess.run(["winget", "install", "OpenJS.NodeJS.LTS", "--accept-source-agreements", "--accept-package-agreements"], check=True, timeout=300)
            if shutil.which("node"):
                print("  ✅ Node.js 已安装")
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    print("  ⚠ 无法自动安装 Node.js")
    print("  请手动安装：https://nodejs.org/")
    return False


def ensure_lark_cli():
    """确保 lark-cli 已安装。返回 True 表示可用。"""
    if shutil.which("lark-cli"):
        return True

    # 先确保有 Node.js / npm
    if not shutil.which("npm"):
        if not ensure_node():
            return False
        # brew/apt 装完后 npm 可能在新 PATH 里，刷新一下
        if not shutil.which("npm"):
            return False

    npm = shutil.which("npm")
    print("  正在安装 lark-cli（飞书官方命令行工具）...")
    try:
        subprocess.run(
            [npm, "install", "-g", "@larksuite/cli"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=120,
        )
        print("  ✅ lark-cli 已安装")
        return shutil.which("lark-cli") is not None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("  ⚠ lark-cli 安装失败，将使用手动配置流程")
        return False


def read_lark_cli_app_id():
    """从 lark-cli 配置中读取 appId"""
    if not LARK_CLI_CONFIG.exists():
        return None
    try:
        data = json.loads(LARK_CLI_CONFIG.read_text(encoding="utf-8"))
        apps = data.get("apps", [])
        if apps:
            return apps[-1].get("appId")  # 取最新的应用
    except (json.JSONDecodeError, KeyError):
        pass
    return None


# ─── 丝滑流程（使用 lark-cli） ──────────────────────────────
def smooth_setup():
    """使用 lark-cli 的丝滑配置流程"""
    total_steps = 2

    # ══════════════════════════════════════════════════════════
    # 第 1 步：创建飞书应用
    # ══════════════════════════════════════════════════════════
    print_header("创建飞书应用", 1, total_steps)
    print("  接下来会打开一个链接，你只需在网页上点几下，")
    print("  应用创建、权限配置、版本发布全部自动完成。")
    print()
    input("  按回车开始 → ")
    print()
    print("  等待你在浏览器中完成配置...")

    url_pattern = r"https://open\.feishu\.cn/page/cli\?[^\s]+"
    code, output, url = run_blocking_cmd(
        ["lark-cli", "config", "init", "--new"],
        extract_url_pattern=url_pattern,
        timeout=300,
    )

    if code != 0:
        print(f"  ❌ 应用创建失败。输出:\n{output}")
        return False

    # 从输出中提取 appId
    app_id = read_lark_cli_app_id()
    if not app_id:
        # 尝试从输出中提取
        match = re.search(r"cli_[a-f0-9]+", output)
        if match:
            app_id = match.group(0)

    if not app_id:
        print("  ❌ 无法获取 App ID，请重试。")
        return False

    print(f"  ✅ 应用创建成功！App ID: {app_id}")

    # ══════════════════════════════════════════════════════════
    # 第 2 步：授权登录
    # ══════════════════════════════════════════════════════════
    print_header("授权登录", 2, total_steps)
    print("  接下来会打开一个链接，点击授权即可。")
    print("  这一步会自动为应用开通所有常用权限。")
    print()
    input("  按回车开始 → ")
    print()
    print("  等待你在浏览器中完成授权...")

    auth_url_pattern = r"https://accounts\.feishu\.cn/oauth/v1/device/verify\?[^\s]+"
    code, output, url = run_blocking_cmd(
        ["lark-cli", "auth", "login", "--domain", "all"],
        extract_url_pattern=auth_url_pattern,
        timeout=300,
    )

    if code != 0:
        print(f"  ⚠ 授权出错，输出:\n{output}")
        print("  你可以稍后手动运行: lark-cli auth login --domain all")
    else:
        print("  ✅ 授权成功！")

    # ══════════════════════════════════════════════════════════
    # 保存配置 + 拉取数据
    # ══════════════════════════════════════════════════════════
    print()
    print("  正在保存配置...")

    config = {
        "app_id": app_id,
        "app_secret": "",
        "default_chat_id": "",
        "oauth_scopes": "",
        "team_members": {},
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("  ✅ 配置文件已保存")
    print()
    print("  用户身份操作（文档/日历/知识库/多维表格/邮箱等）")
    print("  将自动通过 lark-cli 代理，无需额外配置。")

    # 通过 lark-cli 拉取通讯录
    print("  正在获取通讯录...")
    try:
        result = subprocess.run(
            ["lark-cli", "api", "GET", "/open-apis/contact/v3/users?department_id=0&page_size=50", "--as", "bot"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            items = data.get("data", {}).get("items", [])
            contacts = [
                {"name": u.get("name", ""), "open_id": u.get("open_id", ""),
                 "mobile": u.get("mobile", ""), "status": "已激活" if u.get("status", {}).get("is_activated") else "未激活"}
                for u in items
            ]
            with open(CONTACTS_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(contacts, f, indent=2, ensure_ascii=False)
            config["team_members"] = {c["name"]: c["open_id"] for c in contacts if c["name"]}
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"  ✅ 找到 {len(contacts)} 位成员")
        else:
            print(f"  ⚠ 获取通讯录失败，可稍后使用时自动获取")
    except Exception as e:
        print(f"  ⚠ 获取通讯录出错: {e}")

    return True


# ─── 手动流程（无 lark-cli 的 fallback） ────────────────────
def legacy_setup():
    """原有的手动配置流程"""
    total_steps = 4

    # 第 1 步：获取凭证
    print_header("获取飞书应用凭证", 1, total_steps)
    print("  你需要在飞书开放平台创建一个应用。")
    print()

    if ask_yes_no("要自动打开飞书开放平台吗？"):
        safe_open_url("https://open.feishu.cn/app")

    print()
    print("  ┌─────────────────────────────────────────┐")
    print("  │ 1. 点击「创建应用」→「企业自建应用」    │")
    print("  │ 2. 填写应用名称（比如「我的飞书助手」） │")
    print("  │ 3. 进入应用 →「凭证与基础信息」         │")
    print("  │ 4. 复制 App ID 和 App Secret            │")
    print("  └─────────────────────────────────────────┘")
    print()

    import requests

    app_id = ask("App ID（应用ID，以 cli_ 开头）")
    app_secret = ask("App Secret（应用密钥）")

    print("\n  正在验证凭证...")
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
    )
    if r.json().get("code") != 0:
        print(f"  ❌ 凭证验证失败: {r.json().get('msg')}")
        sys.exit(1)
    print("  ✅ 凭证验证通过！")

    # 第 2 步：配置权限
    print_header("配置应用权限", 2, total_steps)
    print("  ┌──────────────────────────────────────────────────┐")
    print("  │ 在飞书开放平台 → 你的应用：                      │")
    print("  │ 1. 添加「机器人」能力                            │")
    print("  │ 2.「权限管理」→「批量导入/导出权限」             │")
    print("  │ 3. 导入 scopes.json 的内容                       │")
    print("  │ 4.「版本管理与发布」→ 创建版本 → 申请发布        │")
    print("  │ 5. 可用范围建议选「所有员工」                    │")
    print("  └──────────────────────────────────────────────────┘")
    print()

    scopes_path = SCRIPTS_DIR / "scopes.json"
    if scopes_path.exists():
        safe_open_url(f"file:///{scopes_path.as_posix()}")
        print("  scopes.json 已在浏览器中打开，请复制内容粘贴到飞书平台。")

    print()
    input("  完成权限配置并发布后，按回车继续...")

    # 第 3 步：OAuth 授权
    print_header("授权登录", 3, total_steps)

    oauth_scopes = (
        "offline_access auth:user.id:read "
        "docx:document docx:document:readonly docx:document:create docx:document:write_only "
        "wiki:wiki wiki:wiki:readonly wiki:node:read "
        "bitable:app bitable:app:readonly "
        "calendar:calendar calendar:calendar:readonly calendar:calendar:read "
        "calendar:calendar:create calendar:calendar:delete calendar:calendar:update "
        "calendar:calendar.event:create calendar:calendar.event:delete "
        "calendar:calendar.event:read calendar:calendar.event:update "
        "calendar:calendar.free_busy:read "
        "im:message:readonly im:message.group_msg:get_as_user im:message.p2p_msg:get_as_user "
        "im:message.pins:read im:message.pins:write_only "
        "im:message.reactions:read im:message.reactions:write_only "
        "contact:user.base:readonly contact:user.basic_profile:readonly contact:user:search "
        "mail:user_mailbox:readonly mail:user_mailbox.message:readonly "
        "mail:user_mailbox.message:modify mail:user_mailbox.message.address:read "
        "mail:user_mailbox.message.body:read mail:user_mailbox.message.subject:read "
        "mail:event mail:user_mailbox.mail_contact:read mail:user_mailbox.mail_contact:write "
        "task:task:read task:task:write task:tasklist:read task:tasklist:write task:comment:write "
        "vc:meeting.meetingevent:read vc:meeting.search:read vc:note:read "
        "board:whiteboard:node:create board:whiteboard:node:delete board:whiteboard:node:read "
        "docs:event:subscribe docs:document.comment:delete"
    )

    config = {
        "app_id": app_id,
        "app_secret": app_secret,
        "default_chat_id": "",
        "oauth_scopes": oauth_scopes,
        "team_members": {},
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("  ┌──────────────────────────────────────────────────┐")
    print("  │ 先在飞书开放平台 → 安全设置 → 重定向 URL 添加： │")
    print("  │ http://127.0.0.1:8080/callback                   │")
    print("  └──────────────────────────────────────────────────┘")
    print()

    safe_open_url(f"https://open.feishu.cn/app/{app_id}/security")
    token_data = None

    if ask_yes_no("已添加重定向 URL，开始授权？"):
        try:
            token_data = do_oauth(app_id, app_secret, oauth_scopes)
            with open(USER_TOKEN_PATH, "w", encoding="utf-8") as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            print("  ✅ 授权成功！")
        except Exception as e:
            print(f"\n  ⚠ 授权出错: {e}")
            print("  稍后可运行 oauth_server.py 重试。")

    # 第 4 步：拉取数据
    print_header("获取团队信息", 4, total_steps)
    pull_team_data(config, token_data)


# ─── 通用：拉取团队数据 ─────────────────────────────────────
def pull_team_data(config, token_data):
    """拉取通讯录和知识库"""
    app_id = config["app_id"]
    app_secret = config["app_secret"]

    # 通讯录
    print("  正在获取通讯录...")
    contacts, err = fetch_contacts(app_id, app_secret)
    if err:
        print(f"  ⚠ 获取通讯录失败: {err}")
        python_cmd = "python" if sys.platform == "win32" else "python3"
        print(f"  稍后可运行: {python_cmd} scripts/feishu_client.py refresh-contacts")
    else:
        with open(CONTACTS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2, ensure_ascii=False)
        config["team_members"] = {c["name"]: c["open_id"] for c in contacts if c["name"]}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"  ✅ 找到 {len(contacts)} 位成员")

    # 知识库
    if token_data:
        print("  正在获取知识库列表...")
        spaces, err = fetch_wiki_spaces(token_data["access_token"])
        if err:
            print(f"  ⚠ 获取知识库失败: {err}")
        else:
            with open(SPACES_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(spaces, f, indent=2, ensure_ascii=False)
            print(f"  ✅ 找到 {len(spaces)} 个知识库空间")
    else:
        print("  ⚠ 跳过知识库获取（需要先完成 OAuth 授权）")


# ─── 完成提示 ────────────────────────────────────────────────
def print_finish():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║           安装完成！                         ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()
    print("  现在可以在 Claude Code 中直接用自然语言操作飞书：")
    print()
    print('    "给张三发一条飞书消息"')
    print('    "看看知识库里有什么文章"')
    print('    "查一下多维表格里的数据"')
    print('    "帮我搜一下飞书邮箱里的邮件"')
    print()
    print(f"  配置文件：{CONFIG_PATH}")
    print()


# ─── 主流程 ──────────────────────────────────────────────────
def main():
    check_python_version()
    ensure_requests()
    ensure_utf8()
    clear_screen()

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║        飞书助手 · 安装引导                   ║")
    print("  ║        让 AI 帮你操作飞书                    ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    # 检测 lark-cli
    has_lark_cli = ensure_lark_cli()

    if has_lark_cli:
        print()
        print("  检测到 lark-cli，将使用丝滑配置流程（点几个链接即可）。")
        print()
        input("  准备好了吗？按回车开始 → ")
        success = smooth_setup()
        if not success:
            print("\n  丝滑流程未完成，切换到手动配置...\n")
            legacy_setup()
    else:
        print()
        if shutil.which("npm"):
            print("  ⚠ lark-cli 安装失败，使用手动配置流程。")
        else:
            print("  未检测到 npm，使用手动配置流程。")
            print("  提示：安装 Node.js 后可获得更丝滑的配置体验。")
        print()
        input("  按回车开始 → ")
        legacy_setup()

    print_finish()


if __name__ == "__main__":
    main()
