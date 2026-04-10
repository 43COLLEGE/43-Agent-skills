# email-invoice-processor

从邮箱自动提取发票，下载附件，识别字段，生成 Excel 汇总。

> 43 COLLEGE 凯寓 (KAIYU) 出品

---

## 能力

| 能力 | 说明 |
|------|------|
| 邮件筛选 | IMAP 服务端搜索，按关键词+日期精准定位发票邮件 |
| 三级下载 | 直接附件 → 正文链接 → Playwright 浏览器兜底 |
| 二维码处理 | 自动解码二维码图片 → 访问链接 → 下载 PDF |
| 字段提取 | pdfplumber 表格 + 正则双策略，适配数电发票 |
| Excel 汇总 | 按购买方分 sheet，自动合计金额 |
| 多邮箱兼容 | 支持 QQ、163、Gmail、Outlook 等 IMAP 邮箱 |

## 安装

**方式一：让 Claude 自动安装**

```
帮我安装这个 skill：https://github.com/43COLLEGE/43-Agent-skills（email-invoice-processor 目录）
```

**方式二：手动**

```bash
git clone https://github.com/43COLLEGE/43-Agent-skills /tmp/43-skills
cp -r /tmp/43-skills/email-invoice-processor ~/.claude/skills/email-invoice-processor
rm -rf /tmp/43-skills
```

## 前置条件

- **Python 3**
- **邮箱 IMAP 授权码**（QQ 邮箱需在设置里开启 IMAP 并生成授权码）
- 必需依赖：`pip install pdfplumber openpyxl requests Pillow`

详细配置步骤见 [SETUP.md](./SETUP.md)。

## 使用

安装配置后，直接用自然语言：

- "帮我处理上个月的发票"
- "整理 3 月份邮箱里的发票，生成 Excel"
- "提取 2026-03-01 到 2026-03-15 的发票"

## 输出

```
~/Desktop/发票-2026-03/
├── 001-XX公司发票通知.pdf
├── 002-YY平台电子发票.pdf
├── 发票汇总.xlsx        ← 按购买方分 sheet，含合计
└── 处理日志.txt
```

## 许可证

[CC BY-NC-SA 4.0](../LICENSE) · 43 COLLEGE 凯寓 (KAIYU) 出品
