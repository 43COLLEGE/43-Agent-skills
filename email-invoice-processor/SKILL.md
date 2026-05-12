---
name: email-invoice-processor
description: 邮箱发票处理器。按日期范围从邮箱中筛选发票邮件，下载PDF/图片附件（含链接下载），提取发票字段，按购买方分sheet生成Excel汇总。当用户需要处理发票、整理发票、从邮箱提取发票时使用此技能。
---

# email-invoice-processor — 邮箱发票处理器

> 作者：43 COLLEGE 凯寓 (KAIYU) 出品
> 版本：v1.0

## 首次配置

如果运行报错找不到 config.json 或邮箱连接失败，读 `SETUP.md` 完成首次配置。

## 跨平台兼容

| 项目 | macOS / Linux | Windows |
|------|--------------|---------|
| Python | `python3` | `python` |
| 脚本路径 | `${CLAUDE_SKILL_DIR}/scripts/process_invoices.py` | `${CLAUDE_SKILL_DIR}\scripts\process_invoices.py` |
| 默认输出 | `~/Desktop/发票-日期/` | `%USERPROFILE%\Desktop\发票-日期\` |
| pip 安装 | `pip install ...` 或 `pip3 install ...` | `python -m pip install ...` |

## 使用方式

**macOS / Linux：**
```bash
# 整月处理
python3 ${CLAUDE_SKILL_DIR}/scripts/process_invoices.py 2026-03

# 指定日期范围
python3 ${CLAUDE_SKILL_DIR}/scripts/process_invoices.py 2026-03-01~2026-03-15

# 单日
python3 ${CLAUDE_SKILL_DIR}/scripts/process_invoices.py 2026-03-15

# 自定义输出目录
python3 ${CLAUDE_SKILL_DIR}/scripts/process_invoices.py 2026-03 -o ~/Desktop/三月发票
```

**Windows：**
```cmd
python ${CLAUDE_SKILL_DIR}\scripts\process_invoices.py 2026-03
python ${CLAUDE_SKILL_DIR}\scripts\process_invoices.py 2026-03 -o %USERPROFILE%\Desktop\三月发票
```

## 处理流程

1. **依赖预检** — 必需依赖缺失则退出，可选依赖缺失仅警告
2. **连接邮箱** — 通过 IMAP SSL 连接（凭证从 config.json 读取）
3. **服务端搜索** — 按关键词+日期在邮箱服务器筛选，避免全量拉取
4. **关键词过滤** — 对邮件主题/发件人/正文做发票关键词匹配
5. **三级附件下载**：
   - 直接附件（PDF / 图片 / **ZIP** 都支持；含 `application/octet-stream` 伪装的 ZIP）
   - 提取正文中的 HTTP 链接（自动处理 HTML 实体编码，支持 `.pdf`/`.png`/`.jpg`/**`.zip`** 直链）
   - **302 启发式**：短链先 `HEAD` 嗅探，若 302 Location 的 query string 里带 `pdfUrl=`/`fileUrl=`/`downloadUrl=` 参数则绕过 SPA 落地页直取真 PDF（云票 bwjf.cn 等 SPA 平台）
   - Playwright 浏览器兜底（需安装可选依赖）
6. **下载后校验**：
   - Magic bytes 文件类型检测（防止 HTML 页面被存为 PDF）
   - **ZIP 自动解压**：识别 `PK\x03\x04`/`PK\x05\x06` magic bytes 自动取出内部 PDF（12306 火车票 ZIP / 字节系发票 `<a download>` 直链）；仅含 OFD 时记日志（pdfplumber 不支持 OFD）
   - 发票有效性校验（PDF 关键词 / 图片尺寸）
   - 二维码自动处理（解码 → 浏览器访问 → 下载 PDF）
7. **字段提取** — pdfplumber 表格提取 + 文本正则双策略
   - **支持负数金额**：12306 退票红冲发票（`￥-88.50`）正确识别
   - **红冲发票备注**：检测到「红冲」或「原发票号码」关键字，自动在备注列写入「退票红冲，原发票号 xxx」
   - **无"价税合计"标签兜底**：12306 电子客票直接 `￥xx.xx` 格式，取绝对值最大的金额作为价税合计
8. **邮件正文 NLP 兜底** — 每封邮件先扫描正文文本，提取 发票号码/开票日期/购买方/销售方/价税合计；附件抓取失败时仍能落表（标"正文提取，待核对"），附件解析成功但缺字段时用正文补全
9. **生成 Excel** — 按购买方分 sheet，含合计行
   - **⚠️ 待人工核对**：xlsx 首页插入醒目橙底 sheet，汇总下载失败、解析失败、仅靠正文落表、购买方未识别等条目（类型/邮件主题/字段提取情况/建议处置）
10. **处理日志** — 记录跳过/失败项

## 输出结构

```
~/Desktop/发票-2026-03/
├── 001-XX公司发票通知.pdf
├── 002-YY平台电子发票.pdf
├── 003-ZZ服务发票-qr.pdf      ← 二维码发票自动解码下载的 PDF
├── 发票汇总.xlsx
└── 处理日志.txt
```

## 提取字段

发票号码、发票代码、开票日期、销售方、购买方、金额（不含税）、税额、价税合计、备注（红冲 / 原发票号 / 正文兜底来源）

## 依赖

**必需**（缺少会退出）：
- `pdfplumber` — PDF 解析
- `openpyxl` — Excel 生成
- `requests` — HTTP 下载
- `Pillow` — 图片处理

**可选**（缺少仅部分功能受限）：
- `playwright` + chromium — 需要 JS 渲染的发票链接下载
- `pyzbar` — 二维码图片自动解码（Windows 需额外安装 libzbar.dll）

安装必需依赖：
```bash
pip install pdfplumber openpyxl requests Pillow
```

## 邮箱兼容性

当前通过 IMAP 协议连接邮箱，config.json 中可配置任意支持 IMAP 的邮箱：

| 邮箱 | imap_server | 备注 |
|------|-------------|------|
| QQ 邮箱 | imap.qq.com | 需开启 IMAP 并生成授权码 |
| 163 邮箱 | imap.163.com | 需开启 IMAP 并设置客户端授权密码 |
| Gmail | imap.gmail.com | 需开启 IMAP 并生成 App Password |
| Outlook | outlook.office365.com | 需开启 IMAP |

默认配置为 QQ 邮箱。更换邮箱只需修改 config.json 中的 `email`、`password`、`imap_server`。

## 已知限制

1. 部分 JS 重度平台（诺诺网等）headless Playwright 可能失败
2. 非标准发票格式可能字段提取不完整
3. OSS 签名链接有时效，过期需重新获取
4. 发票字段提取针对中国增值税发票格式优化
5. ZIP 内仅含 OFD（国标版式文件）时不会提取（pdfplumber 不支持 OFD），日志会标注
6. 邮件正文 NLP 兜底依赖关键词模板，非标准模板邮件（如纯图片邮件）仍可能漏字段，需查看 ⚠️ 待人工核对 sheet
