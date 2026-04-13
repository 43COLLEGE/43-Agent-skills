---
name: board
description: 项目看板生成——基于逻辑大纲和口述梳理，创建任意项目的 HTML 看板。触发场景：创建项目看板、做个看板、项目板、看板生成、board。
---

# 项目看板生成 Skill

## 触发条件

用户说「创建项目看板」「做个看板」「项目板」「看板生成」「board」时触发。

用户会以以下形式之一提供内容：
- 一段口述/散乱的思考（对话中的聊天文字）
- 一份逻辑大纲（已有结构的项目描述）
- 混合模式：既有大纲又有口述补充

## SVG 图标资源

看板中涉及品牌/工具/平台名称时，使用 thesvg MCP 获取高质量品牌 SVG 图标，而非手绘占位符。

### MCP 工具调用

```
search_icons(query: "github")     → 搜索图标，返回 slug + variants
get_icon(slug: "github", variant: "mono")  → 获取原始 SVG 代码
get_icon_url(slug: "github")      → 获取 CDN 嵌入 URL
list_categories()                 → 浏览所有分类
```

### 使用规则

| 场景 | 做法 |
|------|------|
| 品牌名出现（GitHub、Notion、飞书等） | 调 `search_icons` 找到对应 slug，`get_icon` 取 `mono` 或 `default` variant |
| 人在/角色占位图标 | 不用品牌图标，用纯 CSS 圆点/色块 |
| 装饰性小图标（箭头、勾选等） | 用内联 SVG 原语（`<svg>` + `<path>`），保持单文件零依赖 |

### 嵌入方式

```html
<!-- 方式 1：内联 SVG（推荐，零依赖） -->
<svg width="18" height="18" viewBox="0 0 24 24" fill="none">
  <!-- 从 get_icon 获取的 path 内容 -->
</svg>

<!-- 方式 2：CDN URL（图标多时减少文件体积） -->
<img src="https://cdn.thesvg.org/icons/{slug}.svg" alt="{name}" width="18" height="18" style="opacity:0.7" />
```

**变体选择**：深色模式优先 `default` 或 `light` variant；浅色模式优先 `default` 或 `dark`。`mono` variant 在两种模式下都可使用，用 CSS `filter` 或直接调整 `fill`/`stroke` 适配主题。

### 不适用的场景

- 人名/角色 → 用色块圆点，不用图标
- 抽象概念（如"壁垒""时间窗口"）→ 用语义色标记，不用图标
- 图标库中找不到的 → 用简洁的内联 SVG 原语，不要硬凑

## 第一步：结构梳理

收到用户内容后，**不要立即写代码**。先做结构梳理，输出一份「看板蓝图」给用户确认：

### 分析框架

从用户提供的内容中提取以下维度：

1. **已决项**（Decided）：已经确定、不再讨论的决策/事实
2. **待决项**（Open Questions）：需要回答的问题，标注紧急度（must / can-wait / confirm）
3. **依赖链**（Dependencies）：哪些事是另一些事的前提，上下游关系
4. **行动路线**（Actions）：具体要做的事，按时间/阶段分组
5. **交付物**（Deliverables）：做完后手里应该有的东西

### 蓝图输出格式

```
## 看板蓝图：{项目名}

### 板块规划
1. {板块名} — {一句话说明}
2. {板块名} — {一句话说明}
...

### 信息密度
- 已决项：{数量} 条
- 待决项：{数量} 条（must: X / can-wait: X）
- 依赖链：{层级数} 层
- 行动项：{数量} 条
- 交付物：{数量} 项

### 缺失信息
- {指出用户内容中模糊或缺失的地方，一次性列出}

→ 确认后开始生成看板。
```

用户确认蓝图后进入第二步。用户说「就这样」「直接做」「没问题」即视为确认。

## 第二步：看板生成

### 技术约束

- **格式**：单个 `.html` 文件，零依赖，浏览器直接打开
- **字体**：MiSans 本地 + Outfit Google Fonts + CJK 系统回退
- **主题**：深色/浅色双主题，localStorage 持久化用户选择
- **尺寸**：max-width 1200px，响应式（< 960px 单列折叠）
- **打印**：`@media print` 隐藏 footer/toggle，卡片 `break-inside: avoid`

### Design System（强制）

必须严格遵循以下设计系统，这是 taste-skill 校准后的参数化规范：

#### 色彩体系

`:root` 变量（深色模式为默认）：

```css
:root {
  --bg: #0e0e14;
  --surface: rgba(255,255,255,0.04);
  --surface-hover: rgba(255,255,255,0.06);
  --surface-elevated: rgba(255,255,255,0.08);
  --border: rgba(255,255,255,0.08);
  --border-hover: rgba(255,255,255,0.14);
  --text-primary: #e8e6e1;
  --text-secondary: #8a8680;
  --text-tertiary: #4a4744;
  --accent: #4ade80;
  --accent-dim: rgba(74,222,128,0.15);
  --accent-glow: rgba(74,222,128,0.08);
  --amber: #f59e0b;
  --amber-dim: rgba(245,158,11,0.12);
  --rose: #f43f5e;
  --rose-dim: rgba(244,63,94,0.12);
  --blue: #60a5fa;
  --blue-dim: rgba(96,165,250,0.12);
  --purple: #a78bfa;
  --purple-dim: rgba(167,139,250,0.12);
  --radius: 16px;
  --radius-sm: 10px;
  --font: 'MiSans', 'Outfit', 'PingFang SC', 'Noto Sans SC', system-ui, sans-serif;
  --mono: 'MiSans', 'SF Mono', 'Fira Code', ui-monospace, monospace;
  --transition: 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  --shadow-tinted: 0 8px 32px -8px rgba(14,14,20,0.6);
  --shadow-elevated: 0 20px 60px -12px rgba(14,14,20,0.8);
}
```

浅色模式通过 `html[data-theme="light"]` 覆盖，详见参考实现。

#### 语义色彩映射

| 语义 | 色彩 | dim | 用途 |
|------|------|-----|------|
| 完成/通过/积极 | accent (绿) | accent-dim | 已决项、已完成、产出物 |
| 警告/进行中 | amber | amber-dim | 进行中、待确认、需关注 |
| 紧急/未决/阻塞 | rose | rose-dim | 未决、must关、阻塞项 |
| 信息/正常/参考 | blue | blue-dim | 一般信息、参考、链接 |
| 补充/特殊 | purple | purple-dim | 分类标签、日期标记 |

#### 排版层级

- **页面标题**：`1.8rem; font-weight: 700; letter-spacing: -0.04em`
- **板块标题**：`1.1rem; font-weight: 600; letter-spacing: -0.01em`
- **卡片标题**：`1rem; font-weight: 600; letter-spacing: -0.01em`
- **正文**：`0.88rem; color: var(--text-secondary); line-height: 1.6`
- **辅助文字**：`0.82rem; color: var(--text-secondary)`
- **标签/元数据**：`0.72rem; font-weight: 700; font-family: var(--mono); letter-spacing: 0.05em`
- **列头标签**：`0.65rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase`

#### 粗体修正

```css
strong, b { font-weight: 600; font-size: 0.92em; letter-spacing: -0.01em; }
```

#### Surface 层级

| 层级 | 处理 | 用途 |
|------|------|------|
| 标准卡片 | `background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 28px 32px; backdrop-filter: blur(20px)` | 主要内容容器 |
| 紧凑项 | `padding: 14px 16px; border-radius: var(--radius-sm)` | 已决项、交付物小卡片 |
| 内联条 | `padding: 10px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border)` | 产出物、标注条 |

#### 交互态

- 卡片 hover：`border-color: var(--border-hover); box-shadow: var(--shadow-tinted)`
- 按钮/标签 `:active`：`transform: scale(0.96)`（触觉反馈）
- 高亮卡片：`border-color: rgba(accent,0.25)` 或语义色对应值
- 主题切换：右上角圆形按钮，SVG 太阳/月亮图标

### 板块组件库

根据蓝图规划，从以下组件中选取并组合：

#### 1. Header（必须）

```html
<header class="header">
  <div class="header-left">
    <h1>{项目名}</h1>
    <p>{一句话定位}</p>
  </div>
  <div class="header-meta">
    <span class="meta-badge amber">{周期标记}</span>
    <button class="theme-toggle" onclick="toggleTheme()">
      <!-- 太阳/月亮 SVG -->
    </button>
  </div>
</header>
```

#### 2. Section 容器（必须）

每个板块用 `<section class="section">`，内部结构：

```html
<section class="section">
  <div class="section-header">
    <span class="section-num" style="color:var(--{语义色})">{序号}</span>
    <span class="section-title">{板块名}</span>
    <span class="section-sub">{一句话说明}</span>
  </div>
  <!-- 板块内容 -->
</section>
```

#### 3. 已决项网格

3列网格，每项带绿色勾选圆点 + 主文字 + 灰色补充说明：

```html
<div class="decided-grid">
  <div class="decided-item">
    <div>{主文字}<div class="decided-detail">{补充说明}</div></div>
  </div>
</div>
```

#### 4. 依赖链

层级式节点 + 箭头连接，节点按语义色分级：

```html
<div class="dep-chain">
  <div class="dep-row">
    <div class="dep-node {critical|important|normal|output}">
      <span class="dep-num">{序号}</span>{名称}
      <span class="dep-sub">{补充}</span>
    </div>
  </div>
  <div class="dep-arrow-down">↓</div>
  <!-- 下游节点 -->
</div>
```

#### 5. 泳道对比表（Swim Lane）

多维度对比卡片，左侧 ID 标签 + 主内容 + 多列属性：

```html
<div class="lane-thead">
  <div class="lane-th">#</div>
  <div class="lane-th">{列1标题}</div>
  <div class="lane-th">{列2标题}</div>
  <div class="lane-th">{列3标题}</div>
</div>
<div class="lane-grid">
  <div class="lane-card">
    <div class="lane-id" style="background:var(--{色}-dim);color:var(--{色})">{ID}</div>
    <div class="lane-main">
      <div class="lane-name">{名称}</div>
      <div class="lane-desc">{描述}</div>
    </div>
    <div class="lane-cell">
      <div class="lane-cell-label">{列标签}</div>
      <div class="lane-cell-value {strong|warn|weak|neutral}">{值}</div>
    </div>
    <!-- 更多 lane-cell -->
  </div>
</div>
```

单元格值语义色：`strong` = accent（强优势）、`warn` = amber（有风险）、`weak` = rose（弱/短窗口）、`neutral` = text-secondary（中性）

#### 6. 状态表格

表格形式展示问题/任务列表，带状态胶囊：

```html
<div class="card" style="padding:0;overflow:hidden">
  <table class="q-table">
    <thead>
      <tr><th style="width:40%">{列1}</th><th style="width:20%">{列2}</th><th style="width:25%">{列3}</th><th>{列4}</th></tr>
    </thead>
    <tbody>
      <tr>
        <td class="q-name">{问题名}</td>
        <td><span class="q-status {undecided|waiting|progress|minor|已决}">{状态}</span></td>
        <td class="q-urgency {must|can-wait|confirm}">{紧急度描述}</td>
        <td style="color:var(--text-tertiary);font-size:0.82rem">{归属}</td>
      </tr>
    </tbody>
  </table>
</div>
```

状态胶囊样式：
- `undecided`：rose-dim 背景
- `waiting`：amber-dim 背景
- `progress`：blue-dim 背景
- `已决`：accent-dim 背景（内联 `style`）
- `minor`：surface 背景

#### 7. 时间/阶段卡片

按时间线或阶段分组，每个阶段一张大卡片：

```html
<div class="schedule-grid"> <!-- 2列 -->
  <div class="schedule-day">
    <div class="day-header">
      <span class="day-badge {sat|sun|自定义色}">{标签}</span>
      {阶段名}
    </div>
    <div class="session-card">
      <div class="session-header">
        <div class="session-num s{N}">{编号}</div>
        <div class="session-title">{标题}</div>
      </div>
      <div class="session-desc">{描述}</div>
      <div class="session-tasks">
        <div class="session-task">{任务项}</div>
      </div>
      <div class="session-output">{产出物}</div>
    </div>
  </div>
</div>
```

session-num 颜色循环：s1=rose, s2=amber, s3=purple, s4=blue, s5=amber, s6=accent（可按需分配）

任务项支持完成标记：
- 完成：`style="color:var(--accent)"` + `✓` 前缀
- 进行中：`style="color:var(--amber)"` + `◐` 前缀
- 未开始：无额外样式 + `○` 前缀

#### 8. 交付物网格

3列小卡片，编号 + 名称 + 来源说明：

```html
<div class="deliverable-grid">
  <div class="deliverable">
    <div class="deliverable-num">{序号}</div>
    <div class="deliverable-name">{名称}</div>
    <div class="deliverable-for">{← 来源}</div>
  </div>
</div>
```

#### 9. Footer（必须）

```html
<footer class="footer">
  <span>{品牌} · {项目名} · {日期}</span>
  <span>{署名}</span>
</footer>
```

### 组件选取规则

根据蓝图自动判断使用哪些组件：

| 蓝图中有此内容 | 使用组件 |
|---|---|
| 已决项 | 已决项网格 |
| 待决问题列表 | 状态表格 |
| 上下游依赖 | 依赖链 |
| 多方案/多维度对比 | 泳道对比表 |
| 按时间/阶段划分 | 时间卡片 |
| 做完后手里有什么 | 交付物网格 |

**板块顺序原则**：已决地基 → 依赖链/全景 → 核心决策 → 开放问题 → 行动路线 → 交付物

### 交互特性

- **主题切换**：深色/浅色，localStorage 持久化
- **卡片 hover**：边框变亮 + 投影浮起
- **`:active` 触觉**：scale(0.96) 模拟物理按压
- **可点击行**：`cursor: pointer` + onclick 跳转（如有链接）
- **status badge 可点击切换**（可选）：点击循环切换状态

## 第三步：输出

1. 将完整 HTML 写入 `00_专注区/` 目录，文件名格式：`{项目名}.html`
2. 告知用户文件位置
3. 询问是否需要微调

## 反模式（禁止）

- 禁止使用 emoji，用语义色标记 + 图标替代
- 禁止使用纯黑 `#000` 或纯白 `#fff` 文字
- 禁止使用实色灰色卡片背景（必须用 rgba 白色叠加层）
- 禁止使用实色边框（必须用 rgba 透明度边框）
- 禁止使用 Inter 字体
- 禁止使用三列等宽卡片布局（除非是 decided-grid 或 deliverable-grid 的紧凑项）
- 禁止使用 `h-screen`（必须用 `min-height: 100dvh`）
- 禁止在深色模式下使用通用 `rgba(0,0,0,x)` 阴影（必须用色调阴影）
- 禁止泛化 AI 话术（"elevate"、"seamless"、"next-gen"等）

## 参考实现

完整的 CSS + HTML 组件参考：`assets/component-reference.html`（包含所有组件的视觉效果和 HTML 结构示例）

生成看板时，直接复制此文件中的 CSS 和组件 HTML 结构，替换占位内容为实际项目内容。这是权威样式源——不要自行发明 CSS，从这个文件里取。
