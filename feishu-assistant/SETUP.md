# 飞书助手 — 首次配置引导

**本文件仅在首次使用时由 AI 读取。配置完成后不再加载。**

## AI 执行流程

### 第 1 步：检测 Python

```bash
python3 --version 2>/dev/null || python --version 2>/dev/null
```

确定可用的 Python 命令（macOS/Linux 通常是 `python3`，Windows 是 `python`）。

### 第 2 步：引导用户运行安装脚本

用自然语言告诉用户（直接说，不要让用户去读文档）：

> "飞书助手需要做一次初始配置，大约 3-5 分钟。请打开终端，粘贴运行这条命令：
>
> ```
> cd ~/.claude/skills/feishu-assistant && python3 scripts/setup.py
> ```
>
> （Windows 用户请运行：`cd %USERPROFILE%\.claude\skills\feishu-assistant && python scripts\setup.py`）
>
> 按照终端里的提示操作就行，只需要点 2 个链接。完成后告诉我。"

### 第 3 步：处理常见问题

如果用户反馈 setup.py 报错：

- **"npm not found"** → 告诉用户：没关系，setup.py 会自动切换到手动配置模式，按终端提示一步步操作即可，最终效果完全一样。
- **其他报错** → 让用户把报错信息发过来，帮助诊断。也可以让用户重新运行 `python3 scripts/setup.py`，脚本会从断点继续。

### 第 4 步：验证配置

用户说完成后，AI 自动检查：

```bash
cd ~/.claude/skills/feishu-assistant
cat scripts/config.json
```

Windows：
```cmd
cd %USERPROFILE%\.claude\skills\feishu-assistant
type scripts\config.json
```

验证 `app_id` 字段非空即为配置成功。告诉用户"配置完成！"，然后继续执行用户的原始需求。
