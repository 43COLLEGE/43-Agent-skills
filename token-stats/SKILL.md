---
name: token-stats
description: |
  Token 用量统计——扫描 Claude Code 全部会话 JSONL，生成可视化仪表盘和日历。
  **触发场景**：token 统计、用量统计、token usage、消耗了多少 token、花了多少钱、token 日历、用量日历。
version: "1.0.0"
user_invocable: true
---

# Token 用量统计

扫描 `~/.claude/projects/` 下全部会话 JSONL，提供两种可视化视图。

## 安装

本技能依赖 Python 3.10+，无需额外依赖包（纯标准库实现）。

确认脚本路径后直接运行即可。用 Glob 搜索 `**/se7en-token-stats/token_stats.py` 定位绝对路径。

## 1. 仪表盘（token_stats.py）

- **Summary cards**：总量、日均、会话数、消息数
- **Daily Trend**：日度趋势折线图（Cache Read / Cache Write / Output 分层）
- **Weekly / Monthly**：周度和月度堆叠柱状图
- **Token Breakdown**：四类 token 占比环形图 + 明细卡片
- **Models**：模型分布横向进度条
- **Activity by Hour**：24 小时活跃度热力图

```bash
python3 /path/to/token_stats.py
python3 /path/to/token_stats.py --since 2026-03-01
python3 /path/to/token_stats.py -o ~/Desktop/token-report.html
```

| 参数 | 说明 |
|------|------|
| `--since YYYY-MM-DD` | 起始日期 |
| `--until YYYY-MM-DD` | 截止日期 |
| `-o PATH` | 输出文件路径（默认 /tmp/token-stats.html） |
| `--no-open` | 不自动打开浏览器 |

## 2. Token 日历（token_calendar.py）

月历视图，每个日期格子显示当天总 Token 量和各模型消耗分布。支持月份切换、左右键导航、hover 查看详情。

```bash
python3 /path/to/token_calendar.py
python3 /path/to/token_calendar.py --month 2026-03
```

| 参数 | 说明 |
|------|------|
| `--month YYYY-MM` | 初始显示月份（默认当月） |
| `-o PATH` | 输出文件路径（默认 /tmp/token-calendar.html） |
| `--no-open` | 不自动打开浏览器 |

**日历格子内容**：日期（醒目）· 总 Token · 会话/调用数 · 前三模型明细 · 模型占比条。无数据日期虚线边框。

## 触发判断

- 用户说「token 日历」「用量日历」→ 运行 token_calendar.py
- 其他 token 统计类请求 → 运行 token_stats.py

## 数字单位

所有数字使用中文单位：亿、万、千。图表坐标轴、tooltip、卡片数值统一遵循此规则。

## 日历视觉风格

暖光浮动卡片设计：

### 调色板

| 变量 | 值 | 用途 |
|------|-----|------|
| `--bg` | `#f4f1ec` | 暖纸底背景 |
| `--card` | `#ffffff` | 浮动卡片 |
| `--text` | `#1c1917` | 主文本（warm near-black） |
| `--text-secondary` | `#78716c` | 次文本 |
| `--text-tertiary` | `#a8a29e` | 辅助文本 |
| `--accent` | `#d4714f` | 珊瑚强调色 |
| `--border` | `rgba(0,0,0,0.06)` | 默认边框 |
| `--shadow` | `0 1px 3px rgba(120,100,80,0.06)` | 暖色调阴影 |

### 字体

`Outfit`（Google Fonts）+ `PingFang SC` / `Noto Sans SC` CJK fallback。全局 `tabular-nums` 对齐数字。

### 布局规则

- **周一起始**：周一~周日，周六日标记为 weekend（珊瑚色日期）
- **浮动卡片网格**：7 列 CSS Grid，`gap: 8px`，每个有数据的日期是独立白色卡片（`border-radius: 14px`）
- **无数据日期**：虚线边框（`dashed rgba(0,0,0,0.08)`），无背景
- **空占位格**：完全透明，`min-height: 40px`
- **当日高亮**：珊瑚色 `border + box-shadow` 双环

### 日格卡片内容（由上至下）

1. 日期数字（1.1rem / 700 weight，醒目）
2. Token 总量（1.2rem / 700 weight）
3. 会话·调用（0.68rem 辅助文字）
4. 前三模型明细（色点 + 名称 + 用量）
5. 模型占比条（4px 堆叠色带）

### 交互

- **Hover**：卡片 `translateY(-2px)` + 阴影加深，模型条 `scaleY(1.5)`
- **入场动画**：`fadeUp` 瀑布式（`animation-delay: d * 20ms`）
- **Tooltip**：玻璃态（`backdrop-filter: blur(20px)`），含完整模型明细 + 百分比
- **键盘**：左右箭头切换月份

### 页面底部

- **环形图**（SVG donut）：180px，展示月度模型占比，中心显示月度总量
- **模型图例**：两列卡片网格，默认显示前 6 个，「显示全部」按钮展开其余
- 每项含：色点 + 模型名 + 用量 + 百分比

### 响应式

- `< 900px`：模型明细隐藏，图例单列
- `< 600px`：模型条隐藏，日格最小化
- 打印：隐藏导航和页脚
