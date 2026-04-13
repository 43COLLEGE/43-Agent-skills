#!/usr/bin/env python3
"""Claude Code Token 用量统计 — HTML 可视化报告

扫描 ~/.claude/projects/ 下全部会话 JSONL，生成 Cowork 风格的可视化仪表盘。
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

LOCAL_TZ = datetime.now(timezone.utc).astimezone().tzinfo


# ── 数据采集 ──────────────────────────────────────────────

def find_jsonl_files():
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        print(f"Error: {base} not found", file=sys.stderr)
        sys.exit(1)
    return list(base.rglob("*.jsonl"))


def _home_noise_words():
    """Derive noise words from the user's home path (platform-agnostic)."""
    parts = Path.home().parts  # e.g. ('/', 'Users', 'alice')
    noise = {"Users", "home", "Library", "Mobile", "Documents", "com", "apple", "CloudDocs"}
    noise.update(p for p in parts if p != "/")
    return noise

_HOME_NOISE = _home_noise_words()


def extract_project_name(path: Path) -> str:
    parts = path.parts
    try:
        idx = parts.index("projects")
        proj = parts[idx + 1]
        if proj == "-":
            return "(global)"
        segments = proj.split("-")
        meaningful = [s for s in segments if s and s not in _HOME_NOISE]
        return "-".join(meaningful[-3:]) if meaningful else proj
    except (ValueError, IndexError):
        return str(path.parent.name)


def scan_all(files, since_dt=None, until_dt=None):
    records = []
    sessions_seen = set()
    errors = 0

    for filepath in files:
        project = extract_project_name(filepath)
        is_sub = "subagents" in filepath.parts
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
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
                    except (ValueError, TypeError):
                        continue
                    if since_dt and ts.date() < since_dt:
                        continue
                    if until_dt and ts.date() > until_dt:
                        continue

                    session_id = obj.get("sessionId", filepath.stem)
                    sessions_seen.add(session_id)
                    records.append({
                        "ts": ts,
                        "date": ts.date(),
                        "hour": ts.hour,
                        "model": msg.get("model", "unknown"),
                        "project": project,
                        "is_subagent": is_sub,
                        "session_id": session_id,
                        "input": usage.get("input_tokens", 0),
                        "cache_write": usage.get("cache_creation_input_tokens", 0),
                        "cache_read": usage.get("cache_read_input_tokens", 0),
                        "output": usage.get("output_tokens", 0),
                    })
        except (OSError, UnicodeDecodeError):
            errors += 1

    if errors:
        print(f"(跳过 {errors} 条解析错误)", file=sys.stderr)
    return records, len(sessions_seen)


# ── 聚合 ──────────────────────────────────────────────────

def aggregate(records, key_fn):
    groups = defaultdict(lambda: {
        "input": 0, "cache_write": 0, "cache_read": 0, "output": 0,
        "messages": 0, "sessions": set()
    })
    for r in records:
        k = key_fn(r)
        g = groups[k]
        g["input"] += r["input"]
        g["cache_write"] += r["cache_write"]
        g["cache_read"] += r["cache_read"]
        g["output"] += r["output"]
        g["messages"] += 1
        g["sessions"].add(r["session_id"])
    return groups


def total_tokens(g):
    return g["input"] + g["cache_write"] + g["cache_read"] + g["output"]


def fmt(n):
    if n >= 100_000_000:
        return f"{n / 100_000_000:.2f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    if n >= 1_000:
        return f"{n / 1_000:.1f}千"
    return str(n)


def iso_week(d):
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def compute_model_list(records, grand_total):
    models = defaultdict(lambda: {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0, "messages": 0})
    for r in records:
        m = models[r["model"]]
        for k in ("input", "cache_write", "cache_read", "output"):
            m[k] += r[k]
        m["messages"] += 1
    result = []
    for name, m in sorted(models.items(), key=lambda x: -sum(x[1][k] for k in ("input", "cache_write", "cache_read", "output"))):
        t = m["input"] + m["cache_write"] + m["cache_read"] + m["output"]
        if t == 0:
            continue
        result.append({
            "name": name,
            "total": t,
            "pct": round(t / grand_total * 100, 1) if grand_total else 0,
            "messages": m["messages"]
        })
    return result


def compute_hourly(records):
    hour_groups = aggregate(records, lambda r: r["hour"])
    return [total_tokens(hour_groups[h]) if h in hour_groups else 0 for h in range(24)]


# ── 数据准备 ──────────────────────────────────────────────

def prepare_data(records, total_sessions, since_dt=None, until_dt=None):
    """将 records 聚合为前端所需的全部数据结构"""
    if not records:
        return {}

    # 总量
    totals = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}
    dates = set()
    for r in records:
        for k in ("input", "cache_write", "cache_read", "output"):
            totals[k] += r[k]
        dates.add(r["date"])

    grand_total = sum(totals.values())
    min_date = min(dates)
    max_date = max(dates)
    days = (max_date - min_date).days + 1

    # 日度（全部日期，补零）
    daily_groups = aggregate(records, lambda r: str(r["date"]))
    all_dates = []
    d = min_date
    while d <= max_date:
        all_dates.append(str(d))
        d += timedelta(days=1)
    daily = []
    for ds in all_dates:
        g = daily_groups.get(ds)
        if g:
            daily.append({
                "date": ds,
                "input": g["input"], "cache_write": g["cache_write"],
                "cache_read": g["cache_read"], "output": g["output"],
                "total": total_tokens(g),
                "sessions": len(g["sessions"]), "messages": g["messages"]
            })
        else:
            daily.append({"date": ds, "input": 0, "cache_write": 0, "cache_read": 0, "output": 0, "total": 0, "sessions": 0, "messages": 0})

    # 周度
    weekly_groups = aggregate(records, lambda r: iso_week(r["date"]))
    weekly = []
    for wk in sorted(weekly_groups.keys()):
        g = weekly_groups[wk]
        weekly.append({
            "week": wk,
            "input": g["input"], "cache_write": g["cache_write"],
            "cache_read": g["cache_read"], "output": g["output"],
            "total": total_tokens(g),
            "sessions": len(g["sessions"]), "messages": g["messages"]
        })

    # 月度
    monthly_groups = aggregate(records, lambda r: r["date"].strftime("%Y-%m"))
    monthly = []
    for mo in sorted(monthly_groups.keys()):
        g = monthly_groups[mo]
        monthly.append({
            "month": mo,
            "input": g["input"], "cache_write": g["cache_write"],
            "cache_read": g["cache_read"], "output": g["output"],
            "total": total_tokens(g),
            "sessions": len(g["sessions"]), "messages": g["messages"]
        })

    # 模型
    model_list = compute_model_list(records, grand_total)

    # 小时热力图
    hourly = compute_hourly(records)

    # ── 按月明细（用于前端月份切换）──
    monthly_detail = {}
    records_by_month = defaultdict(list)
    for r in records:
        records_by_month[r["date"].strftime("%Y-%m")].append(r)

    for mo_key, mo_records in records_by_month.items():
        mo_totals = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}
        mo_sessions = set()
        mo_dates = set()
        for r in mo_records:
            for k in ("input", "cache_write", "cache_read", "output"):
                mo_totals[k] += r[k]
            mo_sessions.add(r["session_id"])
            mo_dates.add(r["date"])
        mo_grand = sum(mo_totals.values())
        mo_days = (max(mo_dates) - min(mo_dates)).days + 1 if mo_dates else 1

        # 周度
        mo_weekly_groups = aggregate(mo_records, lambda r: iso_week(r["date"]))
        mo_weekly = []
        for wk in sorted(mo_weekly_groups.keys()):
            g = mo_weekly_groups[wk]
            mo_weekly.append({
                "week": wk,
                "input": g["input"], "cache_write": g["cache_write"],
                "cache_read": g["cache_read"], "output": g["output"],
                "total": total_tokens(g),
            })

        monthly_detail[mo_key] = {
            "totals": mo_totals,
            "grand_total": mo_grand,
            "sessions": len(mo_sessions),
            "messages": len(mo_records),
            "days": mo_days,
            "daily_avg": mo_grand // mo_days if mo_days else 0,
            "models": compute_model_list(mo_records, mo_grand),
            "hourly": compute_hourly(mo_records),
            "weekly": mo_weekly,
        }

    return {
        "totals": totals,
        "grand_total": grand_total,
        "sessions": total_sessions,
        "messages": len(records),
        "days": days,
        "daily_avg": grand_total // days,
        "min_date": str(min_date),
        "max_date": str(max_date),
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "models": model_list,
        "hourly": hourly,
        "monthly_detail": monthly_detail,
        "filter_since": str(since_dt) if since_dt else None,
        "filter_until": str(until_dt) if until_dt else None,
    }


# ── HTML 模板 ─────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Token 用量仪表盘</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #faf8f6;
    --card: #ffffff;
    --text: #1a1a1a;
    --text-secondary: #6b6560;
    --text-tertiary: #a09890;
    --border: #eee9e4;
    --accent: #e07850;
    --accent-light: #f5c8b4;
    --accent-bg: #fef3ee;
    --blue: #5b8fd9;
    --green: #6bbf7a;
    --purple: #9b7fd4;
    --shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.03);
    --shadow-hover: 0 2px 8px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.05);
    --radius: 16px;
    --radius-sm: 10px;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  .container {
    max-width: 1120px;
    margin: 0 auto;
    padding: 48px 24px 80px;
  }

  /* Header */
  .header {
    margin-bottom: 24px;
  }
  .header h1 {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--text);
  }
  .header .subtitle {
    font-size: 15px;
    color: var(--text-tertiary);
    margin-top: 6px;
  }
  .header .subtitle span {
    color: var(--accent);
    font-weight: 600;
  }

  /* Month tabs */
  .month-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 32px;
    flex-wrap: wrap;
  }
  .month-tab {
    padding: 8px 18px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    border: 1.5px solid var(--border);
    background: var(--card);
    color: var(--text-secondary);
    transition: all 0.2s ease;
    user-select: none;
  }
  .month-tab:hover {
    border-color: var(--accent-light);
    color: var(--accent);
  }
  .month-tab.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }

  /* Stat cards row */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 32px;
  }
  .stat-card {
    background: var(--card);
    border-radius: var(--radius);
    padding: 24px;
    box-shadow: var(--shadow);
    transition: box-shadow 0.2s ease, transform 0.2s ease;
  }
  .stat-card:hover {
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }
  .stat-card .label {
    font-size: 13px;
    color: var(--text-tertiary);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
  }
  .stat-card .value {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--text);
  }
  .stat-card .detail {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 4px;
  }
  .stat-card.accent {
    background: var(--accent);
    color: white;
  }
  .stat-card.accent .label { color: rgba(255,255,255,0.75); }
  .stat-card.accent .value { color: white; }
  .stat-card.accent .detail { color: rgba(255,255,255,0.8); }

  /* Chart cards */
  .chart-card {
    background: var(--card);
    border-radius: var(--radius);
    padding: 28px;
    box-shadow: var(--shadow);
    margin-bottom: 24px;
  }
  .chart-card h2 {
    font-size: 17px;
    font-weight: 650;
    color: var(--text);
    margin-bottom: 20px;
  }
  .chart-card .chart-wrap {
    position: relative;
    width: 100%;
  }

  /* Two-col layout */
  .row-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
  }

  /* Three-col layout */
  .row-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 24px;
  }

  /* Token breakdown mini cards */
  .breakdown-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 16px;
  }
  .breakdown-item {
    background: var(--bg);
    border-radius: var(--radius-sm);
    padding: 16px;
  }
  .breakdown-item .b-label {
    font-size: 12px;
    color: var(--text-tertiary);
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .breakdown-item .b-label .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .breakdown-item .b-value {
    font-size: 20px;
    font-weight: 700;
    margin-top: 4px;
    letter-spacing: -0.3px;
  }
  .breakdown-item .b-pct {
    font-size: 12px;
    color: var(--text-tertiary);
  }

  /* Model list */
  .model-list { list-style: none; }
  .model-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
  }
  .model-item:last-child { border-bottom: none; }
  .model-bar-bg {
    flex: 1;
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
  }
  .model-bar {
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s ease;
  }
  .model-name {
    font-size: 13px;
    font-weight: 500;
    min-width: 180px;
    color: var(--text);
  }
  .model-pct {
    font-size: 13px;
    color: var(--text-tertiary);
    min-width: 50px;
    text-align: right;
  }
  .model-total {
    font-size: 13px;
    color: var(--text-secondary);
    font-weight: 600;
    min-width: 60px;
    text-align: right;
  }

  /* Heatmap */
  .heatmap-row {
    display: flex;
    gap: 4px;
    align-items: end;
    height: 100px;
    padding-top: 8px;
  }
  .heatmap-bar {
    flex: 1;
    background: var(--accent-light);
    border-radius: 4px 4px 0 0;
    min-height: 2px;
    transition: background 0.2s;
    position: relative;
  }
  .heatmap-bar:hover { background: var(--accent); }
  .heatmap-labels {
    display: flex;
    gap: 4px;
    margin-top: 6px;
  }
  .heatmap-labels span {
    flex: 1;
    text-align: center;
    font-size: 10px;
    color: var(--text-tertiary);
  }

  /* Filter badge */
  .filter-badge {
    display: inline-block;
    margin-top: 8px;
    padding: 5px 14px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
    color: var(--accent);
    background: var(--accent-bg);
    border: 1px solid var(--accent-light);
  }
  .filter-badge:empty { display: none; }

  /* Footer */
  .footer {
    text-align: center;
    margin-top: 48px;
    font-size: 13px;
    color: var(--text-tertiary);
  }

  /* Responsive */
  @media (max-width: 768px) {
    .stats-row { grid-template-columns: repeat(2, 1fr); }
    .row-2, .row-3 { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>Token 用量仪表盘</h1>
    <div class="subtitle" id="subtitle"></div>
    <div class="filter-badge" id="filterBadge"></div>
  </div>

  <!-- Month tabs -->
  <div class="month-tabs" id="monthTabs"></div>

  <!-- Summary cards -->
  <div class="stats-row">
    <div class="stat-card accent">
      <div class="label">总消耗</div>
      <div class="value" id="totalValue"></div>
      <div class="detail" id="totalDetail"></div>
    </div>
    <div class="stat-card">
      <div class="label">日均消耗</div>
      <div class="value" id="avgValue"></div>
      <div class="detail">每天</div>
    </div>
    <div class="stat-card">
      <div class="label">会话数</div>
      <div class="value" id="sessionsValue"></div>
      <div class="detail" id="sessionsDetail"></div>
    </div>
    <div class="stat-card">
      <div class="label">消息数</div>
      <div class="value" id="messagesValue"></div>
      <div class="detail">助手回复</div>
    </div>
  </div>

  <!-- Daily trend -->
  <div class="chart-card">
    <h2>日度趋势</h2>
    <div class="chart-wrap"><canvas id="dailyChart" height="80"></canvas></div>
  </div>

  <!-- Weekly + Monthly -->
  <div class="row-2">
    <div class="chart-card">
      <h2>周度统计</h2>
      <div class="chart-wrap"><canvas id="weeklyChart" height="120"></canvas></div>
    </div>
    <div class="chart-card">
      <h2>月度统计</h2>
      <div class="chart-wrap"><canvas id="monthlyChart" height="120"></canvas></div>
    </div>
  </div>

  <!-- Breakdown + Models + Hourly -->
  <div class="row-3">
    <!-- Token breakdown -->
    <div class="chart-card">
      <h2>Token 构成</h2>
      <div class="chart-wrap" style="max-width:220px;margin:0 auto;">
        <canvas id="breakdownChart"></canvas>
      </div>
      <div class="breakdown-grid">
        <div class="breakdown-item">
          <div class="b-label"><span class="dot" style="background:#e07850"></span>输入</div>
          <div class="b-value" id="inputFmt"></div>
          <div class="b-pct" id="inputPct"></div>
        </div>
        <div class="breakdown-item">
          <div class="b-label"><span class="dot" style="background:#5b8fd9"></span>缓存写入</div>
          <div class="b-value" id="cacheWriteFmt"></div>
          <div class="b-pct" id="cacheWritePct"></div>
        </div>
        <div class="breakdown-item">
          <div class="b-label"><span class="dot" style="background:#9b7fd4"></span>缓存读取</div>
          <div class="b-value" id="cacheReadFmt"></div>
          <div class="b-pct" id="cacheReadPct"></div>
        </div>
        <div class="breakdown-item">
          <div class="b-label"><span class="dot" style="background:#6bbf7a"></span>输出</div>
          <div class="b-value" id="outputFmt"></div>
          <div class="b-pct" id="outputPct"></div>
        </div>
      </div>
    </div>

    <!-- Models -->
    <div class="chart-card">
      <h2>模型分布</h2>
      <ul class="model-list" id="modelList"></ul>
    </div>

    <!-- Hourly activity -->
    <div class="chart-card">
      <h2>24 小时活跃度</h2>
      <div class="heatmap-row" id="heatmap"></div>
      <div class="heatmap-labels" id="heatmapLabels"></div>
    </div>
  </div>
</div>

<div class="footer">由 token-stats 技能生成 · Claude Code</div>

<script>
const DATA = {{DATA_JSON}};

// Color palette
const C = {
  accent: '#e07850',
  accentLight: 'rgba(224,120,80,0.15)',
  blue: '#5b8fd9',
  blueLight: 'rgba(91,143,217,0.15)',
  purple: '#9b7fd4',
  purpleLight: 'rgba(155,127,212,0.15)',
  green: '#6bbf7a',
  greenLight: 'rgba(107,191,122,0.15)',
  grid: 'rgba(0,0,0,0.04)',
  text: '#6b6560',
};

const MODEL_COLORS = ['#e07850', '#5b8fd9', '#9b7fd4', '#6bbf7a', '#d4a27f', '#7fc4d4', '#d47fa8'];

// Shared chart defaults
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = C.text;

function fmtTick(v) {
  if (v >= 1e8) return (v/1e8).toFixed(1) + '亿';
  if (v >= 1e4) return (v/1e4).toFixed(0) + '万';
  if (v >= 1e3) return (v/1e3).toFixed(0) + '千';
  return v;
}

function pct(part, total) {
  return total > 0 ? (part / total * 100).toFixed(1) : '0';
}

// ── 初始化图表（存储引用以便后续更新）──

const dailyChart = new Chart(document.getElementById('dailyChart'), {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      {
        label: '缓存读取',
        data: [],
        backgroundColor: C.purpleLight,
        borderColor: C.purple,
        borderWidth: 1.5,
        fill: true,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
      {
        label: '缓存写入',
        data: [],
        backgroundColor: C.blueLight,
        borderColor: C.blue,
        borderWidth: 1.5,
        fill: true,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
      {
        label: '输出',
        data: [],
        backgroundColor: C.greenLight,
        borderColor: C.green,
        borderWidth: 1.5,
        fill: true,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
    ]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { display: true, position: 'top', labels: { boxWidth: 10, padding: 16, usePointStyle: true } },
      tooltip: { mode: 'index', intersect: false, callbacks: { label: ctx => ctx.dataset.label + ': ' + fmtTick(ctx.raw) } }
    },
    scales: {
      x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkipPadding: 16 } },
      y: { grid: { color: C.grid }, ticks: { callback: fmtTick }, stacked: false }
    },
    interaction: { mode: 'index', intersect: false },
  }
});

const weeklyChart = new Chart(document.getElementById('weeklyChart'), {
  type: 'bar',
  data: {
    labels: [],
    datasets: [
      { label: '缓存读取', data: [], backgroundColor: C.purple, borderRadius: 4 },
      { label: '缓存写入', data: [], backgroundColor: C.blue, borderRadius: 4 },
      { label: '输出', data: [], backgroundColor: C.green, borderRadius: 4 },
    ]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { display: true, position: 'top', labels: { boxWidth: 8, padding: 12, usePointStyle: true } },
      tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmtTick(ctx.raw) } }
    },
    scales: {
      x: { stacked: true, grid: { display: false } },
      y: { stacked: true, grid: { color: C.grid }, ticks: { callback: fmtTick } }
    }
  }
});

const monthlyChart = new Chart(document.getElementById('monthlyChart'), {
  type: 'bar',
  data: {
    labels: [],
    datasets: [
      { label: '缓存读取', data: [], backgroundColor: [], borderRadius: 6 },
      { label: '缓存写入', data: [], backgroundColor: [], borderRadius: 6 },
      { label: '输出', data: [], backgroundColor: [], borderRadius: 6 },
    ]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { display: true, position: 'top', labels: { boxWidth: 8, padding: 12, usePointStyle: true } },
      tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmtTick(ctx.raw) } }
    },
    scales: {
      x: { stacked: true, grid: { display: false } },
      y: { stacked: true, grid: { color: C.grid }, ticks: { callback: fmtTick } }
    }
  }
});

const breakdownChart = new Chart(document.getElementById('breakdownChart'), {
  type: 'doughnut',
  data: {
    labels: ['输入', '缓存写入', '缓存读取', '输出'],
    datasets: [{
      data: [0, 0, 0, 0],
      backgroundColor: [C.accent, C.blue, C.purple, C.green],
      borderWidth: 0,
      spacing: 2,
    }]
  },
  options: {
    cutout: '68%',
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: ctx => ctx.label + ': ' + fmtTick(ctx.raw) } }
    }
  }
});

// ── 渲染辅助函数 ──

function renderModels(models) {
  const el = document.getElementById('modelList');
  el.innerHTML = '';
  models.forEach((m, i) => {
    const color = MODEL_COLORS[i % MODEL_COLORS.length];
    const li = document.createElement('li');
    li.className = 'model-item';
    li.innerHTML = `
      <span class="model-name">${m.name.replace('claude-', '').replace(/-\d{8}$/, '')}</span>
      <div class="model-bar-bg"><div class="model-bar" style="width:${m.pct}%;background:${color}"></div></div>
      <span class="model-total">${fmtTick(m.total)}</span>
      <span class="model-pct">${m.pct}%</span>
    `;
    el.appendChild(li);
  });
}

function renderHeatmap(hourly) {
  const heatmap = document.getElementById('heatmap');
  const heatLabels = document.getElementById('heatmapLabels');
  heatmap.innerHTML = '';
  heatLabels.innerHTML = '';
  const maxH = Math.max(...hourly);
  hourly.forEach((v, h) => {
    const p = maxH > 0 ? (v / maxH * 100) : 0;
    const bar = document.createElement('div');
    bar.className = 'heatmap-bar';
    bar.style.height = Math.max(p, 2) + '%';
    bar.title = h + ':00 — ' + fmtTick(v);
    if (p > 70) bar.style.background = '#e07850';
    else if (p > 40) bar.style.background = '#f0a880';
    heatmap.appendChild(bar);

    const lbl = document.createElement('span');
    lbl.textContent = h % 3 === 0 ? h + '' : '';
    heatLabels.appendChild(lbl);
  });
}

// ── 月份切换核心逻辑 ──

let currentMonth = null;

function setMonth(month) {
  currentMonth = month;

  // 更新标签激活状态
  document.querySelectorAll('.month-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.month === (month || ''));
  });

  let filteredDaily, totals, sessions, messages, days, models, hourly, filteredWeekly;
  let minDate, maxDate;

  if (!month) {
    filteredDaily = DATA.daily;
    totals = DATA.totals;
    sessions = DATA.sessions;
    messages = DATA.messages;
    days = DATA.days;
    models = DATA.models;
    hourly = DATA.hourly;
    filteredWeekly = DATA.weekly;
    minDate = DATA.min_date;
    maxDate = DATA.max_date;
  } else {
    const detail = DATA.monthly_detail[month];
    filteredDaily = DATA.daily.filter(d => d.date.startsWith(month));
    totals = detail.totals;
    sessions = detail.sessions;
    messages = detail.messages;
    days = detail.days;
    models = detail.models;
    hourly = detail.hourly;
    filteredWeekly = detail.weekly;
    if (filteredDaily.length > 0) {
      minDate = filteredDaily[0].date;
      maxDate = filteredDaily[filteredDaily.length - 1].date;
    } else {
      minDate = maxDate = month;
    }
  }

  const grandTotal = totals.input + totals.cache_write + totals.cache_read + totals.output;
  const dailyAvg = days > 0 ? Math.floor(grandTotal / days) : 0;

  // 更新副标题
  document.getElementById('subtitle').innerHTML =
    `${minDate} → ${maxDate}（${days} 天）· 累计 <span>${fmtTick(grandTotal)}</span>`;

  // 更新摘要卡片
  document.getElementById('totalValue').textContent = fmtTick(grandTotal);
  document.getElementById('totalDetail').textContent = grandTotal.toLocaleString();
  document.getElementById('avgValue').textContent = fmtTick(dailyAvg);
  document.getElementById('sessionsValue').textContent = sessions.toLocaleString();
  document.getElementById('sessionsDetail').textContent = '日均 ' + (days > 0 ? (sessions / days).toFixed(1) : '0') + ' 个';
  document.getElementById('messagesValue').textContent = messages.toLocaleString();

  // 更新日度趋势
  dailyChart.data.labels = filteredDaily.map(d => d.date.slice(5));
  dailyChart.data.datasets[0].data = filteredDaily.map(d => d.cache_read);
  dailyChart.data.datasets[1].data = filteredDaily.map(d => d.cache_write);
  dailyChart.data.datasets[2].data = filteredDaily.map(d => d.output);
  dailyChart.update();

  // 更新周度
  weeklyChart.data.labels = filteredWeekly.map(w => w.week);
  weeklyChart.data.datasets[0].data = filteredWeekly.map(w => w.cache_read);
  weeklyChart.data.datasets[1].data = filteredWeekly.map(w => w.cache_write);
  weeklyChart.data.datasets[2].data = filteredWeekly.map(w => w.output);
  weeklyChart.update();

  // 更新月度（高亮选中月）
  const baseColors = { purple: C.purple, blue: C.blue, green: C.green };
  const dimColors = { purple: 'rgba(155,127,212,0.2)', blue: 'rgba(91,143,217,0.2)', green: 'rgba(107,191,122,0.2)' };
  monthlyChart.data.labels = DATA.monthly.map(m => m.month);
  monthlyChart.data.datasets[0].data = DATA.monthly.map(m => m.cache_read);
  monthlyChart.data.datasets[1].data = DATA.monthly.map(m => m.cache_write);
  monthlyChart.data.datasets[2].data = DATA.monthly.map(m => m.output);
  const colorKeys = ['purple', 'blue', 'green'];
  colorKeys.forEach((ck, i) => {
    monthlyChart.data.datasets[i].backgroundColor = DATA.monthly.map(m =>
      (!month || m.month === month) ? baseColors[ck] : dimColors[ck]
    );
  });
  monthlyChart.update();

  // 更新 Token 构成
  breakdownChart.data.datasets[0].data = [totals.input, totals.cache_write, totals.cache_read, totals.output];
  breakdownChart.update();
  document.getElementById('inputFmt').textContent = fmtTick(totals.input);
  document.getElementById('inputPct').textContent = pct(totals.input, grandTotal) + '%';
  document.getElementById('cacheWriteFmt').textContent = fmtTick(totals.cache_write);
  document.getElementById('cacheWritePct').textContent = pct(totals.cache_write, grandTotal) + '%';
  document.getElementById('cacheReadFmt').textContent = fmtTick(totals.cache_read);
  document.getElementById('cacheReadPct').textContent = pct(totals.cache_read, grandTotal) + '%';
  document.getElementById('outputFmt').textContent = fmtTick(totals.output);
  document.getElementById('outputPct').textContent = pct(totals.output, grandTotal) + '%';

  // 更新模型分布
  renderModels(models);

  // 更新小时热力图
  renderHeatmap(hourly);
}

// ── 过滤器提示 ──

const filterBadge = document.getElementById('filterBadge');
const filterSince = DATA.filter_since;
const filterUntil = DATA.filter_until;
const hasFilter = !!(filterSince || filterUntil);

if (hasFilter) {
  const parts = [];
  if (filterSince) parts.push('从 ' + filterSince);
  if (filterUntil) parts.push('至 ' + filterUntil);
  filterBadge.textContent = '筛选范围：' + parts.join(' ');
}

// 判断月份是否被过滤截断（部分数据）
function isPartialMonth(monthStr) {
  if (!hasFilter) return false;
  // monthStr like "2026-03"
  const monthStart = monthStr + '-01';
  // 计算月末
  const [y, m] = monthStr.split('-').map(Number);
  const lastDay = new Date(y, m, 0).getDate();
  const monthEnd = monthStr + '-' + String(lastDay).padStart(2, '0');
  // 如果 since 在月中（不是月初）或 until 在月中（不是月末），则该月数据不完整
  if (filterSince && filterSince > monthStart && filterSince <= monthEnd) return true;
  if (filterUntil && filterUntil >= monthStart && filterUntil < monthEnd) return true;
  return false;
}

// ── 初始化月份标签 ──

const tabsEl = document.getElementById('monthTabs');

const allTab = document.createElement('div');
allTab.className = 'month-tab active';
allTab.dataset.month = '';
allTab.textContent = '全部';
allTab.onclick = () => setMonth(null);
tabsEl.appendChild(allTab);

DATA.monthly.forEach(m => {
  const tab = document.createElement('div');
  tab.className = 'month-tab';
  tab.dataset.month = m.month;
  const partial = isPartialMonth(m.month);
  tab.textContent = m.month + (partial ? '（部分）' : '');
  tab.onclick = () => setMonth(m.month);
  tabsEl.appendChild(tab);
});

// ── 首次渲染 ──
setMonth(null);
</script>
</body>
</html>"""


# ── 跨平台打开文件 ───────────────────────────────────────

def _open_file(path):
    import platform
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", path], check=False)
    elif system == "Linux":
        subprocess.run(["xdg-open", path], check=False)
    elif system == "Windows":
        os.startfile(path)


# ── 生成 HTML ─────────────────────────────────────────────

def render_html(data):
    html = HTML_TEMPLATE
    html = html.replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False, default=str))
    return html


# ── Main ──────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Claude Code Token 用量统计 — HTML 仪表盘")
    p.add_argument("--since", type=str, help="起始日期 YYYY-MM-DD")
    p.add_argument("--until", type=str, help="截止日期 YYYY-MM-DD")
    p.add_argument("--no-open", action="store_true", help="生成 HTML 但不自动打开")
    p.add_argument("-o", "--output", type=str, help="输出文件路径（默认临时文件）")
    args = p.parse_args()

    since_dt = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    until_dt = datetime.strptime(args.until, "%Y-%m-%d").date() if args.until else None

    print("正在扫描会话文件...", file=sys.stderr, flush=True)
    files = find_jsonl_files()
    print(f"找到 {len(files)} 个文件，解析中...", file=sys.stderr, flush=True)

    records, total_sessions = scan_all(files, since_dt, until_dt)
    print(f"完成：{len(records)} 条消息", file=sys.stderr, flush=True)

    if not records:
        print("指定范围内无数据", file=sys.stderr)
        return

    data = prepare_data(records, total_sessions, since_dt, until_dt)
    html = render_html(data)

    if args.output:
        out_path = args.output
    else:
        out_path = os.path.join(tempfile.gettempdir(), "token-stats.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"报告已生成：{out_path}", file=sys.stderr)

    if not args.no_open:
        _open_file(out_path)


if __name__ == "__main__":
    main()
