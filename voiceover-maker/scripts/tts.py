#!/usr/bin/env python3
"""多 provider TTS：把文本变成 MP3 口播文件。

provider 路由：
- 默认 auto，按文本语种检测：中文 → MiniMax，英文 → ElevenLabs
- 也可以用 --provider 强制指定

用法：
    python tts.py "要朗读的文本"                          # auto 路由
    python tts.py "你好世界" --voice lyrical --emotion happy --speed 1.1
    python tts.py "Hello" --voice rachel
    python tts.py --file 长稿.txt                         # 自动按段落/句末分段
    python tts.py "文本" --dry-run                        # 只估算字符与价钱
    python tts.py "文本" -o -                             # 输出到 stdout（管道）
    python tts.py --list-voices                           # 列本地预设
    python tts.py --list-remote-voices [--filter Chinese] # 拉 MiniMax 全部音色
    python tts.py --usage                                 # 看本地累计用量
    python tts.py --clear-cache                           # 清缓存
    python tts.py --preview lyrical                       # 5s 试听
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
ASSETS_DIR = ROOT / "assets"
SILENCE_ASSET = ASSETS_DIR / "silence-300ms-32k-128k-mono.mp3"
CACHE_DIR = ROOT / "cache"
USAGE_LOG = ROOT / "usage.jsonl"

SILENCE_UNIT_MS = 300

# 文本上限（保守，留 buffer）
MINIMAX_TEXT_LIMIT = 9500       # 官方 10000
ELEVENLABS_TEXT_LIMIT = 4500    # ElevenLabs 推荐 < 5000

# 网络重试（5xx / URLError 触发；同 key 重试，不切 fallback）
NETWORK_RETRY_COUNT = 2
NETWORK_RETRY_BACKOFF = 2.0

# --preview 用的示例文本
PREVIEW_SAMPLES = {
    "minimax": "这是一段示例语音，你可以听听看音色、节奏和情绪表达。",
    "elevenlabs": "This is a sample preview to help you compare different voices.",
}


# ---------- 配置加载 ----------

def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(f"找不到配置文件：{CONFIG_PATH}")
    # utf-8-sig：兼容 Windows 记事本另存为时自动写入的 UTF-8 BOM
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        return json.load(f)


def merge_env_keys(cfg):
    """环境变量 > config.json。"""
    el = cfg.get("providers", {}).get("elevenlabs")
    if el and os.environ.get("ELEVENLABS_API_KEY"):
        el["api_key"] = os.environ["ELEVENLABS_API_KEY"]

    mm = cfg.get("providers", {}).get("minimax")
    if mm:
        if os.environ.get("MINIMAX_API_KEY"):
            mm["api_key"] = os.environ["MINIMAX_API_KEY"]
        if os.environ.get("MINIMAX_FALLBACK_API_KEY"):
            mm["fallback_keys"] = [os.environ["MINIMAX_FALLBACK_API_KEY"]] + mm.get("fallback_keys", [])


# ---------- 预检 ----------

def check_environment():
    """检查 config / 凭证 / 静默 asset / 网络可达性。不调真实合成 API。"""
    print("=== voiceover-maker 环境预检 ===\n")
    ok = True

    # Python 版本
    py = sys.version_info
    print(f"  Python：{py.major}.{py.minor}.{py.micro}")
    if py < (3, 6):
        print("  ✗ 需要 Python 3.6+")
        ok = False

    # config.json
    print(f"  config.json：{CONFIG_PATH}")
    if not CONFIG_PATH.exists():
        print("  ✗ 不存在。请把 config.json.template 复制为 config.json 后填入 API key")
        return False
    try:
        with open(CONFIG_PATH, encoding="utf-8-sig") as f:
            cfg = json.load(f)
        print("  ✓ 解析成功")
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON 解析失败：{e}")
        print("    （Windows 用记事本编辑过？JSON 格式可能被改坏了，建议用 VS Code 等编辑器重存）")
        return False

    merge_env_keys(cfg)

    # 静默 asset
    print(f"  静默 asset：{SILENCE_ASSET.name}")
    if SILENCE_ASSET.exists():
        print("  ✓ 存在")
    else:
        print("  ⚠ 缺失（长稿段间会用 0ms 间隔，不影响单段合成）")

    # ElevenLabs key
    el_key = cfg.get("providers", {}).get("elevenlabs", {}).get("api_key") or ""
    if el_key:
        masked = el_key[:8] + "..." if len(el_key) > 8 else "***"
        print(f"  ElevenLabs key：✓ 已配置（{masked}）")
    else:
        print("  ElevenLabs key：⚠ 未配置（英文配音将无法工作）")

    # MiniMax key
    mm = cfg.get("providers", {}).get("minimax", {})
    mm_key = mm.get("api_key") or ""
    fb_keys = mm.get("fallback_keys") or []
    if mm_key:
        masked = mm_key[:8] + "..." if len(mm_key) > 8 else "***"
        print(f"  MiniMax key：✓ 已配置（{masked}）")
        if fb_keys:
            print(f"  MiniMax fallback：✓ {len(fb_keys)} 个备用 key")
    else:
        print("  MiniMax key：⚠ 未配置（中文配音将无法工作）")

    if not el_key and not mm_key:
        print("\n  ✗ 至少需要配置一个 provider 的 api_key")
        ok = False

    # 网络可达性（不带凭证 GET endpoint，4xx/5xx 也算服务器有响应=网络通）
    print("\n  网络可达性：")
    for name, prov in cfg.get("providers", {}).items():
        endpoint = prov.get("endpoint") or ""
        if not endpoint:
            continue
        try:
            req = urllib.request.Request(endpoint, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                print(f"    {name}: ✓ {endpoint} (HTTP {resp.status})")
        except urllib.error.HTTPError as e:
            # 服务器响应了 4xx/5xx——只要不是 DNS/连接失败，就算网络通
            print(f"    {name}: ✓ {endpoint} (HTTP {e.code}，服务器响应正常)")
        except urllib.error.URLError as e:
            print(f"    {name}: ✗ {endpoint} - {e.reason}")
            ok = False
        except Exception as e:
            print(f"    {name}: ✗ {endpoint} - {e}")
            ok = False

    print()
    if ok:
        print("✅ 预检通过，skill 可以正常使用。")
    else:
        print("❌ 预检失败，请按上面提示修复后重试。")
    return ok


# ---------- 语种检测 ----------

def detect_language(text: str):
    """返回 (lang, cjk_ratio, mixed)。"""
    if not text:
        return "en", 0.0, False
    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    total_letters = sum(1 for ch in text if ch.isalpha() or "\u4e00" <= ch <= "\u9fff")
    if total_letters == 0:
        return "en", 0.0, False
    ratio = cjk_count / total_letters
    lang = "zh" if ratio >= 0.15 else "en"
    has_zh = cjk_count > 0
    has_en = (total_letters - cjk_count) > 0
    mixed = has_zh and has_en and 0.1 <= ratio <= 0.9
    return lang, ratio, mixed


# ---------- provider / voice 解析 ----------

def resolve_provider(cfg, args, text):
    if args.provider and args.provider != "auto":
        if args.provider not in cfg["providers"]:
            sys.exit(f"未知 provider：{args.provider}，可用：{list(cfg['providers'])}")
        return args.provider

    if args.voice:
        voice_lower = args.voice.lower()
        hits = []
        for name, prov in cfg["providers"].items():
            for vname in prov.get("voices", {}):
                if vname.lower() == voice_lower:
                    hits.append((name, vname))
        if len(hits) == 1:
            return hits[0][0]
        if len(hits) > 1:
            providers = ", ".join(p for p, _ in hits)
            sys.exit(f"音色名 '{args.voice}' 在多个 provider 都存在（{providers}），请加 --provider 明确指定")

    lang, _, _ = detect_language(text)
    routing = cfg.get("language_routing", {"zh": "minimax", "en": "elevenlabs"})
    return routing.get(lang, "elevenlabs")


def resolve_voice(provider_cfg, voice_arg):
    voices = provider_cfg.get("voices", {})
    if not voice_arg:
        voice_arg = provider_cfg.get("default_voice")
    if not voice_arg:
        sys.exit("provider 没配 default_voice，且 --voice 没指定")
    for vname, info in voices.items():
        if vname.lower() == voice_arg.lower():
            return info["voice_id"], vname
    return voice_arg, voice_arg


# ---------- 文本分段 ----------

def split_text(text: str, limit: int):
    """切成不超过 limit 字符的块，优先在段落 / 句末标点处切。"""
    if len(text) <= limit:
        return [text]

    chunks = []
    paragraphs = text.split("\n")
    buf = ""
    for para in paragraphs:
        if not para.strip():
            continue
        if len(para) > limit:
            for sentence in _split_by_sentence(para, limit):
                if len(buf) + len(sentence) + 1 > limit:
                    if buf:
                        chunks.append(buf.strip())
                    buf = sentence
                else:
                    buf += ("\n" if buf else "") + sentence
        else:
            if len(buf) + len(para) + 1 > limit:
                chunks.append(buf.strip())
                buf = para
            else:
                buf += ("\n" if buf else "") + para
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def _split_by_sentence(text, limit):
    parts = re.split(r"(?<=[。！？.!?])", text)
    out, buf = [], ""
    for p in parts:
        if not p:
            continue
        if len(p) > limit:
            if buf:
                out.append(buf)
                buf = ""
            for i in range(0, len(p), limit):
                out.append(p[i:i + limit])
        elif len(buf) + len(p) > limit:
            out.append(buf)
            buf = p
        else:
            buf += p
    if buf:
        out.append(buf)
    return out


# ---------- 网络层 ----------

def _do_http(req, timeout=180):
    """带重试的 HTTP 调用。返回 (status, body_bytes)。"""
    last_reason = None
    for attempt in range(NETWORK_RETRY_COUNT + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            if 500 <= e.code < 600 and attempt < NETWORK_RETRY_COUNT:
                wait = NETWORK_RETRY_BACKOFF * (2 ** attempt)
                print(f"  ⚠️ 服务端 {e.code}，{wait:.0f}s 后重试 ({attempt + 1}/{NETWORK_RETRY_COUNT})")
                time.sleep(wait)
                last_reason = f"HTTP {e.code}"
                continue
            return e.code, body
        except urllib.error.URLError as e:
            last_reason = str(e.reason)
            if attempt < NETWORK_RETRY_COUNT:
                wait = NETWORK_RETRY_BACKOFF * (2 ** attempt)
                print(f"  ⚠️ 网络异常 {e.reason}，{wait:.0f}s 后重试 ({attempt + 1}/{NETWORK_RETRY_COUNT})")
                time.sleep(wait)
                continue
            sys.exit(f"网络重试已耗尽：{e.reason}")
    sys.exit(f"重试已耗尽：{last_reason}")


# ---------- ElevenLabs ----------

def synthesize_elevenlabs(provider_cfg, text, voice_id, model_id):
    """返回 (audio_bytes, billed_chars, key_label)。"""
    url = f"{provider_cfg['endpoint']}/{voice_id}"
    voice_settings = provider_cfg.get(
        "voice_settings",
        {"stability": 0.6, "similarity_boost": 0.75, "style": 0.2},
    )
    payload = {"text": text, "model_id": model_id, "voice_settings": voice_settings}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "xi-api-key": provider_cfg["api_key"],
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    status, body = _do_http(req)
    if status != 200:
        body_text = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
        sys.exit(f"ElevenLabs API 错误 {status}：{body_text[:500]}")
    return body, len(text), "elevenlabs"


# ---------- MiniMax ----------

class MiniMaxFallbackError(Exception):
    pass


MINIMAX_FALLBACK_STATUS_CODES = {1004, 1008, 1029, 1039, 2013, 2049}
MINIMAX_FALLBACK_HTTP_CODES = {401, 402, 403, 429}


def _minimax_request_once(provider_cfg, text, voice_id, model_id, api_key, voice_settings_override):
    voice_setting = {
        "voice_id": voice_id,
        **provider_cfg.get("voice_settings", {}),
        **voice_settings_override,
    }
    payload = {
        "model": model_id,
        "text": text,
        "stream": False,
        "voice_setting": voice_setting,
        "audio_setting": provider_cfg.get(
            "audio_setting",
            {"sample_rate": 32000, "bitrate": 128000, "format": "mp3", "channel": 1},
        ),
    }
    req = urllib.request.Request(
        provider_cfg["endpoint"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    status, body = _do_http(req)
    if status != 200:
        body_text = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
        if status in MINIMAX_FALLBACK_HTTP_CODES:
            raise MiniMaxFallbackError(f"HTTP {status}: {body_text[:200]}")
        sys.exit(f"MiniMax API 错误 {status}：{body_text[:500]}")

    data = json.loads(body)
    base = data.get("base_resp", {})
    code = base.get("status_code")
    msg = base.get("status_msg", "")
    if code != 0:
        if code in MINIMAX_FALLBACK_STATUS_CODES:
            raise MiniMaxFallbackError(f"业务错误 {code}: {msg}")
        sys.exit(f"MiniMax 业务错误 {code}：{msg}")

    audio_hex = data.get("data", {}).get("audio")
    if not audio_hex:
        sys.exit(f"MiniMax 未返回音频数据：{data}")
    extra = data.get("extra_info", {})
    print(f"  audio_length={extra.get('audio_length')}ms format={extra.get('audio_format')} usage={extra.get('usage_characters')} 字符")
    return bytes.fromhex(audio_hex), extra.get("usage_characters", 0)


def synthesize_minimax(provider_cfg, text, voice_id, model_id, voice_settings_override):
    """返回 (audio_bytes, billed_chars, key_label)。"""
    keys = [provider_cfg["api_key"]] + provider_cfg.get("fallback_keys", [])
    last_err = None
    for i, key in enumerate(keys):
        label = "primary (Token Plan)" if i == 0 else f"fallback #{i} (按量付费)"
        if i > 0:
            print(f"  ⚠️ 切换到 {label}")
        try:
            audio, billed = _minimax_request_once(provider_cfg, text, voice_id, model_id, key, voice_settings_override)
            return audio, billed, label
        except MiniMaxFallbackError as e:
            last_err = e
            print(f"  {label} 失败：{e}")
            continue
    sys.exit(f"MiniMax 所有 key 都失败了。最后错误：{last_err}")


# ---------- 缓存（content-addressed） ----------

def cache_key(provider, voice_id, model_id, text, voice_settings, audio_setting):
    """所有影响输出的参数都进 hash。任一参数变 → key 变 → cache miss。"""
    payload = json.dumps({
        "provider": provider,
        "voice_id": voice_id,
        "model_id": model_id,
        "text": text,
        "voice_settings": voice_settings or {},
        "audio_setting": audio_setting or {},
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def cache_get(key: str):
    p = CACHE_DIR / f"{key}.mp3"
    return p.read_bytes() if p.exists() else None


def cache_put(key: str, audio_bytes: bytes, meta: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.mp3").write_bytes(audio_bytes)
    (CACHE_DIR / f"{key}.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def cache_clear():
    if not CACHE_DIR.exists():
        print("缓存目录不存在，无需清理")
        return
    count = 0
    total_bytes = 0
    for p in CACHE_DIR.iterdir():
        if p.is_file():
            total_bytes += p.stat().st_size
            p.unlink()
            count += 1
    print(f"已清理 {count} 个文件，共释放 {total_bytes / 1024:.1f} KB")


def cache_stats():
    if not CACHE_DIR.exists() or not any(CACHE_DIR.iterdir()):
        return 0, 0
    files = list(CACHE_DIR.glob("*.mp3"))
    total = sum(f.stat().st_size for f in files)
    return len(files), total


# ---------- 用量日志 ----------

def log_usage(provider, voice, input_chars, billed_chars, key_label):
    USAGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "provider": provider,
        "voice": voice,
        "input_chars": input_chars,
        "billed_chars": billed_chars,
        "key": key_label,
    }
    with open(USAGE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def usage_summary():
    if not USAGE_LOG.exists():
        print("还没有使用记录（usage.jsonl 不存在）")
        return
    now = datetime.now()
    today = now.date().isoformat()
    month = now.strftime("%Y-%m")

    def _new(): return {"calls": 0, "input": 0, "billed": 0}
    total = defaultdict(_new)
    today_t = defaultdict(_new)
    month_t = defaultdict(_new)
    by_key = defaultdict(_new)  # 按 key_label 分

    with open(USAGE_LOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            prov = e.get("provider", "?")
            ic = int(e.get("input_chars") or 0)
            bc = int(e.get("billed_chars") or 0)
            ts = e.get("ts", "")
            for bucket in (total[prov], by_key[e.get("key", "?")]):
                bucket["calls"] += 1
                bucket["input"] += ic
                bucket["billed"] += bc
            if ts.startswith(today):
                today_t[prov]["calls"] += 1
                today_t[prov]["input"] += ic
                today_t[prov]["billed"] += bc
            if ts[:7] == month:
                month_t[prov]["calls"] += 1
                month_t[prov]["input"] += ic
                month_t[prov]["billed"] += bc

    cache_n, cache_bytes = cache_stats()

    print("=== 使用统计 ===")
    print(f"\n今日 ({today}):")
    if today_t:
        for prov, t in sorted(today_t.items()):
            print(f"  {prov:<11}  {t['calls']:>3} 次  / 输入 {t['input']:>6} / 计费 {t['billed']:>6}")
    else:
        print("  （无）")

    print(f"\n本月 ({month}):")
    if month_t:
        for prov, t in sorted(month_t.items()):
            print(f"  {prov:<11}  {t['calls']:>3} 次  / 输入 {t['input']:>6} / 计费 {t['billed']:>6}")
    else:
        print("  （无）")

    print("\n累计:")
    for prov, t in sorted(total.items()):
        print(f"  {prov:<11}  {t['calls']:>3} 次  / 输入 {t['input']:>6} / 计费 {t['billed']:>6}")

    print("\n按 key 分:")
    for k, t in sorted(by_key.items()):
        print(f"  {k:<28} {t['calls']:>3} 次 / 计费 {t['billed']:>6}")

    print(f"\n缓存：{cache_n} 个文件 / {cache_bytes / 1024:.1f} KB")
    print(f"日志路径：{USAGE_LOG}")


# ---------- 远端音色列表 ----------

def list_remote_voices_minimax(provider_cfg, filter_str=None):
    endpoint = provider_cfg.get("get_voice_endpoint", "https://api.minimaxi.com/v1/get_voice")
    payload = {"voice_type": "all"}
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {provider_cfg['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    status, body = _do_http(req)
    body_text = body.decode("utf-8", errors="replace") if isinstance(body, (bytes, bytearray)) else str(body)
    if status != 200:
        sys.exit(f"MiniMax /get_voice 失败 {status}：{body_text[:500]}")

    data = json.loads(body_text)
    base = data.get("base_resp", {})
    if base.get("status_code", 0) != 0:
        sys.exit(f"MiniMax /get_voice 业务错误：{base}")

    sys_voices = data.get("system_voice", []) or []
    if filter_str:
        f = filter_str.lower()
        sys_voices = [
            v for v in sys_voices
            if f in json.dumps(v, ensure_ascii=False).lower()
        ]

    print(f"MiniMax 系统音色：{len(sys_voices)} 个" + (f"（filter='{filter_str}'）" if filter_str else ""))
    print()
    for v in sys_voices:
        # 字段名在不同版本可能不同；防御性提取
        vid = v.get("voice_id") or v.get("voice_name") or "?"
        name = v.get("voice_name") or ""
        desc = v.get("description")
        if isinstance(desc, list):
            desc = " | ".join(str(x) for x in desc)
        elif desc is None:
            desc = ""
        line = f"  {vid:<48}"
        if name and name != vid:
            line += f"  [{name}]"
        if desc:
            line += f"  {desc}"
        print(line)
    print(f"\n本地预设：{len(provider_cfg.get('voices', {}))} 个（要新增：复制 voice_id 加到 config.json 的 providers.minimax.voices）")


# ---------- list-voices（本地） ----------

def list_voices(cfg, only_provider=None):
    print("可用音色预设：")
    for prov_name, prov in cfg["providers"].items():
        if only_provider and prov_name != only_provider:
            continue
        default = prov.get("default_voice")
        print(f"\n[{prov_name}] (默认 model: {prov.get('default_model')})")
        for name, info in prov.get("voices", {}).items():
            marker = "  ← 默认" if name == default else ""
            print(f"  {name:<14} : {info['desc']}{marker}")
    print()
    print(f"语种路由：{cfg.get('language_routing', {})}")


# ---------- 计费估算 / dry-run ----------

def count_billable_chars(text: str, provider: str) -> int:
    """估算 provider 实际计费字符数。
    - MiniMax：1 个汉字按 2 字符算（实测），其它按 1 字符
    - ElevenLabs：按字符长度
    """
    if provider == "minimax":
        cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        return cjk * 2 + (len(text) - cjk)
    return len(text)


def estimate_cost(provider: str, billable: int) -> str:
    if provider == "minimax":
        cost = billable / 1000 * 0.20
        return f"¥{cost:.3f}（按量价；Token Plan 套餐内不另计价）"
    if provider == "elevenlabs":
        cost_usd = billable / 1000 * 0.30
        return f"${cost_usd:.3f} (≈ ¥{cost_usd * 7.2:.3f})"
    return "未知"


def dry_run_report(provider, text, chunks):
    billable_total = count_billable_chars(text, provider)
    print("=== Dry run（不调用 API）===")
    print(f"Provider：{provider}")
    print(f"文本字符：{len(text)}")
    print(f"估算计费字符：{billable_total}{'（CJK ×2 + 其它 ×1）' if provider == 'minimax' else ''}")
    print(f"分段数：{len(chunks)}")
    if len(chunks) > 1:
        print(f"  各段字符：{[len(c) for c in chunks]}")
    print(f"估算费用：{estimate_cost(provider, billable_total)}")
    print("（最终计费以 provider 返回的 usage 为准）")


# ---------- main ----------

def parse_voice_overrides(args):
    overrides = {}
    if args.emotion:
        overrides["emotion"] = args.emotion
    if args.speed is not None:
        overrides["speed"] = args.speed
    if args.pitch is not None:
        overrides["pitch"] = args.pitch
    if args.vol is not None:
        overrides["vol"] = args.vol
    return overrides


def synthesize_chunk_with_cache(provider_name, provider_cfg, text, voice_id, voice_label, model_id, overrides, use_cache):
    """单段合成（带缓存）。返回 audio_bytes。命中缓存时不会写 usage 日志。"""
    # 计算 cache key
    if provider_name == "minimax":
        effective_voice_settings = {**provider_cfg.get("voice_settings", {}), **overrides}
        audio_setting = provider_cfg.get("audio_setting", {})
    else:
        effective_voice_settings = provider_cfg.get("voice_settings", {})
        audio_setting = {}

    key = cache_key(provider_name, voice_id, model_id, text, effective_voice_settings, audio_setting)

    if use_cache:
        cached = cache_get(key)
        if cached is not None:
            print(f"  ✓ cache hit [{key}] {len(cached):,} bytes")
            return cached

    # miss → 调 API
    if provider_name == "elevenlabs":
        audio, billed, key_label = synthesize_elevenlabs(provider_cfg, text, voice_id, model_id)
    elif provider_name == "minimax":
        audio, billed, key_label = synthesize_minimax(provider_cfg, text, voice_id, model_id, overrides)
    else:
        sys.exit(f"未实现 provider：{provider_name}")

    # 写日志（仅真实调用）
    log_usage(provider_name, voice_label, len(text), billed, key_label)

    # 写缓存
    if use_cache:
        meta = {
            "provider": provider_name,
            "voice": voice_label,
            "voice_id": voice_id,
            "model": model_id,
            "input_chars": len(text),
            "billed_chars": billed,
            "settings": effective_voice_settings,
            "audio_setting": audio_setting,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "size_bytes": len(audio),
            "text_preview": text[:80],
        }
        cache_put(key, audio, meta)

    return audio


def main():
    parser = argparse.ArgumentParser(description="多 provider TTS → MP3（ElevenLabs / MiniMax）")
    parser.add_argument("text", nargs="?", help="要朗读的文本")
    parser.add_argument("--file", help="从文本文件读取（与位置参数二选一）")
    parser.add_argument("--voice", help="音色预设名（大小写不敏感）或原始 voice_id")
    parser.add_argument("--provider", choices=["auto", "elevenlabs", "minimax"],
                        default="auto", help="强制使用某个 provider，默认 auto")
    parser.add_argument("--model", help="模型 id，默认走 provider 配置")
    parser.add_argument("--output", "-o", help="输出 mp3 路径（'-' 输出到 stdout），默认 ~/Desktop")
    parser.add_argument("--dry-run", action="store_true", help="只估算字符数与价钱，不调 API")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的输出文件")
    # MiniMax voice setting 覆盖
    parser.add_argument("--emotion",
                        choices=["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"],
                        help="（仅 MiniMax）情绪")
    parser.add_argument("--speed", type=float, help="（仅 MiniMax）语速 0.5-2.0")
    parser.add_argument("--pitch", type=int, help="（仅 MiniMax）音调 -12~12")
    parser.add_argument("--vol", type=float, help="（仅 MiniMax）音量 0.5-2.0")
    parser.add_argument("--gap-ms", type=int, default=300,
                        help="长稿段间静默毫秒数（按 300ms 取整），默认 300。0 = 无间隔")
    parser.add_argument("--preview", help="试听某个音色：用预设示例文本生成 5s 样本到桌面")
    parser.add_argument("--no-cache", action="store_true",
                        help="不读不写缓存，强制调 API")
    # 子命令（互斥语义）
    parser.add_argument("--list-voices", nargs="?", const="__all__",
                        help="列本地预设。可选传 provider 名只列那一家")
    parser.add_argument("--list-remote-voices", action="store_true",
                        help="拉 MiniMax 系统音色全表（用 --filter 子串过滤）")
    parser.add_argument("--filter", help="（配合 --list-remote-voices）按子串过滤")
    parser.add_argument("--usage", action="store_true", help="显示本地累计用量统计")
    parser.add_argument("--clear-cache", action="store_true", help="清空缓存目录")
    parser.add_argument("--check", action="store_true",
                        help="预检环境/凭证/静默 asset/网络，不调真实合成 API")
    args = parser.parse_args()

    # --check 必须在 load_config() 之前——它要诊断 config 本身的问题
    if args.check:
        sys.exit(0 if check_environment() else 1)

    cfg = load_config()
    merge_env_keys(cfg)

    # 子命令短路
    if args.list_voices is not None:
        only = None if args.list_voices == "__all__" else args.list_voices
        list_voices(cfg, only)
        return
    if args.list_remote_voices:
        list_remote_voices_minimax(cfg["providers"]["minimax"], args.filter)
        return
    if args.usage:
        usage_summary()
        return
    if args.clear_cache:
        cache_clear()
        return

    # --preview：用预设示例文本试听音色
    if args.preview:
        preview_provider = None
        preview_vname = None
        for name, prov in cfg["providers"].items():
            for vname in prov.get("voices", {}):
                if vname.lower() == args.preview.lower():
                    preview_provider = name
                    preview_vname = vname
                    break
            if preview_provider:
                break
        if not preview_provider:
            sys.exit(f"未知音色预设：{args.preview}（用 --list-voices 查看）")
        args.text = PREVIEW_SAMPLES[preview_provider]
        args.voice = preview_vname
        args.provider = preview_provider
        args.force = True
        if not args.output:
            out_dir = Path(cfg.get("default_output_dir", "~/Desktop")).expanduser()
            args.output = str(out_dir / f"preview-{preview_provider}-{preview_vname}.mp3")
        print(f"🎧 试听模式：{preview_provider}/{preview_vname}")

    # 取文本
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8").strip()
    elif args.text:
        text = args.text
    else:
        parser.error("需要提供文本（位置参数）或 --file，或子命令 --usage/--list-voices/--list-remote-voices/--clear-cache")
    if not text:
        sys.exit("文本为空")

    # provider / voice / model
    provider_name = resolve_provider(cfg, args, text)
    provider_cfg = cfg["providers"][provider_name]
    voice_id, voice_label = resolve_voice(provider_cfg, args.voice)
    model_id = args.model or provider_cfg.get("default_model")

    # 语种检测 + 混合警告
    lang, ratio, mixed = detect_language(text)
    if mixed:
        print(f"⚠️ 检测到中英混合文本（中文占比 {ratio:.1%}），当前 provider={provider_name}。")
        print("   如果效果不理想，用 --provider 强制切换试试。")

    # 文本分段
    limit = MINIMAX_TEXT_LIMIT if provider_name == "minimax" else ELEVENLABS_TEXT_LIMIT
    chunks = split_text(text, limit)

    if args.dry_run:
        dry_run_report(provider_name, text, chunks)
        return

    # 输出路径
    if args.output == "-":
        out_path = None
    elif args.output:
        out_path = Path(args.output).expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = Path(cfg.get("default_output_dir", "~/Desktop")).expanduser()
        safe_label = "".join(c if c.isalnum() or c in "-_" else "_" for c in voice_label)
        out_path = out_dir / f"tts-{provider_name}-{safe_label}-{ts}.mp3"

    if out_path is not None:
        if out_path.exists() and not args.force:
            sys.exit(f"输出文件已存在：{out_path}（用 --force 覆盖）")
        out_path.parent.mkdir(parents=True, exist_ok=True)

    overrides = parse_voice_overrides(args)
    print(f"Provider：{provider_name}（语种：{lang}，中文占比 {ratio:.1%}）")
    print(f"音色：{voice_label} ({voice_id})")
    print(f"模型：{model_id}")
    print(f"文本长度：{len(text)} 字符；分 {len(chunks)} 段")
    if overrides and provider_name == "minimax":
        print(f"voice_setting 覆盖：{overrides}")
    elif overrides and provider_name != "minimax":
        print(f"⚠️ {provider_name} 不支持 emotion/speed/pitch/vol，已忽略")
    if args.no_cache:
        print("缓存：已禁用 (--no-cache)")

    # 准备段间静默
    silence_bytes = b""
    if len(chunks) > 1 and args.gap_ms > 0:
        if SILENCE_ASSET.exists():
            silence_repeat = max(1, round(args.gap_ms / SILENCE_UNIT_MS))
            silence_bytes = SILENCE_ASSET.read_bytes() * silence_repeat
            actual_ms = silence_repeat * SILENCE_UNIT_MS
            print(f"段间静默：{actual_ms}ms（{silence_repeat}× 300ms 单位）")
        else:
            print(f"⚠️ 找不到静默 asset {SILENCE_ASSET}，段间无间隔")

    # 合成（带缓存）
    use_cache = not args.no_cache
    audio_chunks = []
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            print(f"[段 {i + 1}/{len(chunks)}] {len(chunk)} 字符")
        audio = synthesize_chunk_with_cache(
            provider_name, provider_cfg, chunk, voice_id, voice_label,
            model_id, overrides, use_cache,
        )
        audio_chunks.append(audio)

    # 段间插静默
    if silence_bytes and len(audio_chunks) > 1:
        joined = []
        for idx, ac in enumerate(audio_chunks):
            joined.append(ac)
            if idx < len(audio_chunks) - 1:
                joined.append(silence_bytes)
        audio = b"".join(joined)
    else:
        audio = b"".join(audio_chunks)

    # 写出
    if out_path is None:
        sys.stdout.buffer.write(audio)
        print(f"完成：写入 stdout ({len(audio):,} bytes)", file=sys.stderr)
    else:
        out_path.write_bytes(audio)
        print(f"完成：{out_path} ({len(audio):,} bytes)")


if __name__ == "__main__":
    main()
