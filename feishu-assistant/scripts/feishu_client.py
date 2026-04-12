#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书助手 API 客户端
通用版本，所有个性化配置从 config.json 读取。

作者：凯寓 (KAIYU)
"""

import json
import os
import re
import sys
import time
import argparse
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
import requests


# ─── 路径定义 ───────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
CACHE_DIR = SCRIPTS_DIR / "cache"
CONFIG_PATH = SCRIPTS_DIR / "config.json"
USER_TOKEN_PATH = CACHE_DIR / "user_token.json"
CONTACTS_CACHE_PATH = CACHE_DIR / "contacts.json"
SPACES_CACHE_PATH = CACHE_DIR / "wiki_spaces.json"


def ensure_utf8():
    """确保控制台能正常显示中文"""
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ─── FeishuClient 核心类 ────────────────────────────────────
class FeishuClient:
    """飞书 API 客户端"""

    PERMISSION_ERROR_CODES = {99991668, 99991672, 99991663, 99991664}

    def __init__(self, app_id: str, app_secret: str, user_token_file: Optional[str] = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self._access_token = None
        self._token_expire_time = 0
        self.user_token_file = user_token_file
        self._user_token_data = None

    def get_access_token(self, token_type: str = "app") -> str:
        """获取 access_token（app 或 tenant）"""
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token

        if token_type == "tenant":
            url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
            token_key = "tenant_access_token"
        else:
            url = f"{self.base_url}/auth/v3/app_access_token/internal"
            token_key = "app_access_token"

        response = requests.post(url, json={
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        })
        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"获取 access_token 失败: {data.get('msg')}")

        self._access_token = data[token_key]
        self._token_expire_time = time.time() + data["expire"] - 300
        return self._access_token

    def get_user_access_token(self) -> Optional[str]:
        """获取用户 access_token（自动刷新）"""
        if not self.user_token_file:
            return None

        token_path = Path(self.user_token_file)
        if not token_path.exists():
            return None

        if not self._user_token_data:
            with open(token_path, "r", encoding="utf-8") as f:
                self._user_token_data = json.load(f)

        token_time = self._user_token_data.get("_token_time", 0)
        expires_in = self._user_token_data.get("expires_in", 7200)

        if time.time() > token_time + expires_in - 300:
            self._refresh_user_token()

        return self._user_token_data.get("access_token")

    def _refresh_user_token(self):
        """刷新用户 access_token"""
        app_token = self.get_access_token("app")

        response = requests.post(
            f"{self.base_url}/authen/v1/oidc/refresh_access_token",
            json={
                "grant_type": "refresh_token",
                "refresh_token": self._user_token_data["refresh_token"],
            },
            headers={
                "Authorization": f"Bearer {app_token}",
                "Content-Type": "application/json",
            },
        )
        data = response.json()

        if data.get("code") != 0:
            # refresh_token 过期，自动重新授权
            print("\n" + "=" * 56)
            print("  用户授权已过期（超过 30 天未使用）")
            print("  正在自动启动授权流程...")
            print("=" * 56)

            oauth_script = SCRIPTS_DIR / "oauth_server.py"
            try:
                subprocess.run([sys.executable, str(oauth_script)], check=True)
                with open(self.user_token_file, "r", encoding="utf-8") as f:
                    self._user_token_data = json.load(f)
                print("\n  授权成功！继续执行...\n")
                return
            except subprocess.CalledProcessError as e:
                raise Exception(f"自动授权失败: {e}。请手动运行: {sys.executable} {oauth_script}")

        new_data = data.get("data", {})
        new_data["_token_time"] = time.time()
        self._user_token_data = new_data

        with open(self.user_token_file, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)

    def _request(self, method: str, endpoint: str, use_user_token: bool = False, **kwargs) -> Dict[str, Any]:
        """统一请求方法。优先用自有 token，不可用时 fallback 到 lark-cli"""
        if use_user_token:
            token = self.get_user_access_token()
            if not token:
                return self._request_via_lark_cli(method, endpoint, as_user=True, **kwargs)
        else:
            if not self.app_secret:
                return self._request_via_lark_cli(method, endpoint, as_user=False, **kwargs)
            token = self.get_access_token()

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.request(method, url, headers=headers, **kwargs)
        data = response.json()

        if data.get("code") != 0:
            self._raise_with_guidance(data, endpoint, use_user_token)

        return data.get("data", {})

    def _request_via_lark_cli(self, method: str, endpoint: str, as_user: bool = True, **kwargs) -> Dict[str, Any]:
        """通过 lark-cli 代理请求（无需自维护 token）"""
        import shutil
        if not shutil.which("lark-cli"):
            raise Exception(
                "lark-cli 未安装，请先运行: npm install -g @larksuite/cli && lark-cli config init --new && lark-cli auth login --domain all"
            )

        identity = "user" if as_user else "bot"
        url = f"/open-apis{endpoint}" if not endpoint.startswith("/open-apis") else endpoint
        cmd = ["lark-cli", "api", method, url, "--as", identity]

        # 处理 JSON body
        json_data = kwargs.get("json")
        if json_data:
            cmd.extend(["--data", json.dumps(json_data, ensure_ascii=False)])

        # 处理 query params
        params = kwargs.get("params")
        if params:
            cmd.extend(["--params", json.dumps(params, ensure_ascii=False)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"lark-cli 调用失败: {result.stderr or result.stdout}")

        data = json.loads(result.stdout)

        if data.get("code") != 0:
            self._raise_with_guidance(data, endpoint, as_user)

        return data.get("data", {})

    def _raise_with_guidance(self, data: Dict[str, Any], endpoint: str, use_user_token: bool):
        """解析 API 错误并给出修复建议"""
        code = data.get("code", 0)
        msg = data.get("msg", "")

        is_permission_error = (
            code in self.PERMISSION_ERROR_CODES
            or "Unauthorized" in msg
            or "permission" in msg.lower()
            or "scope" in msg.lower()
        )

        if is_permission_error:
            scope_match = re.search(r"[\w:]+:[\w:]+(?:readonly|read|write)", msg)
            missing_scope = scope_match.group(0) if scope_match else None

            hint_lines = [f"API 权限不足 (code={code}): {msg}", "", "修复步骤:"]

            if missing_scope:
                hint_lines.append(f"  1. 在 config.json 的 oauth_scopes 中添加: {missing_scope}")
            else:
                hint_lines.append("  1. 检查 config.json 的 oauth_scopes 是否包含该 API 所需的 scope")

            if use_user_token:
                hint_lines.append("  2. 运行 oauth_server.py 重新授权（scope 变更后必须重新授权）")
            else:
                hint_lines.append("  2. 在飞书开放平台后台确认应用已开通对应权限")

            hint_lines.append("  3. 飞书开放平台: https://open.feishu.cn/app")
            raise Exception("\n".join(hint_lines))

        raise Exception(f"API 请求失败 (code={code}): {msg}")

    # ─── 消息 ──────────────────────────────────────────────
    def send_message(self, receive_id: str, msg_type: str, content: str, receive_id_type: str = "open_id") -> Dict[str, Any]:
        """发送消息"""
        if msg_type == "text":
            content_obj = {"text": content}
        elif msg_type == "post":
            content_obj = {"zh_cn": {"title": "", "content": [[{"tag": "text", "text": content}]]}}
        else:
            content_obj = json.loads(content) if isinstance(content, str) else content

        payload = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(content_obj),
        }
        return self._request("POST", "/im/v1/messages", json=payload, params={"receive_id_type": receive_id_type})

    def get_chat_messages(self, chat_id: str, page_size: int = 20, start_time: Optional[str] = None, page_token: Optional[str] = None) -> Dict[str, Any]:
        """获取群组消息"""
        params = {"container_id_type": "chat", "container_id": chat_id, "page_size": min(page_size, 50)}
        if start_time:
            params["start_time"] = start_time
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", "/im/v1/messages", params=params)

    # ─── 群聊 ──────────────────────────────────────────────
    def create_chat(self, name: str, member_ids: List[str], description: str = "") -> Dict[str, Any]:
        """创建群聊并拉入成员"""
        payload = {
            "name": name,
            "user_id_list": member_ids,
        }
        if description:
            payload["description"] = description
        return self._request("POST", "/im/v1/chats", json=payload, params={"user_id_type": "open_id"})

    def add_chat_members(self, chat_id: str, member_ids: List[str]) -> Dict[str, Any]:
        """向群聊添加成员"""
        return self._request("POST", f"/im/v1/chats/{chat_id}/members", json={"id_list": member_ids}, params={"member_id_type": "open_id"})

    def remove_chat_members(self, chat_id: str, member_ids: List[str]) -> Dict[str, Any]:
        """从群聊移除成员"""
        return self._request("DELETE", f"/im/v1/chats/{chat_id}/members", json={"id_list": member_ids}, params={"member_id_type": "open_id"})

    def update_chat(self, chat_id: str, name: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """修改群聊信息（群名、群描述等）"""
        payload = {}
        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        return self._request("PUT", f"/im/v1/chats/{chat_id}", json=payload)

    def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """获取群聊信息"""
        return self._request("GET", f"/im/v1/chats/{chat_id}")

    def list_chat_members(self, chat_id: str, page_size: int = 50, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出群聊成员"""
        params = {"member_id_type": "open_id", "page_size": min(page_size, 50)}
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", f"/im/v1/chats/{chat_id}/members", params=params)

    def dissolve_chat(self, chat_id: str) -> Dict[str, Any]:
        """解散群聊"""
        return self._request("DELETE", f"/im/v1/chats/{chat_id}")

    # ─── 文档 ──────────────────────────────────────────────
    def create_document(self, title: str, content: str = "", folder_token: Optional[str] = None) -> Dict[str, Any]:
        """创建文档（用户身份）"""
        payload = {"title": title}
        if folder_token:
            payload["folder_token"] = folder_token
        result = self._request("POST", "/docx/v1/documents", use_user_token=True, json=payload)
        if content:
            doc_token = result["document"]["document_id"]
            self.update_document(doc_token, content)
        return result

    def update_document(self, doc_token: str, content: str) -> Dict[str, Any]:
        """更新文档（追加内容）"""
        blocks_data = self._request("GET", f"/docx/v1/documents/{doc_token}/blocks", use_user_token=True)
        items = blocks_data.get("items", [])
        if not items:
            raise Exception("文档为空，无法找到根 block")

        page_block_id = items[0].get("block_id")
        payload = {
            "children": [{
                "block_type": 2,
                "text": {"elements": [{"text_run": {"content": content}}]},
            }]
        }
        return self._request("POST", f"/docx/v1/documents/{doc_token}/blocks/{page_block_id}/children", use_user_token=True, json=payload)

    # ─── 文件上传 ──────────────────────────────────────────
    def upload_file(self, file_path: str, parent_node: str, file_name: Optional[str] = None) -> Dict[str, Any]:
        """上传文件到飞书云文档"""
        if not file_name:
            file_name = Path(file_path).name
        with open(file_path, "rb") as f:
            url = f"{self.base_url}/drive/v1/files/upload_all"
            headers = {"Authorization": f"Bearer {self.get_access_token()}"}
            response = requests.post(url, headers=headers, data={"parent_node": parent_node, "file_name": file_name}, files={"file": (file_name, f, "application/octet-stream")})
            result = response.json()
            if result.get("code") != 0:
                raise Exception(f"上传文件失败: {result.get('msg')}")
            return result.get("data", {})

    # ─── 日历 ──────────────────────────────────────────────
    def _parse_time(self, time_str: str) -> str:
        """将 'YYYY-MM-DD HH:MM' 或 'YYYY-MM-DD' 格式转为 Unix 时间戳字符串"""
        from datetime import datetime
        try:
            return str(int(datetime.strptime(time_str, "%Y-%m-%d %H:%M").timestamp()))
        except ValueError:
            return str(int(datetime.strptime(time_str, "%Y-%m-%d").timestamp()))

    def list_calendars(self) -> Dict[str, Any]:
        """列出用户的日历列表"""
        return self._request("GET", "/calendar/v4/calendars", use_user_token=True)

    def _resolve_calendar_id(self, calendar_id: str) -> str:
        """将 'primary' 解析为用户主日历的真实 calendar_id"""
        if calendar_id != "primary":
            return calendar_id
        data = self.list_calendars()
        for cal in data.get("calendar_list", []):
            if cal.get("type") == "primary":
                return cal["calendar_id"]
        raise Exception("未找到主日历，请使用 list-calendars 查看可用日历并指定 calendar_id")

    def list_calendar_events(self, calendar_id: str = "primary", start_time: Optional[str] = None, end_time: Optional[str] = None, page_size: int = 50, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出日历事件，支持时间范围过滤"""
        calendar_id = self._resolve_calendar_id(calendar_id)
        params = {"page_size": min(page_size, 50)}
        if start_time:
            params["start_time"] = self._parse_time(start_time)
        if end_time:
            params["end_time"] = self._parse_time(end_time)
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", f"/calendar/v4/calendars/{calendar_id}/events", use_user_token=True, params=params)

    def get_calendar_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """获取单个日历事件详情"""
        calendar_id = self._resolve_calendar_id(calendar_id)
        return self._request("GET", f"/calendar/v4/calendars/{calendar_id}/events/{event_id}", use_user_token=True)

    def create_calendar_event(self, summary: str, start_time: str, end_time: str, description: str = "", attendees: Optional[list] = None, calendar_id: str = "primary") -> Dict[str, Any]:
        """创建日历事件"""
        calendar_id = self._resolve_calendar_id(calendar_id)
        payload = {
            "summary": summary, "description": description,
            "start_time": {"timestamp": self._parse_time(start_time)},
            "end_time": {"timestamp": self._parse_time(end_time)},
        }
        if attendees:
            payload["attendees"] = [{"type": "user", "user_id": a} for a in attendees]
        return self._request("POST", f"/calendar/v4/calendars/{calendar_id}/events", use_user_token=True, json=payload)

    def update_calendar_event(self, calendar_id: str, event_id: str, summary: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """更新日历事件"""
        calendar_id = self._resolve_calendar_id(calendar_id)
        payload = {}
        if summary is not None:
            payload["summary"] = summary
        if description is not None:
            payload["description"] = description
        if start_time is not None:
            payload["start_time"] = {"timestamp": self._parse_time(start_time)}
        if end_time is not None:
            payload["end_time"] = {"timestamp": self._parse_time(end_time)}
        return self._request("PATCH", f"/calendar/v4/calendars/{calendar_id}/events/{event_id}", use_user_token=True, json=payload)

    def delete_calendar_event(self, calendar_id: str, event_id: str) -> Dict[str, Any]:
        """删除日历事件"""
        calendar_id = self._resolve_calendar_id(calendar_id)
        return self._request("DELETE", f"/calendar/v4/calendars/{calendar_id}/events/{event_id}", use_user_token=True)

    def _to_rfc3339(self, t: str, day_end: bool = False) -> str:
        """将 'YYYY-MM-DD HH:MM' 或 'YYYY-MM-DD' 转为 RFC 3339 格式
        day_end=True 时，纯日期自动补为 23:59:59"""
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=8))
        try:
            dt = datetime.strptime(t, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            return dt.isoformat()
        except ValueError:
            pass
        try:
            dt = datetime.strptime(t, "%Y-%m-%d").replace(tzinfo=tz)
            if day_end:
                dt = dt.replace(hour=23, minute=59, second=59)
            return dt.isoformat()
        except ValueError:
            pass
        return t  # 已经是 ISO 8601

    def _get_my_open_id(self) -> str:
        """获取当前用户的 open_id"""
        data = self._request("GET", "/authen/v1/user_info", use_user_token=True)
        return data.get("open_id", "")

    def query_freebusy(self, start_time: str, end_time: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """查询用户主日历忙闲信息
        start_time/end_time: 'YYYY-MM-DD HH:MM' 或 'YYYY-MM-DD' 或 ISO 8601
        user_id: open_id，不传则查询当前用户
        """
        if not user_id:
            user_id = self._get_my_open_id()
        payload = {
            "time_min": self._to_rfc3339(start_time),
            "time_max": self._to_rfc3339(end_time, day_end=True),
            "need_rsvp_status": True,
            "user_id": user_id,
        }
        return self._request("POST", "/calendar/v4/freebusy/list", use_user_token=True, json=payload, params={"user_id_type": "open_id"})

    def suggest_meeting_time(self, start_time: str, end_time: str, attendee_ids: List[str], duration_minutes: int = 30) -> List[Dict[str, str]]:
        """推荐多人共同空闲时段
        attendee_ids: open_id 列表
        duration_minutes: 会议时长（分钟）
        返回最多 5 个空闲时段 [{"start": "...", "end": "..."}]
        """
        from datetime import datetime, timedelta

        def parse_dt(s: str) -> datetime:
            return datetime.fromisoformat(s)

        range_start = parse_dt(self._to_rfc3339(start_time))
        range_end = parse_dt(self._to_rfc3339(end_time, day_end=True))

        # 收集所有人的忙碌时段（含自己）
        all_busy = []
        query_ids = attendee_ids + [None]  # None = 查自己
        for uid in query_ids:
            data = self.query_freebusy(start_time, end_time, uid)
            for item in data.get("freebusy_list", []):
                all_busy.append((parse_dt(item["start_time"]), parse_dt(item["end_time"])))

        # 合并重叠忙碌时段
        all_busy.sort()
        merged = []
        for s, e in all_busy:
            if merged and s <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))

        # 从忙碌间隙找空闲时段
        duration = timedelta(minutes=duration_minutes)
        suggestions = []
        cursor = range_start
        for busy_start, busy_end in merged:
            if busy_start - cursor >= duration:
                suggestions.append({"start": cursor.isoformat(), "end": (cursor + duration).isoformat()})
                if len(suggestions) >= 5:
                    break
            cursor = max(cursor, busy_end)
        if len(suggestions) < 5 and range_end - cursor >= duration:
            suggestions.append({"start": cursor.isoformat(), "end": (cursor + duration).isoformat()})

        return suggestions

    # ─── 任务管理 ────────────────────────────────────────────
    def create_task(self, summary: str, due: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """创建任务
        summary: 任务标题
        due: 截止时间，'YYYY-MM-DD HH:MM' 或 'YYYY-MM-DD'
        description: 任务描述
        """
        payload: Dict[str, Any] = {"summary": summary}
        if description:
            payload["description"] = description
        if due:
            from datetime import datetime, timezone, timedelta
            tz = timezone(timedelta(hours=8))
            try:
                dt = datetime.strptime(due, "%Y-%m-%d %H:%M").replace(tzinfo=tz)
            except ValueError:
                try:
                    dt = datetime.strptime(due, "%Y-%m-%d").replace(hour=23, minute=59, tzinfo=tz)
                except ValueError:
                    dt = datetime.fromisoformat(due)
            payload["due"] = {"timestamp": str(int(dt.timestamp())), "is_all_day": False}
        return self._request("POST", "/task/v2/tasks", use_user_token=True, json=payload)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """获取任务详情"""
        return self._request("GET", f"/task/v2/tasks/{task_id}", use_user_token=True)

    def list_tasks(self, page_size: int = 20, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出我的任务"""
        params: Dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", "/task/v2/tasks", use_user_token=True, params=params)

    def update_task(self, task_id: str, summary: Optional[str] = None, completed: bool = False, description: Optional[str] = None) -> Dict[str, Any]:
        """更新任务
        completed=True 时标记为已完成
        """
        payload: Dict[str, Any] = {}
        update_fields = []
        if summary:
            payload["summary"] = summary
            update_fields.append("summary")
        if description is not None:
            payload["description"] = description
            update_fields.append("description")
        if completed:
            payload["completed_at"] = str(int(time.time()))
            update_fields.append("completed_at")
        params = {"update_fields": ",".join(update_fields)} if update_fields else {}
        return self._request("PATCH", f"/task/v2/tasks/{task_id}", use_user_token=True, json=payload, params=params)

    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """标记任务为已完成（快捷方法）"""
        return self.update_task(task_id, completed=True)

    # ─── 电子表格 ────────────────────────────────────────────
    def create_sheet(self, title: str) -> Dict[str, Any]:
        """创建电子表格"""
        return self._request("POST", "/sheets/v3/spreadsheets", use_user_token=True, json={"title": title})

    def read_sheet(self, token: str, range_str: str) -> Dict[str, Any]:
        """读取电子表格数据
        token: spreadsheet token
        range_str: 范围，如 'Sheet1!A1:C10'
        """
        return self._request("GET", f"/sheets/v2/spreadsheets/{token}/values/{range_str}", use_user_token=True)

    def write_sheet(self, token: str, range_str: str, values: list) -> Dict[str, Any]:
        """写入电子表格数据
        values: 二维数组，如 [["a","b"],["c","d"]]
        """
        payload = {
            "valueRange": {
                "range": range_str,
                "values": values,
            }
        }
        return self._request("PUT", f"/sheets/v2/spreadsheets/{token}/values", use_user_token=True, json=payload)

    def append_sheet(self, token: str, range_str: str, values: list) -> Dict[str, Any]:
        """追加数据到电子表格
        values: 二维数组
        """
        payload = {
            "valueRange": {
                "range": range_str,
                "values": values,
            }
        }
        return self._request("POST", f"/sheets/v2/spreadsheets/{token}/values_append", use_user_token=True, json=payload)

    # ─── 通讯录 ────────────────────────────────────────────
    def get_user_info(self, email: str) -> Dict[str, Any]:
        """根据邮箱获取用户信息"""
        return self._request("POST", "/contact/v3/users/batch_get_id", params={"emails": email})

    def list_departments(self, parent_department_id: str = "0") -> Dict[str, Any]:
        """获取部门列表"""
        return self._request("GET", "/contact/v3/departments", params={"parent_department_id": parent_department_id, "fetch_child": True, "page_size": 50})

    def list_department_users(self, department_id: str) -> Dict[str, Any]:
        """获取部门成员列表"""
        return self._request("GET", "/contact/v3/users", params={"department_id": department_id, "page_size": 50})

    def get_user_by_id(self, user_id: str, user_id_type: str = "open_id") -> Dict[str, Any]:
        """根据 ID 获取用户详情"""
        return self._request("GET", f"/contact/v3/users/{user_id}", params={"user_id_type": user_id_type})

    def get_tenant_info(self) -> Dict[str, Any]:
        """获取企业信息"""
        return self._request("GET", "/tenant/v2/tenant/query")

    # ─── 知识库 ────────────────────────────────────────────
    def list_wiki_spaces(self, page_size: int = 50, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出知识库空间"""
        params = {"page_size": min(page_size, 50)}
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", "/wiki/v2/spaces", use_user_token=True, params=params)

    def list_wiki_nodes(self, space_id: str, parent_node_token: Optional[str] = None, page_size: int = 20, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出知识库节点"""
        params = {"page_size": min(page_size, 50)}
        if parent_node_token:
            params["parent_node_token"] = parent_node_token
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", f"/wiki/v2/spaces/{space_id}/nodes", use_user_token=True, params=params)

    def get_wiki_node(self, token: str) -> Dict[str, Any]:
        """获取知识库节点信息"""
        return self._request("GET", "/wiki/v2/spaces/get_node", use_user_token=True, params={"token": token})

    def read_wiki_node_content(self, node_token: str) -> Dict[str, Any]:
        """读取知识库文章纯文本"""
        node_info = self.get_wiki_node(node_token)
        node = node_info.get("node", {})
        obj_token = node.get("obj_token")
        obj_type = node.get("obj_type")
        title = node.get("title", "")

        if not obj_token:
            raise Exception(f"无法获取节点文档 token: {node_info}")

        if obj_type in ("doc", "docx"):
            content_data = self._request("GET", f"/docx/v1/documents/{obj_token}/raw_content", use_user_token=True)
            return {"title": title, "obj_type": obj_type, "obj_token": obj_token, "content": content_data.get("content", "")}
        else:
            return {"title": title, "obj_type": obj_type, "obj_token": obj_token, "content": f"[不支持直接读取的类型: {obj_type}，请在飞书中查看]"}

    # ─── 多维表格（Base/Bitable） ────────────────────────────
    def list_base_tables(self, app_token: str, page_size: int = 20, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出多维表格中的数据表"""
        params = {"page_size": min(page_size, 100)}
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables", use_user_token=True, params=params)

    def list_base_fields(self, app_token: str, table_id: str, page_size: int = 100, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出数据表的字段"""
        params = {"page_size": min(page_size, 100)}
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", use_user_token=True, params=params)

    def list_base_records(self, app_token: str, table_id: str, page_size: int = 20, page_token: Optional[str] = None, filter_str: Optional[str] = None, sort_str: Optional[str] = None) -> Dict[str, Any]:
        """列出数据表的记录"""
        params = {"page_size": min(page_size, 200)}
        if page_token:
            params["page_token"] = page_token
        if filter_str:
            params["filter"] = filter_str
        if sort_str:
            params["sort"] = sort_str
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", use_user_token=True, params=params)

    def get_base_record(self, app_token: str, table_id: str, record_id: str) -> Dict[str, Any]:
        """获取单条记录"""
        return self._request("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}", use_user_token=True)

    def create_base_record(self, app_token: str, table_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """创建记录"""
        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", use_user_token=True, json={"fields": fields})

    def batch_create_base_records(self, app_token: str, table_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量创建记录（最多500条）"""
        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create", use_user_token=True, json={"records": [{"fields": r} for r in records]})

    def update_base_record(self, app_token: str, table_id: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """更新记录"""
        return self._request("PUT", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}", use_user_token=True, json={"fields": fields})

    def delete_base_record(self, app_token: str, table_id: str, record_id: str) -> Dict[str, Any]:
        """删除记录"""
        return self._request("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}", use_user_token=True)

    def create_base_table(self, app_token: str, name: str, fields: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """创建数据表"""
        payload: Dict[str, Any] = {"table": {"name": name}}
        if fields:
            payload["table"]["fields"] = fields
        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables", use_user_token=True, json=payload)

    def create_base_field(self, app_token: str, table_id: str, field_name: str, field_type: int, property_obj: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建字段（field_type: 1=文本, 2=数字, 3=单选, 4=多选, 5=日期, 7=复选框, 11=人员, 13=手机号, 15=超链接, 17=附件, 20=公式, 21=双向关联, 22=地理位置, 23=群组, 1001=创建时间, 1002=修改时间, 1003=创建人, 1004=修改人, 1005=自动编号）"""
        payload: Dict[str, Any] = {"field_name": field_name, "type": field_type}
        if property_obj:
            payload["property"] = property_obj
        return self._request("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", use_user_token=True, json=payload)

    # ─── 邮箱（Mail） ────────────────────────────────────────
    def get_mail_profile(self) -> Dict[str, Any]:
        """获取当前用户邮箱地址"""
        return self._request("GET", "/mail/v1/user_mailboxes/me/profile", use_user_token=True)

    def list_mail_messages(self, folder_id: str = "INBOX", page_size: int = 20, page_token: Optional[str] = None) -> Dict[str, Any]:
        """列出邮件"""
        params = {"user_mailbox_id": "me", "page_size": min(page_size, 50), "folder_id": folder_id}
        if page_token:
            params["page_token"] = page_token
        return self._request("GET", "/mail/v1/user_mailboxes/me/messages", use_user_token=True, params=params)

    def get_mail_message(self, message_id: str) -> Dict[str, Any]:
        """读取单封邮件"""
        return self._request("GET", f"/mail/v1/user_mailboxes/me/messages/{message_id}", use_user_token=True)

    def search_mail(self, query: str, page_size: int = 20, page_token: Optional[str] = None) -> Dict[str, Any]:
        """搜索邮件"""
        params = {"page_size": min(page_size, 50)}
        if page_token:
            params["page_token"] = page_token
        return self._request("POST", "/mail/v1/user_mailboxes/me/messages/search", use_user_token=True, json={"query": query}, params=params)

    def send_mail(self, to: List[str], subject: str, body: str, cc: Optional[List[str]] = None, body_html: bool = True) -> Dict[str, Any]:
        """发送邮件（先创建草稿再发送）"""
        to_list = [{"mail_address": addr} for addr in to]
        cc_list = [{"mail_address": addr} for addr in (cc or [])]
        payload: Dict[str, Any] = {
            "subject": subject,
            "to": to_list,
            "body": {"content": body, "body_type": "text/html" if body_html else "text/plain"},
        }
        if cc_list:
            payload["cc"] = cc_list
        # 创建草稿
        draft = self._request("POST", "/mail/v1/user_mailboxes/me/drafts", use_user_token=True, json=payload)
        draft_id = draft.get("id") or draft.get("draft_id")
        if not draft_id:
            return {"status": "draft_created", "data": draft}
        # 发送草稿
        return self._request("POST", f"/mail/v1/user_mailboxes/me/drafts/{draft_id}/send", use_user_token=True)

    def create_mail_draft(self, to: List[str], subject: str, body: str, cc: Optional[List[str]] = None, body_html: bool = True) -> Dict[str, Any]:
        """创建邮件草稿（不发送）"""
        to_list = [{"mail_address": addr} for addr in to]
        cc_list = [{"mail_address": addr} for addr in (cc or [])]
        payload: Dict[str, Any] = {
            "subject": subject,
            "to": to_list,
            "body": {"content": body, "body_type": "text/html" if body_html else "text/plain"},
        }
        if cc_list:
            payload["cc"] = cc_list
        return self._request("POST", "/mail/v1/user_mailboxes/me/drafts", use_user_token=True, json=payload)


# ─── 配置加载 ──────────────────────────────────────────────
def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    if not CONFIG_PATH.exists():
        print("错误: 未找到 config.json")
        print(f"请先运行安装引导: {sys.executable} {SCRIPTS_DIR / 'setup.py'}")
        sys.exit(1)

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    if USER_TOKEN_PATH.exists():
        config["user_token_file"] = str(USER_TOKEN_PATH)

    return config


def create_client(config: Dict[str, Any]) -> FeishuClient:
    """根据配置创建客户端"""
    return FeishuClient(config["app_id"], config["app_secret"], config.get("user_token_file"))


# ─── 缓存刷新命令 ──────────────────────────────────────────
def cmd_refresh_contacts(client: FeishuClient):
    """刷新通讯录缓存"""
    data = client.list_department_users("0")
    items = data.get("items", [])

    contacts = []
    for u in items:
        contacts.append({
            "name": u.get("name", ""),
            "open_id": u.get("open_id", ""),
            "mobile": u.get("mobile", ""),
            "status": "已激活" if u.get("status", {}).get("is_activated") else "未激活",
        })

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONTACTS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=2, ensure_ascii=False)

    # 同步更新 config.json 的 team_members
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["team_members"] = {c["name"]: c["open_id"] for c in contacts if c["name"]}
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"通讯录已刷新，共 {len(contacts)} 人，保存到 {CONTACTS_CACHE_PATH}")
    for c in contacts:
        print(f"  {c['name']:12s} {c['mobile']:16s} {c['open_id']}")


def cmd_refresh_spaces(client: FeishuClient):
    """刷新知识库空间缓存"""
    all_spaces = []
    page_token = None

    while True:
        data = client.list_wiki_spaces(page_size=50, page_token=page_token)
        items = data.get("items", [])
        for s in items:
            all_spaces.append({
                "name": s.get("name", ""),
                "space_id": s.get("space_id", ""),
                "description": s.get("description", ""),
            })
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(SPACES_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(all_spaces, f, indent=2, ensure_ascii=False)

    print(f"知识库空间已刷新，共 {len(all_spaces)} 个，保存到 {SPACES_CACHE_PATH}")
    for s in all_spaces:
        print(f"  {s['name']:30s} {s['space_id']}")


def cmd_show_contacts():
    """显示缓存的通讯录"""
    if not CONTACTS_CACHE_PATH.exists():
        print("通讯录缓存不存在，请先运行: refresh-contacts")
        return

    contacts = json.loads(CONTACTS_CACHE_PATH.read_text(encoding="utf-8"))
    print(f"团队通讯录（共 {len(contacts)} 人）：\n")
    print(f"  {'序号':4s} {'姓名':12s} {'手机号':16s} {'状态':8s} {'open_id'}")
    print("  " + "-" * 80)
    for i, c in enumerate(contacts, 1):
        print(f"  {i:<4d} {c['name']:12s} {c['mobile']:16s} {c['status']:8s} {c['open_id']}")


def cmd_show_spaces():
    """显示缓存的知识库列表"""
    if not SPACES_CACHE_PATH.exists():
        print("知识库缓存不存在，请先运行: refresh-spaces")
        return

    spaces = json.loads(SPACES_CACHE_PATH.read_text(encoding="utf-8"))
    print(f"知识库空间（共 {len(spaces)} 个）：\n")
    for s in spaces:
        desc = f"（{s['description']}）" if s.get("description") else ""
        print(f"  {s['name']:30s} {s['space_id']}  {desc}")


def cmd_show_org(client: FeishuClient):
    """显示组织信息"""
    data = client.get_tenant_info()
    tenant = data.get("tenant", {})
    print("组织信息：")
    print(f"  名称: {tenant.get('name', '未知')}")
    print(f"  域名: {tenant.get('domain', '未知')}")
    print(f"  显示ID: {tenant.get('display_id', '未知')}")
    print(f"  租户Key: {tenant.get('tenant_key', '未知')}")


def cmd_check_config():
    """检查配置完整性"""
    print("检查配置...\n")
    issues = []

    # config.json
    if not CONFIG_PATH.exists():
        print(f"  ❌ config.json 不存在")
        print(f"     请运行: {sys.executable} {SCRIPTS_DIR / 'setup.py'}")
        return
    print(f"  ✅ config.json 存在")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    if not config.get("app_id") or config["app_id"] == "cli_xxx":
        issues.append("app_id 未配置")
    else:
        print(f"  ✅ app_id: {config['app_id']}")

    if not config.get("app_secret") or config["app_secret"] == "xxx":
        issues.append("app_secret 未配置")
    else:
        print(f"  ✅ app_secret: {'*' * 8}（已隐藏）")

    if config.get("default_chat_id"):
        print(f"  ✅ 默认群聊: {config['default_chat_id']}")
    else:
        print(f"  ⚠  默认群聊: 未设置（可选）")

    # token
    if USER_TOKEN_PATH.exists():
        token_data = json.loads(USER_TOKEN_PATH.read_text(encoding="utf-8"))
        token_time = token_data.get("_token_time", 0)
        refresh_expires = token_data.get("refresh_expires_in", 2592000)
        if time.time() > token_time + refresh_expires:
            issues.append("OAuth refresh_token 已过期，需要重新授权")
        else:
            remaining_days = int((token_time + refresh_expires - time.time()) / 86400)
            print(f"  ✅ OAuth 授权: 有效（还剩约 {remaining_days} 天）")
    else:
        issues.append("OAuth 授权未完成")

    # 缓存
    if CONTACTS_CACHE_PATH.exists():
        contacts = json.loads(CONTACTS_CACHE_PATH.read_text(encoding="utf-8"))
        print(f"  ✅ 通讯录缓存: {len(contacts)} 人")
    else:
        print(f"  ⚠  通讯录缓存: 不存在（运行 refresh-contacts 生成）")

    if SPACES_CACHE_PATH.exists():
        spaces = json.loads(SPACES_CACHE_PATH.read_text(encoding="utf-8"))
        print(f"  ✅ 知识库缓存: {len(spaces)} 个空间")
    else:
        print(f"  ⚠  知识库缓存: 不存在（运行 refresh-spaces 生成）")

    if issues:
        print(f"\n  ⚠ 发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"     - {issue}")
    else:
        print("\n  🎉 配置完整，一切就绪！")


# ─── CLI 入口 ──────────────────────────────────────────────
def main():
    ensure_utf8()

    parser = argparse.ArgumentParser(description="飞书助手 API 客户端")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # ── 管理命令 ──
    subparsers.add_parser("check-config", help="检查配置完整性")
    subparsers.add_parser("refresh-contacts", help="刷新通讯录缓存")
    subparsers.add_parser("refresh-spaces", help="刷新知识库空间缓存")
    subparsers.add_parser("show-contacts", help="显示通讯录")
    subparsers.add_parser("show-spaces", help="显示知识库列表")
    subparsers.add_parser("show-org", help="显示组织信息")

    # ── 发送消息 ──
    p = subparsers.add_parser("send-message", help="发送消息")
    p.add_argument("--type", required=True, choices=["text", "post", "interactive", "image"])
    p.add_argument("--content", required=True)
    p.add_argument("--receive_id", required=True)
    p.add_argument("--receive_id_type", default="open_id")

    # ── 群消息 ──
    p = subparsers.add_parser("get-chat-messages", help="获取群组消息")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--page_size", type=int, default=20)
    p.add_argument("--start_time", type=str)
    p.add_argument("--page_token", type=str)

    # ── 群聊管理 ──
    p = subparsers.add_parser("create-chat", help="创建群聊")
    p.add_argument("--name", required=True, help="群聊名称")
    p.add_argument("--members", required=True, help="成员 open_id，逗号分隔")
    p.add_argument("--description", default="")

    p = subparsers.add_parser("add-chat-members", help="向群聊添加成员")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--members", required=True, help="成员 open_id，逗号分隔")

    p = subparsers.add_parser("remove-chat-members", help="从群聊移除成员")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--members", required=True, help="成员 open_id，逗号分隔")

    p = subparsers.add_parser("get-chat-info", help="获取群聊信息")
    p.add_argument("--chat_id", required=True)

    p = subparsers.add_parser("update-chat", help="修改群聊信息")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--name", help="新群名")
    p.add_argument("--description", help="新群描述")

    p = subparsers.add_parser("list-chat-members", help="列出群聊成员")
    p.add_argument("--chat_id", required=True)
    p.add_argument("--page_size", type=int, default=50)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("dissolve-chat", help="解散群聊")
    p.add_argument("--chat_id", required=True)

    # ── 文档 ──
    p = subparsers.add_parser("create-doc", help="创建文档")
    p.add_argument("--title", required=True)
    p.add_argument("--content", default="")
    p.add_argument("--folder_token")

    p = subparsers.add_parser("update-doc", help="更新文档")
    p.add_argument("--doc_token", required=True)
    p.add_argument("--content", required=True)

    # ── 日历 ──
    subparsers.add_parser("list-calendars", help="列出日历列表")

    p = subparsers.add_parser("list-events", help="列出日历事件")
    p.add_argument("--calendar_id", default="primary")
    p.add_argument("--start_time", type=str, help="起始时间，格式 YYYY-MM-DD HH:MM")
    p.add_argument("--end_time", type=str, help="结束时间，格式 YYYY-MM-DD HH:MM")
    p.add_argument("--page_size", type=int, default=50)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("get-event", help="获取日历事件详情")
    p.add_argument("--calendar_id", default="primary")
    p.add_argument("--event_id", required=True)

    p = subparsers.add_parser("create-event", help="创建日历事件")
    p.add_argument("--summary", required=True)
    p.add_argument("--start_time", required=True, help="格式 YYYY-MM-DD HH:MM")
    p.add_argument("--end_time", required=True, help="格式 YYYY-MM-DD HH:MM")
    p.add_argument("--calendar_id", default="primary")
    p.add_argument("--description", default="")
    p.add_argument("--attendees", help="参会人 open_id，逗号分隔")

    p = subparsers.add_parser("update-event", help="更新日历事件")
    p.add_argument("--calendar_id", default="primary")
    p.add_argument("--event_id", required=True)
    p.add_argument("--summary", type=str)
    p.add_argument("--start_time", type=str, help="格式 YYYY-MM-DD HH:MM")
    p.add_argument("--end_time", type=str, help="格式 YYYY-MM-DD HH:MM")
    p.add_argument("--description", type=str)

    p = subparsers.add_parser("delete-event", help="删除日历事件")
    p.add_argument("--calendar_id", default="primary")
    p.add_argument("--event_id", required=True)

    p = subparsers.add_parser("query-freebusy", help="查询忙闲信息")
    p.add_argument("--start_time", required=True, help="起始时间，格式 YYYY-MM-DD HH:MM 或 YYYY-MM-DD")
    p.add_argument("--end_time", required=True, help="结束时间")
    p.add_argument("--user_id", type=str, help="目标用户 open_id（不传查自己）")

    p = subparsers.add_parser("suggest-meeting-time", help="推荐多人共同空闲时段")
    p.add_argument("--start_time", required=True, help="搜索区间开始")
    p.add_argument("--end_time", required=True, help="搜索区间结束")
    p.add_argument("--attendees", required=True, help="参会人 open_id，逗号分隔")
    p.add_argument("--duration", type=int, default=30, help="会议时长（分钟，默认30）")

    # ── 任务管理 ──
    p = subparsers.add_parser("create-task", help="创建任务")
    p.add_argument("--summary", required=True, help="任务标题")
    p.add_argument("--due", type=str, help="截止时间，格式 YYYY-MM-DD HH:MM 或 YYYY-MM-DD")
    p.add_argument("--description", type=str, help="任务描述")

    p = subparsers.add_parser("get-task", help="获取任务详情")
    p.add_argument("--task_id", required=True, help="任务 ID")

    p = subparsers.add_parser("list-tasks", help="列出我的任务")
    p.add_argument("--page_size", type=int, default=20, help="每页数量（默认20）")
    p.add_argument("--page_token", type=str, help="分页标记")

    p = subparsers.add_parser("update-task", help="更新任务")
    p.add_argument("--task_id", required=True, help="任务 ID")
    p.add_argument("--summary", type=str, help="新标题")
    p.add_argument("--description", type=str, help="新描述")
    p.add_argument("--completed", action="store_true", help="标记为已完成")

    p = subparsers.add_parser("complete-task", help="标记任务为已完成")
    p.add_argument("--task_id", required=True, help="任务 ID")

    # ── 电子表格 ──
    p = subparsers.add_parser("create-sheet", help="创建电子表格")
    p.add_argument("--title", required=True, help="表格标题")

    p = subparsers.add_parser("read-sheet", help="读取电子表格数据")
    p.add_argument("--token", required=True, help="spreadsheet token")
    p.add_argument("--range", required=True, help="范围，如 Sheet1!A1:C10")

    p = subparsers.add_parser("write-sheet", help="写入电子表格数据")
    p.add_argument("--token", required=True, help="spreadsheet token")
    p.add_argument("--range", required=True, help="起始范围，如 Sheet1!A1")
    p.add_argument("--values", required=True, help='二维数组 JSON，如 \'[["a","b"],["c","d"]]\'')

    p = subparsers.add_parser("append-sheet", help="追加数据到电子表格")
    p.add_argument("--token", required=True, help="spreadsheet token")
    p.add_argument("--range", required=True, help="目标工作表，如 Sheet1")
    p.add_argument("--values", required=True, help='二维数组 JSON，如 \'[["a","b"]]\'')

    # ── 文件上传 ──
    p = subparsers.add_parser("upload-file", help="上传文件")
    p.add_argument("--file_path", required=True)
    p.add_argument("--parent_node", required=True)
    p.add_argument("--file_name")

    # ── 用户 ──
    p = subparsers.add_parser("get-user", help="通过邮箱查用户")
    p.add_argument("--email", required=True)

    p = subparsers.add_parser("get-user-detail", help="通过 ID 查用户详情")
    p.add_argument("--user_id", required=True)
    p.add_argument("--user_id_type", default="open_id")

    p = subparsers.add_parser("list-departments", help="获取部门列表")
    p.add_argument("--parent_id", default="0")

    p = subparsers.add_parser("list-department-users", help="获取部门成员")
    p.add_argument("--department_id", required=True)

    p = subparsers.add_parser("get-tenant-info", help="获取企业信息")

    # ── 知识库 ──
    p = subparsers.add_parser("list-wiki-spaces", help="列出知识库空间")
    p.add_argument("--page_size", type=int, default=50)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("list-wiki-nodes", help="列出知识库文章")
    p.add_argument("--space_id", required=True)
    p.add_argument("--parent_node_token", type=str)
    p.add_argument("--page_size", type=int, default=20)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("read-wiki-node", help="读取知识库文章内容")
    p.add_argument("--node_token", required=True)

    # ── 多维表格 ──
    p = subparsers.add_parser("list-base-tables", help="列出多维表格中的数据表")
    p.add_argument("--app_token", required=True, help="多维表格 app_token")
    p.add_argument("--page_size", type=int, default=20)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("list-base-fields", help="列出数据表字段")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--page_size", type=int, default=100)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("list-base-records", help="列出数据表记录")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--page_size", type=int, default=20)
    p.add_argument("--page_token", type=str)
    p.add_argument("--filter", type=str, help="筛选条件")
    p.add_argument("--sort", type=str, help="排序条件")

    p = subparsers.add_parser("get-base-record", help="获取单条记录")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--record_id", required=True)

    p = subparsers.add_parser("create-base-record", help="创建记录")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--fields", required=True, help="JSON 格式的字段值")

    p = subparsers.add_parser("batch-create-base-records", help="批量创建记录")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--records", required=True, help="JSON 数组格式的记录列表")

    p = subparsers.add_parser("update-base-record", help="更新记录")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--record_id", required=True)
    p.add_argument("--fields", required=True, help="JSON 格式的字段值")

    p = subparsers.add_parser("delete-base-record", help="删除记录")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--record_id", required=True)

    p = subparsers.add_parser("create-base-table", help="创建数据表")
    p.add_argument("--app_token", required=True)
    p.add_argument("--name", required=True, help="数据表名称")
    p.add_argument("--fields", type=str, help="JSON 数组格式的字段定义")

    p = subparsers.add_parser("create-base-field", help="创建字段")
    p.add_argument("--app_token", required=True)
    p.add_argument("--table_id", required=True)
    p.add_argument("--field_name", required=True)
    p.add_argument("--field_type", required=True, type=int, help="字段类型（1=文本, 2=数字, 3=单选, 4=多选, 5=日期, 7=复选框, 11=人员, 15=超链接, 17=附件）")
    p.add_argument("--property", type=str, help="JSON 格式的字段属性")

    # ── 邮箱 ──
    subparsers.add_parser("mail-profile", help="获取当前用户邮箱地址")

    p = subparsers.add_parser("list-mail", help="列出邮件")
    p.add_argument("--folder", default="INBOX", help="文件夹: INBOX/SENT/DRAFT/TRASH")
    p.add_argument("--page_size", type=int, default=20)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("read-mail", help="读取单封邮件")
    p.add_argument("--message_id", required=True)

    p = subparsers.add_parser("search-mail", help="搜索邮件")
    p.add_argument("--query", required=True, help="搜索关键词")
    p.add_argument("--page_size", type=int, default=20)
    p.add_argument("--page_token", type=str)

    p = subparsers.add_parser("send-mail", help="发送邮件")
    p.add_argument("--to", required=True, help="收件人邮箱，逗号分隔")
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--cc", type=str, help="抄送，逗号分隔")
    p.add_argument("--plain_text", action="store_true", help="使用纯文本（默认 HTML）")

    p = subparsers.add_parser("draft-mail", help="创建邮件草稿（不发送）")
    p.add_argument("--to", required=True, help="收件人邮箱，逗号分隔")
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--cc", type=str, help="抄送，逗号分隔")
    p.add_argument("--plain_text", action="store_true", help="使用纯文本（默认 HTML）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 不需要 API 连接的命令
    if args.command == "check-config":
        cmd_check_config()
        return
    if args.command == "show-contacts":
        cmd_show_contacts()
        return
    if args.command == "show-spaces":
        cmd_show_spaces()
        return

    # 需要 API 连接的命令
    config = load_config()
    client = create_client(config)

    try:
        if args.command == "refresh-contacts":
            cmd_refresh_contacts(client)
        elif args.command == "refresh-spaces":
            cmd_refresh_spaces(client)
        elif args.command == "show-org":
            cmd_show_org(client)
        elif args.command == "send-message":
            result = client.send_message(args.receive_id, args.type, args.content, args.receive_id_type)
            print(f"消息发送成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-chat-messages":
            result = client.get_chat_messages(args.chat_id, args.page_size, getattr(args, "start_time", None), getattr(args, "page_token", None))
            print(f"群组消息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-doc":
            result = client.create_document(args.title, args.content, args.folder_token)
            print(f"文档创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "update-doc":
            result = client.update_document(args.doc_token, args.content)
            print(f"文档更新成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-event":
            attendees = args.attendees.split(",") if args.attendees else None
            result = client.create_calendar_event(args.summary, args.start_time, args.end_time, args.description, attendees, args.calendar_id)
            print(f"日历事件创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-calendars":
            result = client.list_calendars()
            print(f"日历列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-events":
            result = client.list_calendar_events(args.calendar_id, getattr(args, "start_time", None), getattr(args, "end_time", None), args.page_size, getattr(args, "page_token", None))
            print(f"日历事件: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-event":
            result = client.get_calendar_event(args.calendar_id, args.event_id)
            print(f"事件详情: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "update-event":
            result = client.update_calendar_event(args.calendar_id, args.event_id, args.summary, args.start_time, args.end_time, args.description)
            print(f"事件更新成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "delete-event":
            result = client.delete_calendar_event(args.calendar_id, args.event_id)
            print(f"事件删除成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "query-freebusy":
            result = client.query_freebusy(args.start_time, args.end_time, getattr(args, "user_id", None))
            print(f"忙闲信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "suggest-meeting-time":
            attendee_list = [a.strip() for a in args.attendees.split(",")]
            result = client.suggest_meeting_time(args.start_time, args.end_time, attendee_list, args.duration)
            print(f"推荐时段: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-task":
            result = client.create_task(args.summary, getattr(args, "due", None), getattr(args, "description", None))
            print(f"任务创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-task":
            result = client.get_task(args.task_id)
            print(f"任务详情: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-tasks":
            result = client.list_tasks(args.page_size, getattr(args, "page_token", None))
            print(f"任务列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "update-task":
            result = client.update_task(args.task_id, getattr(args, "summary", None), args.completed, getattr(args, "description", None))
            print(f"任务更新成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "complete-task":
            result = client.complete_task(args.task_id)
            print(f"任务已完成: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-sheet":
            result = client.create_sheet(args.title)
            print(f"表格创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "read-sheet":
            result = client.read_sheet(args.token, getattr(args, "range"))
            print(f"表格数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "write-sheet":
            values = json.loads(args.values)
            result = client.write_sheet(args.token, getattr(args, "range"), values)
            print(f"写入成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "append-sheet":
            values = json.loads(args.values)
            result = client.append_sheet(args.token, getattr(args, "range"), values)
            print(f"追加成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-chat":
            member_ids = args.members.split(",")
            result = client.create_chat(args.name, member_ids, args.description)
            print(f"群聊创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "add-chat-members":
            member_ids = args.members.split(",")
            result = client.add_chat_members(args.chat_id, member_ids)
            print(f"成员添加成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "remove-chat-members":
            member_ids = args.members.split(",")
            result = client.remove_chat_members(args.chat_id, member_ids)
            print(f"成员移除成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-chat-info":
            result = client.get_chat_info(args.chat_id)
            print(f"群聊信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "update-chat":
            result = client.update_chat(args.chat_id, name=args.name, description=args.description)
            print(f"群聊信息修改成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-chat-members":
            result = client.list_chat_members(args.chat_id, args.page_size, getattr(args, "page_token", None))
            print(f"群聊成员: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "dissolve-chat":
            result = client.dissolve_chat(args.chat_id)
            print(f"群聊已解散: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "upload-file":
            result = client.upload_file(args.file_path, args.parent_node, args.file_name)
            print(f"文件上传成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-user":
            result = client.get_user_info(args.email)
            print(f"用户信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-user-detail":
            result = client.get_user_by_id(args.user_id, args.user_id_type)
            print(f"用户详情: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-departments":
            result = client.list_departments(args.parent_id)
            print(f"部门列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-department-users":
            result = client.list_department_users(args.department_id)
            print(f"部门成员: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-tenant-info":
            result = client.get_tenant_info()
            print(f"企业信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-wiki-spaces":
            result = client.list_wiki_spaces(args.page_size, getattr(args, "page_token", None))
            print(f"知识库空间: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-wiki-nodes":
            result = client.list_wiki_nodes(args.space_id, getattr(args, "parent_node_token", None), args.page_size, getattr(args, "page_token", None))
            print(f"知识库节点: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "read-wiki-node":
            result = client.read_wiki_node_content(args.node_token)
            print(f"文章内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        # ── 多维表格 ──
        elif args.command == "list-base-tables":
            result = client.list_base_tables(args.app_token, args.page_size, getattr(args, "page_token", None))
            print(f"数据表列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-base-fields":
            result = client.list_base_fields(args.app_token, args.table_id, args.page_size, getattr(args, "page_token", None))
            print(f"字段列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-base-records":
            result = client.list_base_records(args.app_token, args.table_id, args.page_size, getattr(args, "page_token", None), getattr(args, "filter", None), getattr(args, "sort", None))
            print(f"记录列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "get-base-record":
            result = client.get_base_record(args.app_token, args.table_id, args.record_id)
            print(f"记录详情: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-base-record":
            fields = json.loads(args.fields)
            result = client.create_base_record(args.app_token, args.table_id, fields)
            print(f"记录创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "batch-create-base-records":
            records = json.loads(args.records)
            result = client.batch_create_base_records(args.app_token, args.table_id, records)
            print(f"批量创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "update-base-record":
            fields = json.loads(args.fields)
            result = client.update_base_record(args.app_token, args.table_id, args.record_id, fields)
            print(f"记录更新成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "delete-base-record":
            result = client.delete_base_record(args.app_token, args.table_id, args.record_id)
            print(f"记录删除成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-base-table":
            fields = json.loads(args.fields) if args.fields else None
            result = client.create_base_table(args.app_token, args.name, fields)
            print(f"数据表创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "create-base-field":
            prop = json.loads(args.property) if getattr(args, "property", None) else None
            result = client.create_base_field(args.app_token, args.table_id, args.field_name, args.field_type, prop)
            print(f"字段创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        # ── 邮箱 ──
        elif args.command == "mail-profile":
            result = client.get_mail_profile()
            print(f"邮箱信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "list-mail":
            result = client.list_mail_messages(args.folder, args.page_size, getattr(args, "page_token", None))
            print(f"邮件列表: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "read-mail":
            result = client.get_mail_message(args.message_id)
            print(f"邮件内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "search-mail":
            result = client.search_mail(args.query, args.page_size, getattr(args, "page_token", None))
            print(f"搜索结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "send-mail":
            to_list = [a.strip() for a in args.to.split(",")]
            cc_list = [a.strip() for a in args.cc.split(",")] if args.cc else None
            result = client.send_mail(to_list, args.subject, args.body, cc_list, not args.plain_text)
            print(f"邮件发送成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
        elif args.command == "draft-mail":
            to_list = [a.strip() for a in args.to.split(",")]
            cc_list = [a.strip() for a in args.cc.split(",")] if args.cc else None
            result = client.create_mail_draft(to_list, args.subject, args.body, cc_list, not args.plain_text)
            print(f"草稿创建成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
