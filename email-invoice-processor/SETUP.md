# 首次配置指南

这份指南写给完全不懂技术的人。配置一次，之后每次处理发票只需告诉 AI 日期就行。

---

## 你能用这个工具做什么

- 自动从邮箱里找出所有发票邮件
- 下载 PDF/图片附件（包括邮件正文里的链接、二维码发票）
- 提取发票上的关键信息（金额、购买方、销售方等）
- 按购买方分类生成 Excel 汇总表

---

## 第一步：安装 Python 依赖

让 AI 运行以下命令：

**Mac / Linux：**
```bash
pip install pdfplumber openpyxl requests Pillow
```

**Windows：**
```cmd
python -m pip install pdfplumber openpyxl requests Pillow
```

可选（增强功能）：
```bash
pip install playwright && playwright install chromium
pip install pyzbar
```

---

## 第二步：开通邮箱 IMAP 并获取授权码

### QQ 邮箱（默认）

1. 登录网页版 QQ 邮箱：https://mail.qq.com
2. 点击左上角 **设置** → **账户**
3. 往下滚动找到 **POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务**
4. 开启 **IMAP/SMTP 服务**（如果已开启则跳过）
5. 按提示用手机发短信验证
6. 验证通过后，页面会显示一个 **授权码**（16 位字母，如 `abcdefghijklmnop`）
7. **复制并保存这个授权码**，它就是你的邮箱密码（不是 QQ 密码）

> 授权码只显示一次。如果忘记了，可以重新生成一个新的。

### 163 邮箱

1. 登录网页版 163 邮箱：https://mail.163.com
2. 点击 **设置** → **POP3/SMTP/IMAP**
3. 开启 **IMAP/SMTP 服务**
4. 按提示设置客户端授权密码
5. 记住这个授权密码

### Gmail

1. 登录 Google 账号：https://myaccount.google.com
2. 搜索 **App passwords**（需要先开启两步验证）
3. 生成一个 App Password
4. 记住这个密码

---

## 第三步：创建配置文件

把授权码告诉 AI，AI 会自动完成以下操作：

**1. 复制模板：**
```bash
cp ${CLAUDE_SKILL_DIR}/config.json.template ${CLAUDE_SKILL_DIR}/config.json
```

**2. 写入你的邮箱和授权码：**

AI 会用 Python 自动写入：
```python
import json
config = {
    "email": "你的邮箱地址",
    "password": "你的授权码",
    "imap_server": "imap.qq.com",
    "imap_port": 993
}
with open("${CLAUDE_SKILL_DIR}/config.json", "w") as f:
    json.dump(config, f, indent=2)
```

> 如果不是 QQ 邮箱，AI 会自动根据你的邮箱类型设置对应的 imap_server。

---

## 第四步：验证配置

让 AI 运行一次测试，随便选一个近期日期：

**Mac / Linux：**
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/process_invoices.py 2026-04
```

**Windows：**
```cmd
python ${CLAUDE_SKILL_DIR}\scripts\process_invoices.py 2026-04
```

如果看到"连接成功"就说明配置正确。如果报错，AI 会根据错误信息帮你排查。

---

## 配置完成后，日常怎么用

直接告诉 AI：

> "帮我处理三月份的发票"
> "把上个月邮箱里的发票整理成 Excel"
> "提取 3月1号到15号的发票，输出到桌面"

AI 会自动调用这个工具，你不需要知道任何命令行的事情。

---

## 常见问题

**授权码和 QQ 密码有什么区别？**

授权码是专门给第三方客户端用的独立密码，不是你的 QQ 登录密码。即使授权码泄露，别人也无法登录你的 QQ 账号。你可以随时在邮箱设置里撤销授权码。

**我有多个邮箱的发票怎么办？**

目前一次只能配置一个邮箱。如果需要处理多个邮箱，可以修改 config.json 切换。

**处理一个月的发票需要多长时间？**

取决于发票数量。通常 10-30 封发票邮件在 1-3 分钟内完成。如果有需要浏览器下载的链接，会稍慢一些。

**发票字段提取不完整？**

部分非标准格式的发票（如手写发票扫描件、特殊排版）可能字段识别不全。提取结果会在 Excel 备注列标注，你可以手动补充。
