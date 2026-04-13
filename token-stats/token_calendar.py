#!/usr/bin/env python3
"""Token 日历 — 月历视图展示每日 Token 用量与模型分布

生成一个日历形式的 HTML 页面，每个日期格子显示当天总 Token 量及各模型消耗。
"""

import json
import os
import sys
import argparse
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
import calendar

LOCAL_TZ = datetime.now(timezone.utc).astimezone().tzinfo

# Model short name mapping
MODEL_SHORT = {
    "claude-opus-4-6-20250527": "Opus 4.6",
    "claude-sonnet-4-6-20250514": "Sonnet 4.6",
    "claude-sonnet-4-5-20250514": "Sonnet 4.5",
    "claude-sonnet-4-20250514": "Sonnet 4",
    "claude-haiku-4-5-20251001": "Haiku 4.5",
}

MODEL_COLORS_MAP = {
    "Opus 4.6": "#e07850",
    "Sonnet 4.6": "#5b8fd9",
    "Sonnet 4.5": "#5b8fd9",
    "Sonnet 4": "#7fc4d4",
    "Haiku 4.5": "#6bbf7a",
}

FALLBACK_COLORS = ["#9b7fd4", "#d4a27f", "#d47fa8", "#7fc4d4", "#b8a060"]


def shorten_model(name: str) -> str:
    if name in MODEL_SHORT:
        return MODEL_SHORT[name]
    s = name.replace("claude-", "").replace("anthropic.", "")
    # strip date suffix like -20250527
    parts = s.rsplit("-", 1)
    if len(parts) == 2 and len(parts[1]) == 8 and parts[1].isdigit():
        s = parts[0]
    return s


def find_jsonl_files():
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        print(f"Error: {base} not found", file=sys.stderr)
        sys.exit(1)
    return list(base.rglob("*.jsonl"))


def scan_all(files):
    """Scan all JSONL files, return per-day per-model aggregated data."""
    # day_data[date_str][model_short] = total_tokens
    day_data = defaultdict(lambda: defaultdict(int))
    day_totals = defaultdict(int)
    day_sessions = defaultdict(set)
    day_calls = defaultdict(int)
    errors = 0

    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        errors += 1
                        continue
                    if obj.get("type") != "assistant":
                        continue
                    msg = obj.get("message", {})
                    usage = msg.get("usage")
                    if not usage:
                        continue
                    ts_str = obj.get("timestamp")
                    if not ts_str:
                        continue
                    try:
                        ts = datetime.fromisoformat(
                            ts_str.replace("Z", "+00:00")
                        ).astimezone(LOCAL_TZ)
                    except (ValueError, TypeError):
                        continue

                    d = ts.date().isoformat()
                    model = shorten_model(msg.get("model", "unknown"))
                    tokens = (
                        usage.get("input_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                        + usage.get("output_tokens", 0)
                    )
                    day_data[d][model] += tokens
                    day_totals[d] += tokens
                    day_calls[d] += 1
                    sid = obj.get("sessionId", "")
                    if sid:
                        day_sessions[d].add(sid)
        except (OSError, UnicodeDecodeError):
            errors += 1

    if errors:
        print(f"(跳过 {errors} 条解析错误)", file=sys.stderr)

    return day_data, day_totals, day_sessions, day_calls


def fmt(n):
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.0f}万"
    if n >= 1_000:
        return f"{n / 1_000:.0f}千"
    return str(n)


def prepare_calendar_data(day_data, day_totals, day_sessions, day_calls):
    """Prepare data structure for the calendar frontend."""
    if not day_totals:
        return {}

    all_dates = sorted(day_totals.keys())
    min_date = datetime.strptime(all_dates[0], "%Y-%m-%d").date()
    max_date = datetime.strptime(all_dates[-1], "%Y-%m-%d").date()

    # Collect all months
    months = set()
    d = min_date.replace(day=1)
    while d <= max_date:
        months.add(d.strftime("%Y-%m"))
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)
    months = sorted(months)

    # Collect all models across entire dataset
    all_models = set()
    for models in day_data.values():
        all_models.update(models.keys())
    # Sort by total usage descending
    model_totals = defaultdict(int)
    for models in day_data.values():
        for m, t in models.items():
            model_totals[m] += t
    sorted_models = sorted(all_models, key=lambda m: -model_totals[m])

    # Assign colors
    model_colors = {}
    fallback_idx = 0
    for m in sorted_models:
        if m in MODEL_COLORS_MAP:
            model_colors[m] = MODEL_COLORS_MAP[m]
        else:
            model_colors[m] = FALLBACK_COLORS[fallback_idx % len(FALLBACK_COLORS)]
            fallback_idx += 1

    # Build per-day entries
    days = {}
    for d_str in all_dates:
        models = {}
        for m in sorted_models:
            v = day_data[d_str].get(m, 0)
            if v > 0:
                models[m] = v
        days[d_str] = {
            "total": day_totals[d_str],
            "sessions": len(day_sessions.get(d_str, set())),
            "calls": day_calls.get(d_str, 0),
            "models": models,
        }

    # Max daily total for heat scaling
    max_daily = max(day_totals.values()) if day_totals else 1

    return {
        "months": months,
        "days": days,
        "models": sorted_models,
        "model_colors": model_colors,
        "model_totals": {m: model_totals[m] for m in sorted_models},
        "max_daily": max_daily,
    }


# ── HTML Template ─────────────────────────────────────────

CALENDAR_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Token Calendar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #f4f1ec;
    --card: #ffffff;
    --text: #1c1917;
    --text-secondary: #78716c;
    --text-tertiary: #a8a29e;
    --border: rgba(0,0,0,0.06);
    --border-hover: rgba(0,0,0,0.10);
    --accent: #d4714f;
    --accent-light: rgba(212,113,79,0.08);
    --accent-dim: rgba(212,113,79,0.15);
    --shadow: 0 1px 3px rgba(120,100,80,0.06);
    --shadow-hover: 0 8px 28px rgba(120,100,80,0.10);
    --radius: 14px;
    --radius-sm: 10px;
    --transition: 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Outfit', 'PingFang SC', 'Noto Sans SC', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 48px 32px 80px;
  }

  /* ── Page Label ── */
  .page-label {
    font-size: 0.73rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 8px;
  }

  /* ── Header ── */
  .header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 32px;
  }

  .header h1 {
    font-size: 2.2rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1.1;
  }

  .header h1 .year {
    font-weight: 400;
    color: var(--text-tertiary);
    margin-right: 4px;
  }

  .nav {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .nav button {
    width: 36px; height: 36px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text-secondary);
    font-size: 15px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all var(--transition);
    box-shadow: var(--shadow);
  }

  .nav button:hover {
    border-color: var(--border-hover);
    box-shadow: var(--shadow-hover);
    color: var(--text);
  }

  .nav button:active { transform: scale(0.96); }

  .nav button:disabled {
    opacity: 0.3;
    cursor: not-allowed;
    box-shadow: none;
  }

  .nav .today-btn {
    width: auto;
    padding: 0 18px;
    font-size: 0.8rem;
    font-weight: 600;
    font-family: inherit;
    letter-spacing: 0.02em;
  }

  /* ── Summary Card ── */
  .summary-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    display: flex;
    margin-bottom: 24px;
    overflow: hidden;
    animation: fadeIn 0.3s ease both;
  }

  .stat {
    flex: 1;
    padding: 20px 24px;
    border-right: 1px solid var(--border);
    min-width: 0;
  }

  .stat:last-child { border-right: none; }

  .stat-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .stat.primary .stat-value { color: var(--accent); }

  /* ── Model Legend (bottom section) ── */
  .legend-section {
    margin-top: 36px;
    animation: fadeIn 0.3s ease 0.2s both;
  }

  .legend-title {
    font-size: 0.73rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 14px;
  }

  .legend-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    transition: all var(--transition);
  }

  .legend-item:hover {
    border-color: var(--border-hover);
    box-shadow: var(--shadow);
  }

  .legend-item.collapsed { display: none; }

  .legend-dot {
    width: 10px; height: 10px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .legend-name {
    flex: 1;
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--text);
  }

  .legend-val {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-secondary);
    font-variant-numeric: tabular-nums;
  }

  .legend-toggle {
    margin-top: 10px;
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 8px 18px;
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    font-family: inherit;
    transition: all var(--transition);
  }

  .legend-toggle:hover {
    border-color: var(--border-hover);
    color: var(--text);
  }

  .legend-toggle:active { transform: scale(0.96); }

  /* ── Donut Chart ── */
  .legend-layout {
    display: flex;
    gap: 36px;
    align-items: flex-start;
  }

  .donut-wrap {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .donut-chart {
    width: 180px;
    height: 180px;
    position: relative;
  }

  .donut-chart svg {
    width: 100%;
    height: 100%;
    transform: rotate(-90deg);
  }

  .donut-chart .donut-center {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transform: none;
  }

  .donut-center .dc-value {
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }

  .donut-center .dc-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-tertiary);
  }

  .legend-right {
    flex: 1;
    min-width: 0;
  }

  @media (max-width: 700px) {
    .legend-layout { flex-direction: column; align-items: center; }
    .donut-chart { width: 150px; height: 150px; }
  }

  /* ── Weekday Headers ── */
  .weekdays {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 8px;
    margin-bottom: 8px;
  }

  .wd {
    text-align: center;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-tertiary);
    padding: 6px 0;
  }

  /* ── Calendar Grid ── */
  .cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 8px;
  }

  .day {
    min-height: 148px;
    border-radius: var(--radius);
    padding: 14px;
    transition: all var(--transition);
    display: flex;
    flex-direction: column;
  }

  .day.has-data {
    background: var(--card);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    cursor: default;
  }

  .day.has-data:hover {
    box-shadow: var(--shadow-hover);
    border-color: var(--border-hover);
    transform: translateY(-2px);
  }

  .day.no-data {
    background: rgba(0,0,0,0.01);
    border: 1.5px dashed rgba(0,0,0,0.13);
    border-radius: var(--radius);
  }

  .day.empty {
    background: transparent;
    min-height: 40px;
  }

  .day.today {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent), var(--shadow) !important;
  }

  .day.weekend .day-num { color: var(--accent); }

  /* ── Day Content ── */
  .day-num {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    font-variant-numeric: tabular-nums;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 5px;
    letter-spacing: -0.02em;
  }

  .day.no-data .day-num {
    color: var(--text-tertiary);
    font-weight: 500;
  }

  .day.today .day-num {
    color: var(--accent);
  }

  .today-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--accent);
  }

  .day-total {
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--text);
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
    margin-bottom: 4px;
  }

  .day-meta {
    font-size: 0.68rem;
    color: var(--text-tertiary);
    font-variant-numeric: tabular-nums;
    margin-bottom: 6px;
  }

  /* ── Model Pills (in day cell) ── */
  .model-pills {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-top: auto;
  }

  .model-pill {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 0.65rem;
    color: var(--text-secondary);
    line-height: 1.3;
  }

  .model-pill .mp-dot {
    width: 5px; height: 5px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .model-pill .mp-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .model-pill .mp-val {
    font-weight: 600;
    color: var(--text);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  /* ── Model Bar ── */
  .model-bar {
    display: flex;
    height: 4px;
    border-radius: 2px;
    overflow: hidden;
    margin-top: 12px;
    background: rgba(0,0,0,0.04);
  }

  .model-bar .seg {
    height: 100%;
    min-width: 2px;
    transition: transform 0.2s;
    transform-origin: bottom;
  }

  .day.has-data:hover .model-bar .seg {
    transform: scaleY(1.5);
  }

  /* ── Stagger Animation ── */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .day.has-data {
    animation: fadeUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  }

  /* ── Tooltip ── */
  .tooltip {
    position: fixed;
    background: rgba(255,255,255,0.94);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px 24px;
    box-shadow: 0 12px 40px rgba(120,100,80,0.12);
    pointer-events: none;
    z-index: 100;
    opacity: 0;
    transition: opacity 0.2s;
    min-width: 220px;
  }

  .tooltip.show { opacity: 1; }

  .tt-date {
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-secondary);
    letter-spacing: 0.02em;
    margin-bottom: 8px;
  }

  .tt-total {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    color: var(--accent);
    font-variant-numeric: tabular-nums;
    margin-bottom: 2px;
  }

  .tt-meta {
    font-size: 0.75rem;
    color: var(--text-tertiary);
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }

  .tt-model {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 0.8rem;
  }

  .tt-dot {
    width: 7px; height: 7px;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .tt-name {
    flex: 1;
    color: var(--text-secondary);
  }

  .tt-val {
    font-weight: 600;
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }

  .tt-pct {
    font-size: 0.7rem;
    color: var(--text-tertiary);
    min-width: 38px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  /* ── Footer ── */
  .footer {
    text-align: center;
    margin-top: 48px;
    font-size: 0.75rem;
    color: var(--text-tertiary);
    letter-spacing: 0.02em;
  }

  /* ── Responsive ── */
  @media (max-width: 900px) {
    .container { padding: 24px 16px 60px; }
    .header h1 { font-size: 1.6rem; }
    .summary-card { flex-wrap: wrap; }
    .stat { min-width: 45%; border-bottom: 1px solid var(--border); }
    .stat:nth-child(even) { border-right: none; }
    .cal-grid, .weekdays { gap: 4px; }
    .day { min-height: 90px; padding: 8px; }
    .day-total { font-size: 0.9rem; }
    .day-meta { display: none; }
    .model-pills { display: none; }
    .legend-grid { grid-template-columns: 1fr; }
  }

  @media (max-width: 600px) {
    .day { min-height: 60px; padding: 6px; }
    .day-num { font-size: 0.8rem; margin-bottom: 4px; }
    .day-total { font-size: 0.8rem; }
    .model-bar { display: none; }
  }

  @media print {
    .footer, .nav { display: none; }
    .day { break-inside: avoid; }
    body { background: white; }
  }
</style>
</head>
<body>

<div class="container">
  <div class="page-label">Token Calendar</div>
  <div class="header">
    <h1 id="calTitle"></h1>
    <div class="nav">
      <button id="prevBtn" title="上月">&#8249;</button>
      <button class="today-btn" id="todayBtn">今天</button>
      <button id="nextBtn" title="下月">&#8250;</button>
    </div>
  </div>

  <div class="summary-card" id="summaryCard"></div>

  <div class="weekdays">
    <div class="wd">周一</div>
    <div class="wd">周二</div>
    <div class="wd">周三</div>
    <div class="wd">周四</div>
    <div class="wd">周五</div>
    <div class="wd">周六</div>
    <div class="wd">周日</div>
  </div>

  <div class="cal-grid" id="calGrid"></div>

  <div class="legend-section" id="legendSection"></div>
</div>

<div class="tooltip" id="tooltip"></div>
<div class="footer">token-stats skill · Claude Code</div>

<script>
const DATA = {{DATA_JSON}};
const TODAY = '{{TODAY}}';

const MONTH_NAMES = ['一月','二月','三月','四月','五月','六月','七月','八月','九月','十月','十一月','十二月'];
const WEEKDAY_NAMES = ['周日','周一','周二','周三','周四','周五','周六'];

let currentYear, currentMonth;

function fmtTick(v) {
  if (v >= 1e8) return (v/1e8).toFixed(1) + '亿';
  if (v >= 1e4) return (v/1e4).toFixed(0) + '万';
  if (v >= 1e3) return (v/1e3).toFixed(1) + '千';
  return v.toString();
}

function fmtTickDetail(v) {
  if (v >= 1e8) return (v/1e8).toFixed(2) + '亿';
  if (v >= 1e4) return (v/1e4).toFixed(1) + '万';
  if (v >= 1e3) return (v/1e3).toFixed(1) + '千';
  return v.toLocaleString();
}

function pad2(n) { return String(n).padStart(2, '0'); }
function dateStr(y, m, d) { return `${y}-${pad2(m)}-${pad2(d)}`; }
function daysInMonth(y, m) { return new Date(y, m, 0).getDate(); }
// Monday-first: Mon=0, Tue=1, ..., Sun=6
function firstDayOfWeekMon(y, m) {
  return (new Date(y, m - 1, 1).getDay() + 6) % 7;
}

const LEGEND_VISIBLE = 6; // show top 6 by default

function renderMonth(y, m) {
  currentYear = y;
  currentMonth = m;
  const monthStr = `${y}-${pad2(m)}`;

  // Title
  document.getElementById('calTitle').innerHTML =
    `<span class="year">${y}</span>${MONTH_NAMES[m-1]}`;

  // Nav bounds
  const idx = DATA.months.indexOf(monthStr);
  document.getElementById('prevBtn').disabled = idx <= 0;
  document.getElementById('nextBtn').disabled = idx >= DATA.months.length - 1;

  // Compute month stats
  let monthTotal = 0, monthCalls = 0, monthSessions = 0, monthActiveDays = 0;
  let monthModels = {};
  const nDays = daysInMonth(y, m);
  for (let d = 1; d <= nDays; d++) {
    const ds = dateStr(y, m, d);
    const info = DATA.days[ds];
    if (info) {
      monthTotal += info.total;
      monthCalls += info.calls;
      monthSessions += info.sessions;
      monthActiveDays++;
      for (const [model, val] of Object.entries(info.models)) {
        monthModels[model] = (monthModels[model] || 0) + val;
      }
    }
  }

  // Summary card
  document.getElementById('summaryCard').innerHTML = `
    <div class="stat primary">
      <div class="stat-label">\u6708\u5ea6\u603b\u91cf</div>
      <div class="stat-value">${fmtTick(monthTotal)}</div>
    </div>
    <div class="stat">
      <div class="stat-label">\u65e5\u5747\u6d88\u8017</div>
      <div class="stat-value">${monthActiveDays > 0 ? fmtTick(Math.floor(monthTotal / monthActiveDays)) : '\u2014'}</div>
    </div>
    <div class="stat">
      <div class="stat-label">\u6d3b\u8dc3\u5929\u6570</div>
      <div class="stat-value">${monthActiveDays} <span style="font-size:0.8rem;font-weight:400;color:var(--text-tertiary)">/ ${nDays}</span></div>
    </div>
    <div class="stat">
      <div class="stat-label">\u4f1a\u8bdd</div>
      <div class="stat-value">${monthSessions.toLocaleString()}</div>
    </div>
    <div class="stat">
      <div class="stat-label">\u8c03\u7528</div>
      <div class="stat-value">${monthCalls.toLocaleString()}</div>
    </div>
  `;

  // Calendar grid
  const grid = document.getElementById('calGrid');
  grid.innerHTML = '';
  const startDay = firstDayOfWeekMon(y, m);

  // Empty cells before month start
  for (let i = 0; i < startDay; i++) {
    const cell = document.createElement('div');
    cell.className = 'day empty';
    grid.appendChild(cell);
  }

  // Actual days
  for (let d = 1; d <= nDays; d++) {
    const ds = dateStr(y, m, d);
    const info = DATA.days[ds];
    const dow = (startDay + d - 1) % 7; // Mon=0 ... Sun=6
    const isWeekend = dow === 5 || dow === 6; // Sat=5, Sun=6
    const isToday = ds === TODAY;
    const hasData = info && info.total > 0;

    const cell = document.createElement('div');
    cell.className = 'day' +
      (hasData ? ' has-data' : ' no-data') +
      (isWeekend ? ' weekend' : '') +
      (isToday ? ' today' : '');
    cell.dataset.date = ds;

    if (hasData) {
      cell.style.animationDelay = `${d * 20}ms`;
    }

    // Day number
    const numEl = document.createElement('div');
    numEl.className = 'day-num';
    numEl.innerHTML = d + (isToday ? ' <span class="today-dot"></span>' : '');
    cell.appendChild(numEl);

    if (hasData) {
      // Total
      const totalEl = document.createElement('div');
      totalEl.className = 'day-total';
      totalEl.textContent = fmtTick(info.total);
      cell.appendChild(totalEl);

      // Meta
      const metaEl = document.createElement('div');
      metaEl.className = 'day-meta';
      metaEl.textContent = `${info.sessions} \u4f1a\u8bdd \u00b7 ${info.calls} \u8c03\u7528`;
      cell.appendChild(metaEl);

      // Model pills (top 3)
      const dayModels = Object.entries(info.models).sort((a, b) => b[1] - a[1]);
      const pillsEl = document.createElement('div');
      pillsEl.className = 'model-pills';
      const topModels = dayModels.slice(0, 3);
      for (const [model, val] of topModels) {
        const pill = document.createElement('div');
        pill.className = 'model-pill';
        pill.innerHTML = `<span class="mp-dot" style="background:${DATA.model_colors[model] || '#999'}"></span><span class="mp-name">${model}</span><span class="mp-val">${fmtTick(val)}</span>`;
        pillsEl.appendChild(pill);
      }
      cell.appendChild(pillsEl);

      // Model bar
      const bar = document.createElement('div');
      bar.className = 'model-bar';
      for (const [model, val] of dayModels) {
        const seg = document.createElement('div');
        seg.className = 'seg';
        seg.style.width = (val / info.total * 100).toFixed(1) + '%';
        seg.style.background = DATA.model_colors[model] || '#999';
        bar.appendChild(seg);
      }
      cell.appendChild(bar);
    }

    grid.appendChild(cell);
  }

  // Trailing empty cells
  const totalCells = startDay + nDays;
  const trailing = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
  for (let i = 0; i < trailing; i++) {
    const cell = document.createElement('div');
    cell.className = 'day empty';
    grid.appendChild(cell);
  }

  // ── Bottom legend with donut chart ──
  const legendSection = document.getElementById('legendSection');
  const sortedModels = DATA.models
    .filter(m => monthModels[m] > 0)
    .sort((a, b) => (monthModels[b] || 0) - (monthModels[a] || 0));

  // Build SVG donut
  const R = 70, STROKE = 28, CX = 90, CY = 90, C = 2 * Math.PI * R;
  let donutArcs = '';
  let offset = 0;
  for (const model of sortedModels) {
    const val = monthModels[model] || 0;
    const pct = monthTotal > 0 ? val / monthTotal : 0;
    const len = pct * C;
    const color = DATA.model_colors[model] || '#999';
    donutArcs += `<circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="${color}" stroke-width="${STROKE}" stroke-dasharray="${len.toFixed(2)} ${(C - len).toFixed(2)}" stroke-dashoffset="${(-offset).toFixed(2)}" />`;
    offset += len;
  }

  const donutSVG = `<div class="donut-chart">
    <svg viewBox="0 0 180 180"><circle cx="${CX}" cy="${CY}" r="${R}" fill="none" stroke="rgba(0,0,0,0.04)" stroke-width="${STROKE}" />${donutArcs}</svg>
    <div class="donut-center"><span class="dc-value">${fmtTick(monthTotal)}</span><span class="dc-label">\u672c\u6708\u603b\u91cf</span></div>
  </div>`;

  // Build legend grid
  const needToggle = sortedModels.length > LEGEND_VISIBLE;
  let gridHTML = '<div class="legend-grid">';
  sortedModels.forEach((model, i) => {
    const color = DATA.model_colors[model] || '#999';
    const pct = monthTotal > 0 ? ((monthModels[model] || 0) / monthTotal * 100).toFixed(1) : '0';
    const cls = i >= LEGEND_VISIBLE ? ' collapsed' : '';
    gridHTML += `<div class="legend-item${cls}" data-legend-idx="${i}">
      <span class="legend-dot" style="background:${color}"></span>
      <span class="legend-name">${model}</span>
      <span class="legend-val">${fmtTick(monthModels[model] || 0)} <span style="color:var(--text-tertiary);font-weight:400;font-size:0.75rem">${pct}%</span></span>
    </div>`;
  });
  gridHTML += '</div>';

  let toggleHTML = '';
  if (needToggle) {
    toggleHTML = `<button class="legend-toggle" id="legendToggle">\u663e\u793a\u5168\u90e8 (${sortedModels.length})</button>`;
  }

  legendSection.innerHTML = `
    <div class="legend-title">\u6a21\u578b\u7528\u91cf\u5206\u5e03</div>
    <div class="legend-layout">
      <div class="donut-wrap">${donutSVG}</div>
      <div class="legend-right">${gridHTML}${toggleHTML}</div>
    </div>`;

  if (needToggle) {
    let expanded = false;
    document.getElementById('legendToggle').onclick = function() {
      expanded = !expanded;
      legendSection.querySelectorAll('.legend-item').forEach(el => {
        const idx = parseInt(el.dataset.legendIdx);
        if (idx >= LEGEND_VISIBLE) {
          el.classList.toggle('collapsed', !expanded);
        }
      });
      this.textContent = expanded ? '\u6536\u8d77' : `\u663e\u793a\u5168\u90e8 (${sortedModels.length})`;
    };
  }
}

// ── Navigation ──

function prevMonth() {
  let y = currentYear, m = currentMonth - 1;
  if (m < 1) { m = 12; y--; }
  renderMonth(y, m);
}

function nextMonth() {
  let y = currentYear, m = currentMonth + 1;
  if (m > 12) { m = 1; y++; }
  renderMonth(y, m);
}

function goToday() {
  const [y, m] = TODAY.split('-').map(Number);
  renderMonth(y, m);
}

document.getElementById('prevBtn').onclick = prevMonth;
document.getElementById('nextBtn').onclick = nextMonth;
document.getElementById('todayBtn').onclick = goToday;

// ── Tooltip ──

const tooltip = document.getElementById('tooltip');

document.getElementById('calGrid').addEventListener('mousemove', (e) => {
  const cell = e.target.closest('.day');
  if (!cell || !cell.classList.contains('has-data')) {
    tooltip.classList.remove('show');
    return;
  }
  const ds = cell.dataset.date;
  const info = DATA.days[ds];
  if (!info || info.total === 0) {
    tooltip.classList.remove('show');
    return;
  }

  const [y, m, d] = ds.split('-').map(Number);
  const dow = new Date(y, m - 1, d).getDay();
  let html = `<div class="tt-date">${ds} ${WEEKDAY_NAMES[dow]}</div>`;
  html += `<div class="tt-total">${fmtTickDetail(info.total)}</div>`;
  html += `<div class="tt-meta">${info.sessions} \u4f1a\u8bdd \u00b7 ${info.calls} \u6b21\u8c03\u7528</div>`;

  const dayModels = Object.entries(info.models).sort((a, b) => b[1] - a[1]);
  for (const [model, val] of dayModels) {
    const pct = (val / info.total * 100).toFixed(1);
    html += `<div class="tt-model">
      <span class="tt-dot" style="background:${DATA.model_colors[model] || '#999'}"></span>
      <span class="tt-name">${model}</span>
      <span class="tt-val">${fmtTickDetail(val)}</span>
      <span class="tt-pct">${pct}%</span>
    </div>`;
  }

  tooltip.innerHTML = html;
  tooltip.classList.add('show');

  const rect = tooltip.getBoundingClientRect();
  let left = e.clientX + 16;
  let top = e.clientY + 16;
  if (left + rect.width > window.innerWidth - 20) left = e.clientX - rect.width - 16;
  if (top + rect.height > window.innerHeight - 20) top = e.clientY - rect.height - 16;
  tooltip.style.left = left + 'px';
  tooltip.style.top = top + 'px';
});

document.getElementById('calGrid').addEventListener('mouseleave', () => {
  tooltip.classList.remove('show');
});

// ── Keyboard nav ──
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowLeft') prevMonth();
  else if (e.key === 'ArrowRight') nextMonth();
});

// ── Init ──
const initMonth = '{{INIT_MONTH}}' || TODAY.slice(0, 7);
const [initY, initM] = initMonth.split('-').map(Number);
renderMonth(initY, initM);
</script>
</body>
</html>"""


def render_calendar_html(data, today_str, init_month):
    html = CALENDAR_HTML
    html = html.replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False, default=str))
    html = html.replace("{{TODAY}}", today_str)
    html = html.replace("{{INIT_MONTH}}", init_month or "")
    return html


def main():
    p = argparse.ArgumentParser(description="Token 日历 — 月历视图展示每日用量与模型分布")
    p.add_argument("--month", type=str, help="初始显示月份 YYYY-MM（默认当月）")
    p.add_argument("--no-open", action="store_true", help="生成 HTML 但不自动打开")
    p.add_argument("-o", "--output", type=str, help="输出文件路径（默认临时文件）")
    args = p.parse_args()

    today_str = datetime.now(LOCAL_TZ).date().isoformat()

    print("正在扫描会话文件...", file=sys.stderr, flush=True)
    files = find_jsonl_files()
    print(f"找到 {len(files)} 个文件，解析中...", file=sys.stderr, flush=True)

    day_data, day_totals, day_sessions, day_calls = scan_all(files)
    print(f"完成：{len(day_totals)} 天有数据", file=sys.stderr, flush=True)

    if not day_totals:
        print("无数据", file=sys.stderr)
        return

    data = prepare_calendar_data(day_data, day_totals, day_sessions, day_calls)
    html = render_calendar_html(data, today_str, args.month or "")

    if args.output:
        out_path = args.output
    else:
        out_path = os.path.join(tempfile.gettempdir(), "token-calendar.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"日历已生成：{out_path}", file=sys.stderr)

    if not args.no_open:
        import platform
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", out_path], check=False)
        elif system == "Linux":
            subprocess.run(["xdg-open", out_path], check=False)
        elif system == "Windows":
            os.startfile(out_path)


if __name__ == "__main__":
    main()
