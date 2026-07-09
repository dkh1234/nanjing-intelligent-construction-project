"""工具函数：日期解析、文本清洗、聚合计算。"""
import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# ---- 日期与时间 ----

def parse_date(text):
    """从文本中提取日期，支持多种格式。"""
    patterns = [
        r"(\d{4})-(\d{1,2})-(\d{1,2})",  # 2025-04-12 / 2025-4-12
        r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        r"(\d{4})/(\d{1,2})/(\d{1,2})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                return datetime(y, mo, d)
            except ValueError:
                pass
    return None


def week_boundaries(dt):
    """返回日期所在周的周一和周日。"""
    mon = dt - timedelta(days=dt.weekday())
    sun = mon + timedelta(days=6)
    return mon.date(), sun.date()


def generate_weeks(start, end):
    """生成从 start 到 end 的每周一列表。"""
    mon = start - timedelta(days=start.weekday())
    last = end - timedelta(days=end.weekday())
    return pd.date_range(mon, last, freq="W-MON")


# ---- 温度解析 ----

def parse_temperature(text):
    """从文本中提取最低/最高气温。"""
    # 匹配: "气温：-3°~13°" 或 "气温9°～ 19°" 或 "气温3℃～21℃"
    pat = r"气温[：:\s]*(-?\d{1,2})\s*[°℃～~\-]+\s*(-?\d{1,2})\s*[°℃]?"
    m = re.search(pat, text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # 单温度格式
    pat2 = r"气温[：:\s]*(-?\d{1,2})\s*[°℃]"
    m2 = re.search(pat2, text)
    if m2:
        t = int(m2.group(1))
        return t, t
    return None, None


# ---- 天气判断 ----

RAIN_KEYWORDS = ["雨", "雪", "霾", "雾"]
EXTREME_KEYWORDS = ["暴雨", "大风", "台风", "红色预警", "地质灾害", "撤离", "暂停施工"]


def is_rainy(text):
    return any(kw in text for kw in RAIN_KEYWORDS)


def is_extreme(text):
    return any(kw in text for kw in EXTREME_KEYWORDS)


# ---- 数字提取 ----

def extract_numbers(text):
    """提取文本中所有整数。"""
    return [int(m) for m in re.findall(r"(\d+)", text)]


# ---- 滚动计算（项目内分组） ----

def rolling_within_group(df, col, window, func="mean"):
    """在 project_code 分组内计算滚动特征，自动滞后1期防泄漏。"""
    def _roll(series):
        shifted = series.shift(1)
        roll = shifted.rolling(window, min_periods=1)
        return roll.mean() if func == "mean" else roll.sum()
    return df.groupby("project_code")[col].transform(_roll)


# ---- 数据校验 ----

def validate_weekly_df(df, name=""):
    """检查周级DataFrame的质量。"""
    issues = []
    if df["project_code"].nunique() < 2:
        issues.append("项目数 < 2")
    if df["weekly_progress"].isna().any():
        issues.append("标签存在NaN")
    if (df["weekly_progress"] < 0).any():
        issues.append("标签存在负值")
    for proj, grp in df.groupby("project_code"):
        if grp["week_num"].diff().dropna().max() > 2:
            issues.append(f"{proj}: week_num不连续")
    if issues:
        print(f"  [{name}] 数据问题: {', '.join(issues)}")
    else:
        print(f"  [{name}] 校验通过 ({len(df)}行, {df['project_code'].nunique()}项目)")
    return len(issues) == 0
