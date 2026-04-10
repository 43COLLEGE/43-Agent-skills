"""
Whisper 视频/音频逐字稿转录工具
使用 OpenAI Whisper 模型将视频/音频转为带时间戳的逐字稿

首次运行时自动创建 venv 并安装依赖，无需手动配置环境。

可选功能:
  --diarize     说话人识别 (需要 HuggingFace token，首次需授权 3 个模型)
  --punctuate   用 Claude API 为全文恢复标点 (需要 ANTHROPIC_API_KEY)
  --save-token  将 --hf-token 保存到本地配置，后续无需重复传入
  --check       预检环境和权限，不执行转录
"""

import sys
import os
import subprocess
import json

# ─── 自动 venv bootstrap（必须在其他 import 之前）────────────────────────────

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.join(SKILL_DIR, "venv")
CONFIG_FILE = os.path.join(SKILL_DIR, "config.json")

_CORE_PACKAGES = [
    "openai-whisper",
    "numpy<2.4",
    "numba",
    "anthropic",
]

_IS_WIN = sys.platform == "win32"
_BIN_DIR = "Scripts" if _IS_WIN else "bin"
_EXE = ".exe" if _IS_WIN else ""
_VENV_PYTHON = os.path.join(VENV_DIR, _BIN_DIR, f"python{_EXE}")
_VENV_PIP = os.path.join(VENV_DIR, _BIN_DIR, f"pip{_EXE}")


def _in_skill_venv() -> bool:
    return os.path.abspath(sys.prefix) == os.path.abspath(VENV_DIR)


def _bootstrap():
    if _in_skill_venv():
        return
    if not os.path.exists(_VENV_PYTHON):
        print("\n" + "="*50, flush=True)
        print("首次运行：正在初始化虚拟环境并安装依赖...", flush=True)
        print("这个过程可能需要几分钟，请耐心等待，不要关闭终端。", flush=True)
        print("="*50 + "\n", flush=True)
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
        print(f"安装核心依赖：{', '.join(_CORE_PACKAGES)}", flush=True)
        subprocess.run(
            [_VENV_PIP, "install", "--quiet"] + _CORE_PACKAGES,
            check=True,
        )
        print("依赖安装完成。\n", flush=True)
    if _IS_WIN:
        result = subprocess.run([_VENV_PYTHON] + sys.argv)
        sys.exit(result.returncode)
    else:
        os.execv(_VENV_PYTHON, [_VENV_PYTHON] + sys.argv)


_bootstrap()

# ─── 正式 import ──────────────────────────────────────────────────────────────

import time
import argparse

if _IS_WIN:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

MODELS_DIR = os.path.join(SKILL_DIR, "models")

SUPPORTED_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
SUPPORTED_AUDIO = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
SUPPORTED_FORMATS = SUPPORTED_VIDEO | SUPPORTED_AUDIO

PUNCTUATION_PROMPTS = {
    "zh": "以下是普通话的句子，包含标点符号。",
    "en": "The following is a sentence in English with proper punctuation.",
    "ja": "以下は句読点を含む日本語の文章です。",
}

# pyannote 说话人识别所需的 3 个 HuggingFace 模型（需分别授权）
PYANNOTE_REQUIRED_MODELS = [
    ("pyannote/speaker-diarization-3.1", "https://huggingface.co/pyannote/speaker-diarization-3.1"),
    ("pyannote/segmentation-3.0",        "https://huggingface.co/pyannote/segmentation-3.0"),
    ("pyannote/speaker-diarization-community-1", "https://huggingface.co/pyannote/speaker-diarization-community-1"),
]


# ─── 配置文件 ─────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict):
    existing = load_config()
    existing.update(data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"配置已保存到 {CONFIG_FILE}", flush=True)


# ─── 预检 ─────────────────────────────────────────────────────────────────────

def check_environment(hf_token: str = None):
    """预检环境，输出可操作的报告。"""
    import importlib
    ok = True
    print("=" * 50)
    print("环境预检")
    print("=" * 50)

    # ffmpeg
    try:
        r = subprocess.run(["ffprobe", "-version"], capture_output=True)
        print("✓ ffmpeg 已安装")
    except FileNotFoundError:
        print("✗ ffmpeg 未安装")
        if _IS_WIN:
            print("  → 请运行: winget install ffmpeg")
        else:
            print("  → 请运行: brew install ffmpeg")
        ok = False

    # whisper
    try:
        import whisper  # noqa: F401
        print("✓ openai-whisper 已安装")
    except ImportError:
        print("✗ openai-whisper 未安装（重新运行脚本会自动安装）")
        ok = False

    # Claude API
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        print("✓ ANTHROPIC_API_KEY 已设置（--punctuate 可用）")
    else:
        print("- ANTHROPIC_API_KEY 未设置（--punctuate 不可用）")
        print("  → 需要标点恢复时，设置环境变量 ANTHROPIC_API_KEY")

    # HuggingFace token
    cfg = load_config()
    token = hf_token or cfg.get("hf_token")
    if token:
        print(f"✓ HuggingFace token 已配置（--diarize 可尝试）")
        print("  检查模型授权状态...")
        _check_hf_model_access(token)
    else:
        print("- HuggingFace token 未配置（--diarize 不可用）")
        print("  → 需要说话人识别时，参考 SETUP.md 完成配置")

    print("=" * 50)
    return ok


def _check_hf_model_access(token: str):
    """逐一检查 pyannote 所需模型的访问权限。"""
    try:
        import requests
    except ImportError:
        subprocess.run([_VENV_PIP, "install", "--quiet", "requests"], check=True)
        import requests

    headers = {"Authorization": f"Bearer {token}"}
    all_ok = True
    for model_id, url in PYANNOTE_REQUIRED_MODELS:
        api_url = f"https://huggingface.co/api/models/{model_id}"
        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                print(f"  ✓ {model_id}")
            elif resp.status_code == 403:
                print(f"  ✗ {model_id} — 未授权")
                print(f"    → 请打开此链接接受协议: {url}")
                all_ok = False
            else:
                print(f"  ? {model_id} — 状态码 {resp.status_code}")
        except Exception as e:
            print(f"  ? {model_id} — 检查失败: {e}")
    if all_ok:
        print("  所有模型授权正常，说话人识别可用。")


# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def format_time(seconds: float) -> str:
    h, remainder = divmod(int(seconds), 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


def get_media_duration(filepath: str) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", filepath],
            capture_output=True,
        )
        data = json.loads(r.stdout.decode("utf-8", errors="replace"))
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


def filter_segments(segments: list, duration: float) -> list:
    if duration <= 0:
        return segments
    return [s for s in segments if s["start"] < duration + 1.0]


# ─── 说话人识别 ───────────────────────────────────────────────────────────────

def _ensure_pyannote():
    try:
        import pyannote.audio  # noqa: F401
    except ImportError:
        print("正在安装 pyannote-audio（首次使用，约 1-2 分钟）...", flush=True)
        subprocess.run([_VENV_PIP, "install", "--quiet", "pyannote-audio"], check=True)
        print("pyannote-audio 安装完成。", flush=True)


def diarize_audio(filepath: str, hf_token: str, num_speakers: int = None) -> list:
    """使用 pyannote 进行说话人分离，返回 [{start, end, speaker}] 列表。"""
    _ensure_pyannote()
    from pyannote.audio import Pipeline
    import torch

    # 预先提示所有需要的模型授权
    print("加载说话人识别模型...", flush=True)
    print("(首次加载需下载约 1GB 模型，请耐心等待)", flush=True)

    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=hf_token,
        )
    except Exception as e:
        err = str(e)
        if "403" in err or "gated" in err.lower() or "restricted" in err.lower():
            # 找出是哪个模型没被授权
            model_name = _extract_model_from_error(err)
            model_url = next(
                (url for mid, url in PYANNOTE_REQUIRED_MODELS if mid in err),
                "https://huggingface.co/pyannote/speaker-diarization-3.1"
            )
            raise PermissionError(
                f"\n说话人识别需要先授权 HuggingFace 模型。\n\n"
                f"请逐一打开以下链接，登录后点击 'Agree and access repository'：\n"
                + "\n".join(f"  {i+1}. {url}" for i, (_, url) in enumerate(PYANNOTE_REQUIRED_MODELS))
                + f"\n\n全部授权后重新运行即可。"
            )
        raise

    if torch.cuda.is_available():
        pipeline = pipeline.to(torch.device("cuda"))

    diar_kwargs = {}
    if num_speakers:
        diar_kwargs["num_speakers"] = num_speakers

    diarization = pipeline(filepath, **diar_kwargs)

    # 兼容 pyannote >= 4.x（返回 DiarizeOutput）和旧版（返回 Annotation）
    annotation = getattr(diarization, "speaker_diarization", diarization)
    return [
        {"start": turn.start, "end": turn.end, "speaker": speaker}
        for turn, _, speaker in annotation.itertracks(yield_label=True)
    ]


def _extract_model_from_error(err: str) -> str:
    for model_id, _ in PYANNOTE_REQUIRED_MODELS:
        if model_id in err:
            return model_id
    return "未知模型"


def assign_speakers(whisper_segments: list, diar_segments: list) -> list:
    result = []
    for seg in whisper_segments:
        best_speaker = "未知"
        best_overlap = 0.0
        for d in diar_segments:
            overlap = max(0.0, min(seg["end"], d["end"]) - max(seg["start"], d["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d["speaker"]
        result.append({**seg, "speaker": best_speaker})
    return result


def normalize_speaker_labels(segments: list) -> list:
    label_map = {}
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    idx = 0
    for seg in segments:
        raw = seg.get("speaker", "未知")
        if raw != "未知" and raw not in label_map:
            label_map[raw] = f"说话人{letters[idx % 26]}"
            idx += 1
    return [{**seg, "speaker": label_map.get(seg.get("speaker", "未知"), "未知")} for seg in segments]


# ─── 标点恢复 ─────────────────────────────────────────────────────────────────

def punctuate_with_claude(text: str, language: str = None) -> str:
    import anthropic
    lang_hint = {"zh": "文本为中文普通话。", "en": "The text is in English."}.get(language or "", "")
    prompt = (
        f"以下是语音转写的原始文本，缺乏标点符号。{lang_hint}"
        "请为其添加准确的标点，保持原文用词不变，只输出添加标点后的文本，不要任何解释或额外内容。\n\n"
        f"{text}"
    )
    print("调用 Claude API 恢复标点...", flush=True)
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ─── 文本构建与保存 ───────────────────────────────────────────────────────────

def build_full_text(segments: list, with_speakers: bool = False) -> str:
    parts = []
    current_speaker = None
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        speaker = seg.get("speaker") if with_speakers else None
        if with_speakers and speaker != current_speaker:
            if parts and "".join(parts).rstrip()[-1:] not in "。！？.!?\n":
                parts.append("。")
            parts.append(f"\n[{speaker}] ")
            current_speaker = speaker
        elif parts:
            last = "".join(parts).rstrip()
            if last and last[-1] not in "。！？，、；：…—,.!?;:\n":
                parts.append("，")
        parts.append(text)
    full = "".join(parts).strip()
    if full and full[-1] not in "。！？.!?":
        full += "。"
    return full


def save_transcript(
    segments: list,
    full_text: str,
    output_path: str,
    title: str,
    with_speakers: bool = False,
):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        prev_speaker = None
        for seg in segments:
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            text = seg["text"].strip()
            if not text:
                continue
            if with_speakers:
                speaker = seg.get("speaker", "未知")
                if speaker != prev_speaker:
                    f.write(f"\n**[{speaker}]**\n")
                    prev_speaker = speaker
                f.write(f"[{start} - {end}] {text}\n")
            else:
                f.write(f"[{start} - {end}] {text}\n")
        f.write(f"\n---\n\n# 完整文本\n\n{full_text}\n")


# ─── 核心转录逻辑 ─────────────────────────────────────────────────────────────

def transcribe_file(
    filepath: str,
    model_name: str = "turbo",
    language: str = None,
    output_dir: str = None,
    overwrite: bool = False,
    diarize: bool = False,
    hf_token: str = None,
    num_speakers: int = None,
    punctuate: bool = False,
    _model=None,
) -> str:
    import whisper

    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise ValueError(f"不支持的格式 {ext}")

    basename = os.path.splitext(os.path.basename(filepath))[0]
    out_dir = output_dir or os.path.dirname(filepath)
    out_path = os.path.join(out_dir, f"{basename}_逐字稿.txt")

    if os.path.exists(out_path) and os.path.getsize(out_path) > 0 and not overwrite:
        print(f"SKIP (已存在): {basename}")
        return out_path

    print(f"转录中: {basename[:70]}...", flush=True)

    model = _model
    if model is None:
        model_path = os.path.join(MODELS_DIR, f"{model_name}.pt")
        if not os.path.exists(model_path):
            model_sizes = {"turbo": "1.5GB", "medium": "1.4GB", "small": "461MB", "base": "139MB"}
            size = model_sizes.get(model_name, "未知大小")
            print(f"\n{'='*50}", flush=True)
            print(f"首次使用：需要下载 Whisper {model_name} 模型（{size}）", flush=True)
            print(f"下载过程中终端可能长时间没有新输出，这是正常现象，请耐心等待。", flush=True)
            print(f"模型下载后保存在本地，以后不会重复下载。", flush=True)
            print(f"{'='*50}\n", flush=True)
        else:
            print(f"加载模型 {model_name}...", flush=True)
        model = whisper.load_model(model_name, download_root=MODELS_DIR)

    duration = get_media_duration(filepath)

    t0 = time.time()
    kwargs = {
        "verbose": False,
        "condition_on_previous_text": False,
        "no_speech_threshold": 0.5,
    }
    if language:
        kwargs["language"] = language
        if language in PUNCTUATION_PROMPTS:
            kwargs["initial_prompt"] = PUNCTUATION_PROMPTS[language]

    result = model.transcribe(filepath, **kwargs)
    elapsed = time.time() - t0

    segments = filter_segments(result["segments"], duration)

    with_speakers = False
    if diarize:
        if not hf_token:
            print("  警告: --diarize 需要 --hf-token 或已保存的 token，跳过说话人识别")
            print("  提示: 运行 --save-token 保存 token，或参考 SETUP.md 配置")
        else:
            try:
                diar_segs = diarize_audio(filepath, hf_token, num_speakers)
                segments = assign_speakers(segments, diar_segs)
                segments = normalize_speaker_labels(segments)
                with_speakers = True
                speakers = set(s["speaker"] for s in segments)
                print(f"  说话人识别完成，检测到 {len(speakers)} 位说话人", flush=True)
            except PermissionError as e:
                print(f"\n{e}")
                print("  跳过说话人识别，继续生成普通逐字稿。")
            except Exception as e:
                print(f"  说话人识别失败: {e}")

    full_text = build_full_text(segments, with_speakers=with_speakers)

    if punctuate:
        try:
            full_text = punctuate_with_claude(full_text, language=language)
        except Exception as e:
            print(f"  标点恢复失败: {e}，使用原始文本")

    os.makedirs(out_dir, exist_ok=True)
    save_transcript(segments, full_text, out_path, basename, with_speakers=with_speakers)
    print(f"  完成 ({elapsed:.0f}s, {len(full_text)} 字) -> {os.path.basename(out_path)}", flush=True)
    return out_path


def transcribe_folder(
    folder: str,
    model_name: str = "turbo",
    language: str = None,
    output_dir: str = None,
    overwrite: bool = False,
    diarize: bool = False,
    hf_token: str = None,
    num_speakers: int = None,
    punctuate: bool = False,
) -> list:
    import whisper

    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        raise NotADirectoryError(f"目录不存在: {folder}")

    files = sorted(
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in SUPPORTED_FORMATS
    )
    if not files:
        print(f"目录中没有找到支持的媒体文件: {folder}")
        return []

    print(f"找到 {len(files)} 个媒体文件，加载模型 {model_name}...", flush=True)
    model = whisper.load_model(model_name, download_root=MODELS_DIR)
    print("模型加载完成", flush=True)

    results = []
    for i, fname in enumerate(files, 1):
        filepath = os.path.join(folder, fname)
        print(f"\n[{i}/{len(files)}] ", end="")
        try:
            out = transcribe_file(
                filepath,
                model_name=model_name,
                language=language,
                output_dir=output_dir,
                overwrite=overwrite,
                diarize=diarize,
                hf_token=hf_token,
                num_speakers=num_speakers,
                punctuate=punctuate,
                _model=model,
            )
            results.append(out)
        except Exception as e:
            print(f"  错误: {e}")

    print(f"\n全部完成！共转录 {len(results)}/{len(files)} 个文件")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Whisper 视频/音频逐字稿转录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础转录
  python3 scripts/transcribe.py video.mp4 --language zh

  # 首次保存 HuggingFace token（之后无需重复传入）
  python3 scripts/transcribe.py video.mp4 --hf-token hf_xxx --save-token

  # 说话人识别 + 标点恢复（token 已保存时无需 --hf-token）
  python3 scripts/transcribe.py video.mp4 --language zh --diarize --punctuate

  # 预检环境和权限
  python3 scripts/transcribe.py --check
        """,
    )
    parser.add_argument("path", nargs="?", help="视频/音频文件或目录路径（--check 时可省略）")
    parser.add_argument("--model", default="turbo", help="Whisper 模型 (默认: turbo)")
    parser.add_argument("--language", default=None, help="语言代码，如 zh/en (默认: 自动检测)")
    parser.add_argument("--output", default=None, help="输出目录 (默认: 与源文件同目录)")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已有逐字稿")
    parser.add_argument("--diarize", action="store_true", help="启用说话人识别")
    parser.add_argument("--hf-token", default=None, help="HuggingFace Access Token")
    parser.add_argument("--save-token", action="store_true", help="将 --hf-token 保存到本地配置")
    parser.add_argument("--speakers", type=int, default=None, help="预期说话人数量 (可选)")
    parser.add_argument("--punctuate", action="store_true", help="用 Claude API 补充标点")
    parser.add_argument("--check", action="store_true", help="预检环境和权限，不执行转录")
    args = parser.parse_args()

    # 读取已保存的 token，命令行传入的优先
    cfg = load_config()
    hf_token = args.hf_token or cfg.get("hf_token")

    # 保存 token
    if args.save_token:
        if not args.hf_token:
            print("错误: --save-token 需要同时传入 --hf-token")
            sys.exit(1)
        save_config({"hf_token": args.hf_token})
        print("Token 已保存，后续使用 --diarize 时无需再传 --hf-token")
        if not args.path:
            return

    # 预检模式
    if args.check:
        check_environment(hf_token=hf_token)
        return

    if not args.path:
        parser.print_help()
        sys.exit(1)

    path = os.path.abspath(args.path)
    common_kwargs = dict(
        model_name=args.model,
        language=args.language,
        output_dir=args.output,
        overwrite=args.overwrite,
        diarize=args.diarize,
        hf_token=hf_token,
        num_speakers=args.speakers,
        punctuate=args.punctuate,
    )

    if os.path.isdir(path):
        transcribe_folder(path, **common_kwargs)
    elif os.path.isfile(path):
        transcribe_file(path, **common_kwargs)
    else:
        print(f"路径不存在: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
