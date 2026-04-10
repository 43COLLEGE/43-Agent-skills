# 首次配置指南

这份指南写给完全不懂技术的人。配置一次，之后每次使用浏览器功能时 AI 会自动调用。

---

## 你能用这个工具做什么

- 让 AI 像你一样操作浏览器：打开页面、点击按钮、填表、截图
- 访问需要登录的网站（直接用你 Chrome 里已登录的账号）
- 抓取反爬严格的平台内容（小红书、微信公众号等）
- 同时打开多个页面并行调研

---

## 第一步：安装 Node.js

CDP Proxy 需要 Node.js 22 或更高版本。

**Mac 用户：**

1. 打开"终端"（Spotlight 搜"终端"）
2. 粘贴这行命令，回车：
   ```
   brew install node
   ```

> 如果提示 brew 不存在，先去 https://brew.sh 按照首页那行命令装 Homebrew，再回来装 Node.js。

**Windows 用户：**

1. 按 Win+R，输入 `cmd`，回车
2. 粘贴这行命令，回车：
   ```
   winget install OpenJS.NodeJS.LTS
   ```

**验证安装：**

```bash
node --version
```

显示 v22.x.x 或更高就对了。

---

## 第二步：开启 Chrome 远程调试

这一步让 AI 能连接到你的浏览器。

1. 在 Chrome 地址栏输入：`chrome://inspect/#remote-debugging`
2. 勾选 **"Allow remote debugging for this browser instance"**
3. 可能需要重启 Chrome 浏览器

> 这个设置只需要做一次。之后每次打开 Chrome 都会自动生效。

---

## 第三步：验证配置

让 AI 运行这个检查脚本：

```bash
bash ${CLAUDE_SKILL_DIR}/scripts/check-deps.sh
```

正常的话会看到类似这样的输出：

```
node: ok (v22.x.x)
chrome: ok (port 9222)
proxy: ready
```

如果某项显示错误，按照提示操作就行。

---

## 配置完成后，日常怎么用

直接告诉 AI：

> "帮我搜索 xxx 最新进展"
> "去小红书搜索 xxx 的账号"
> "帮我在这个网站上操作 xxx"
> "同时调研这 5 个产品的官网，给我对比摘要"

AI 会自动选择最合适的方式（搜索、网页抓取、或浏览器操作），你不需要知道任何技术细节。

---

## 常见问题

**Chrome 弹出授权窗口怎么办？**

点"允许"就行。这是 Chrome 在确认你允许 AI 连接浏览器。只有首次连接时会弹。

**AI 会不会看到我的密码？**

AI 只操作它自己创建的浏览器标签页，不会主动查看你已打开的页面。但它可以使用你已登录的网站状态（如微信、小红书的登录态）。

**需要一直开着 Chrome 吗？**

使用浏览器功能时需要 Chrome 在运行。如果只是普通搜索（WebSearch），不需要 Chrome。

**Windows 上 Node.js 安装后命令找不到？**

关闭并重新打开命令行窗口，或者重启电脑。
