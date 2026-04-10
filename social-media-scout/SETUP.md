# Social Media Scout — 首次配置引导

**本文件仅在首次使用时由 AI 读取。配置完成后不再加载。**

## AI 执行流程

### 第 1 步：自动创建配置文件

```bash
cd ~/.claude/skills/social-media-scout/scripts && cp config.json.template config.json
```

Windows：
```cmd
cd %USERPROFILE%\.claude\skills\social-media-scout\scripts && copy config.json.template config.json
```

### 第 2 步：引导用户获取 API Key

用自然语言告诉用户（直接说，不要让用户去读文档）：

> "要使用社交媒体查询功能，需要一个 TikHub API Key。只需要做一次：
>
> 1. 打开 https://user.tikhub.io ，注册账号并登录
> 2. 点击左侧菜单「API 设置」→「API 密钥」
> 3. 点击右上角红色按钮「+ 创建 API 密钥」
> 4. 给密钥起个名字（比如 Claude Code），确认创建
> 5. 点击密钥旁边的复制图标，把密钥发给我
>
> 注册后有少量免费额度可供测试，正式使用需要充值。"

### 第 3 步：自动写入 API Key

用户提供密钥后，AI 自动执行（不需要用户做任何事）：

```python
import json, os
config_path = os.path.expanduser("~/.claude/skills/social-media-scout/scripts/config.json")
with open(config_path) as f:
    config = json.load(f)
config["api_key"] = "用户提供的密钥"
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)
print("API Key 已写入")
```

Windows 路径替换为：`os.path.join(os.environ["USERPROFILE"], ".claude", "skills", "social-media-scout", "scripts", "config.json")`

### 第 4 步：自动验证

```bash
cd ~/.claude/skills/social-media-scout
python3 scripts/tikhub_client.py rest-call douyin_web_fetch_hot_search_result --args '{}'
```

Windows：
```cmd
cd %USERPROFILE%\.claude\skills\social-media-scout
python scripts\tikhub_client.py rest-call douyin_web_fetch_hot_search_result --args "{}"
```

根据结果：
- **返回正常数据** → 告诉用户"配置成功！"，然后继续执行用户的原始需求
- **返回 401** → API Key 有误，请用户检查后重新发送
- **连接失败** → 网络问题，提示检查网络
