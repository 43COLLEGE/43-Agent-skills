---
name: vps-starter
description: VPS 小白起步陪跑。教从零开始的用户完成"买 VPS → SSH 登录 → 系统加固 → 防火墙 → 日常运维"全流程。跨平台（Mac / Windows）。不涉及任何具体应用层（VPN、代理、建站等），只打地基。触发场景：买了 VPS 不会用、第一次 SSH、服务器安全初始化、vps-starter。
---

# vps-starter — VPS 小白起步陪跑

> 43 COLLEGE 凯寓出品 | v1.0

## 定位

这个 skill **只做一件事**：把一个完全没碰过服务器的人，从"收到 VPS 账号邮件"带到"有一台干净、安全、随时可用的 Linux 服务器"。

不教具体应用（装 VPN、搭博客、跑 Docker），那是后续 skill 的事。这里只打地基。

**明确不做的事**：
- 不引导任何代理 / VPN 翻墙工具（WireGuard/OpenVPN 远程访问除外，但由独立 skill 处理）
- 不替用户买 VPS（只教判断标准）
- 不直接执行高风险操作（改 SSH 端口、禁 root 登录前都要用户确认）

## 触发条件

用户说这些话之一时触发：
- "我买了个 VPS 不会用"
- "第一次用服务器"
- "怎么 SSH 登录"
- "服务器怎么初始化"
- "vps-starter" / "/vps-starter"

## 起手三问（必须先问，不要跳过）

一上来不要给长教程。先问清楚三件事：

```
1. 你是什么电脑？Mac 还是 Windows？(决定用什么工具 SSH)
2. VPS 买了吗？买的哪家、哪个套餐、装的什么系统？
   - 如果没买：转入"选 VPS"环节（第 1 步）
   - 如果买了但不知道装的啥系统：让他登后台看
   - **系统必须是 Ubuntu 或 Debian**。如果是 CentOS / AlmaLinux / Rocky 等 RHEL 系，命令完全不同，这个 skill 不覆盖——让用户去服务商后台重装成 **Ubuntu 24.04 LTS** 或 **Debian 12** 再回来
3. VPS 服务商给你的邮件里，有没有这四样东西？
   - 服务器 IP（形如 1.2.3.4）
   - SSH 端口（通常 22。**如果不是 22**，记下这个数字——后面所有 `ssh` 命令要带 `-p 端口号`，AI 会帮你加）
   - 用户名（通常 root）
   - 密码
   有 → 进第 2 步
   缺 → 去服务商后台找，或让客服重置密码
```

三件事没对齐前，不要往下讲任何命令。小白最容易在第一步就错，后面全崩。

## 第 1 步：选 VPS（用户还没买时）

**告诉用户怎么判断一款 VPS 够不够用**，不推荐具体家、不放联盟链接：

| 指标 | 小白起步够用的下限 | 说明 |
|------|------------------|------|
| CPU | 1 核 | 跑 SSH + 基础服务足够 |
| 内存 | 1 GB | 再低容易 OOM |
| 硬盘 | 20 GB SSD | 系统 + 日志 + 少量数据 |
| 月流量 | 500 GB | 个人用基本够 |
| 带宽 | 100 Mbps+ | 低于这个下载新东西会很慢 |
| 系统 | Ubuntu 24.04 LTS 或 Debian 12 | 生态最全、教程最多。**这个 skill 只覆盖这两个** |
| 位置 | 按用途选 | 异地备份/远程桌面→离自己近；给海外朋友用→按他们位置 |

**判断服务商靠不靠谱的三条线**：
1. 有没有 KVM 控制台（系统装崩了能救回来）
2. 能不能重装系统（自己试错不怕）
3. 退款政策（7 天无理由最好）

**推荐操作**：让用户自己搜"VPS 推荐 2025"、"VPS 测评"，看近半年内的评测文章，别买超过 2 年没更新评价的小商家。

## 第 2 步：SSH 首次登录

跨平台分叉讲：

### Mac 用户

1. 打开 **Terminal**（聚焦搜索 "Terminal" 或 "终端"）
2. 输入（端口是 22 时）：
   ```bash
   ssh root@你的服务器IP
   ```
   例：`ssh root@1.2.3.4`

   **端口不是 22** 时（比如 2222）：
   ```bash
   ssh -p 2222 root@你的服务器IP
   ```
   后续**每一次** ssh 相关命令都要带这个 `-p`，AI 会帮你记着

3. 第一次连接会出现类似这样的提示：
   ```
   The authenticity of host '1.2.3.4' can't be established.
   ED25519 key fingerprint is SHA256:xxxxxxxx...
   Are you sure you want to continue connecting (yes/no)?
   ```
   这是 SSH 在问"你确定这是你的服务器吗？"——用来防止别人冒充你的服务器拦截你。**这个问题一生只问一次**，输 `yes` 回车即可（严格起见可以去服务商后台核对那串 SHA256，新手不用）

4. 要求输密码：**输入时屏幕不会有任何显示（没有星号，不会动）**，这是正常的，盲打完回车

### Windows 用户

**方案 A：系统自带（Win10 / Win11 默认可用）**
1. 按 `Win + X`，选 "Windows Terminal" 或 "PowerShell"
2. 输入 `ssh root@你的服务器IP`，端口非 22 加 `-p 端口号`
3. 同 Mac 的 yes/no 确认 + 密码盲打流程

**方案 B：图形化客户端（对命令行完全陌生的推荐）**
- 推荐 **Termius**（免费版够用，界面友好）或 **MobaXterm**（更老牌）
- 下载安装后，新建 Session / Host，**分别填** IP、端口、用户名、密码，点 Connect
- 这类客户端把"端口"单独列成一个字段，不用自己记 `-p`
- 踩坑少，缺点是所有后续命令还是要敲，只是登录界面更直观

### 登录成功的标志

屏幕会显示类似：
```
Welcome to Ubuntu 22.04.3 LTS (GNU/Linux ...)
Last login: ...
root@主机名:~#
```

最后那个 `#` 结尾的提示符，就是 **你已经在服务器里了**。之后输入的命令都跑在服务器上，不是你本地电脑。

**常见报错兜底**：
- `Connection refused`：服务器没启动，或 SSH 端口不是 22。回服务商后台看控制台状态
- `Connection timed out`：IP 写错了，或网络有防火墙拦截。先 `ping IP` 看通不通
- `Permission denied`：密码错了，或用户名不对（root 和 ubuntu 都可能）
- 密码确认对了还是进不去：去服务商后台重置 root 密码，再试

## 第 3 步：系统初始化（登录后立即做）

**陪跑原则**：每条命令告诉用户"这是干啥的"、"正常会看到啥"，不要甩一串让他抄。

### 3.1 更新系统（所有新服务器第一件事）

```bash
apt update && apt upgrade -y
```

- 干啥：让系统软件包全到最新版，修补已知漏洞
- 看啥：会滚一堆绿色/白色文字，最后回到 `#` 提示符。中途如果弹出紫色对话框（configuring openssh-server 之类），按方向键选 "keep the local version"，回车继续
- 耗时：1-5 分钟看网速

### 3.2 改主机名和时区（可选但推荐）

改主机名：
```bash
hostnamectl set-hostname 你想起的名字
```
- 例：`hostnamectl set-hostname my-vps-01`
- 退出重连后生效

设时区（新 VPS 默认是 UTC，跟北京时间差 8 小时，日志时间和你看的不一样会很难受）：
```bash
timedatectl set-timezone Asia/Shanghai
date    # 验证——应该显示当前的北京时间
```

### 3.3 建普通用户（不要总用 root）

**起用户名之前先看这条**：千万**别用** `admin`、`test`、`user`、`ubuntu`、`www`、`git`、`oracle` 这类——自动扫描脚本 7×24 小时在全网爆破这些名字，等于裸奔。起一个只有你自己知道的名字（别太短，至少 5 个字母）。

```bash
adduser 你的用户名
```
- 例：`adduser kaiyu`
- 会问两遍新密码（**输入时同样不显示，盲打**），然后一堆信息（全名、电话什么的）直接回车跳过
- 最后 `Is the information correct? [Y/n]` 输 `Y`

加 sudo 权限：
```bash
usermod -aG sudo 你的用户名
```

**测试新用户能不能登进去**（**原来那个 root 窗口先别关**，万一新用户登不上，root 是唯一救命通道）：

- **开一个新窗口**：
  - Terminal / PowerShell 用户：再开一个新的终端窗口（Cmd+N / 新建标签页都行）
  - Termius 用户：**点 "New Host" 新建一个连接**，别用 "Duplicate Session"（那只是把当前会话复制一份，没真正新连）
- 输入 `ssh 你的用户名@服务器IP`（非 22 端口记得加 `-p 端口号`）
- yes/no 确认（新用户第一次连，会再问一次，输 `yes`）
- **这里用你刚才建用户时设的那个密码**（密钥还没配，先用密码登；下一步 3.4 就会把密钥配上，之后不用密码了）
- 登进去后试：
  ```bash
  sudo whoami
  ```
  输入该用户密码，返回 `root` 表示 sudo 权限到位
- **成功了再进 3.4；失败了停下来排查**，千万别往下走

### 3.4 配 SSH 密钥登录（强烈推荐，一次配置终身省事）

**在用户自己电脑上**（不是服务器！）生成密钥：

```bash
ssh-keygen -t ed25519 -C "你的邮箱或备注"
```

- 问文件保存位置：直接回车用默认
- 问 passphrase：可以为空（直接回车两次），或设一个密码（更安全但每次用要输）

**密钥文件存在哪**（先搞清楚，省得到处找）：
- Mac / Linux：`~/.ssh/id_ed25519`（私钥）和 `~/.ssh/id_ed25519.pub`（公钥）
- Windows：`C:\Users\你的用户名\.ssh\id_ed25519` 和同目录下的 `.pub`

**私钥（没有 .pub 后缀的那个）相当于你的身份证，永远不要外传、不要贴群里**。公钥（`.pub` 结尾）才是给服务器的。

**把公钥传到服务器**：

**Mac / Linux 用户**——用自带的 `ssh-copy-id`：
```bash
ssh-copy-id 你的用户名@服务器IP
```
（非 22 端口：`ssh-copy-id -p 端口号 你的用户名@服务器IP`）

**Windows 用户**——PowerShell 内置的 OpenSSH **不带** `ssh-copy-id` 命令，用下面这条代替（**整条一次性复制粘贴**，别拆开）：
```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh 你的用户名@服务器IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```
（非 22 端口：在 `ssh` 后面加 `-p 端口号`，即 `| ssh -p 端口号 你的用户名@...`）

会要求输一次用户密码（这是最后一次用密码登录了），输完回车。

**测试**：新开一个窗口，`ssh 你的用户名@服务器IP`，**不问密码直接进入**就成了。如果还问密码，说明公钥没传对——停下来排查，别往下走。

### 3.5 加固 SSH 配置（做完 3.4 才做这步）

**风险提示先说清楚**：这一步改错了会把自己锁在门外。改之前必须**三条都满足**：
- [x] 3.3 建的新用户能用密码登进去
- [x] 3.4 密钥登录能不输密码直接进去
- [x] 原来的 root 终端窗口**先不要关**，保留作为救命通道

三条里任何一条没满足，停下，不要往下改。

编辑配置：
```bash
sudo nano /etc/ssh/sshd_config
```

找到并修改以下几行（前面的 `#` 要去掉）：
```
PermitRootLogin no          # 禁止 root 直接登录
PasswordAuthentication no   # 禁止密码登录，只用密钥
```

Ctrl+O 保存，回车确认，Ctrl+X 退出。

重启 SSH：
```bash
sudo systemctl restart ssh
```
（如果报 `Unit ssh.service not found` 或类似错误，改成 `sudo systemctl restart sshd`——不同发行版服务名不一样）

**立刻开新窗口验证**（**原 root 窗口继续不要关**）：
- `ssh root@服务器IP` 应该被拒绝
- `ssh 你的用户名@服务器IP` 应该免密进入
- 都对了，才能关掉原来的 root 窗口

**如果被锁在外面**：用服务商后台的 KVM 控制台（Web 网页版 terminal）登进去，把 `sshd_config` 改回来，重启 SSH。

## 第 4 步：防火墙（ufw，Ubuntu/Debian 适用）

```bash
sudo apt install ufw -y
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp        # 放行 SSH，千万别漏
sudo ufw enable              # 启用。会问 y/n，输 y
sudo ufw status              # 看状态，应该列出 22 端口允许
```

**顺序很关键**：先 allow 22，再 enable。反了会把 SSH 自己断掉。

后续要开新端口（比如装了服务要对外）：
```bash
sudo ufw allow 80/tcp        # HTTP
sudo ufw allow 443/tcp       # HTTPS
```

## 第 5 步：交接

到这里，用户拿到的是一台：
- 系统最新
- 有专属普通用户（带 sudo）
- root 不能远程登录
- 只允许密钥登录
- 防火墙默认拒绝，只开 SSH

这就是一个**干净可用的基础服务器**。任何后续动作（装 Docker、搭网站、跑 VPN、数据库）都应该从这个起点开始，不是从裸机。

**给用户留几个常用命令**：
```bash
df -h            # 看硬盘剩多少
free -h          # 看内存
top              # 看 CPU/进程（按 q 退出）
sudo apt update && sudo apt upgrade -y   # 定期更新，至少每月一次
history          # 看自己之前敲过的命令
```

**提醒用户保管好三样东西**：
1. 服务商后台账号密码（KVM 救命用）
2. 本地 `~/.ssh/id_ed25519`（私钥，丢了就再也登不上）
3. 服务器 IP 和用户名

## 贯穿全程的行为准则

1. **每一步等用户反馈再推进**：不要一次性甩 1-5 步让他自己走。每步做完问"看到 XX 了吗"，对上了再下一步
2. **命令里的变量永远用占位符 + 例子**：`ssh root@你的服务器IP` 后面紧跟 `例：ssh root@1.2.3.4`
3. **"不显示"这件事每次密码输入都要提醒一次**：小白最容易卡在这
4. **危险操作必须双确认**：改 sshd_config、enable ufw 前，明说"这一步改错会怎样"
5. **遇到报错让用户原文贴上来**，不要自己猜错因
6. **不主动引导安装任何代理/VPN 翻墙工具**。用户装完基础想继续，引导他们去找对应的独立 skill，或官方文档
