"""
甘特图工期基准模块

用5个已完工甘特图项目构建S曲线基准，评估当前项目的进度位置。
输出: "你在第X周/占总工期~Y%，同阶段项目通常完成Z%，你当前完成~W%"
"""
import os
import numpy as np
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GANTT_PATH = os.path.join(_ROOT, "data", "processed", "weekly_gantt.csv")
DAILY_PATH = os.path.join(_ROOT, "data", "processed", "weekly_daily.csv")


# ============================================================
# 1. 构建 S 曲线基准
# ============================================================

def build_s_curve(gantt_df):
    """
    将5个甘特图项目的累计进度按相对位置插值对齐，计算每个位置的基准线。
    返回: DataFrame, 每行一个相对位置(5%步长)，含 P25/中位数/P75
    """
    grid = np.linspace(0.0, 1.0, 21)  # 0%, 5%, 10%, ..., 100%
    all_curves = {}

    for proj in gantt_df["project_code"].unique():
        p = gantt_df[gantt_df["project_code"] == proj].sort_values("week_num")
        if len(p) < 10:
            continue

        # 相对位置
        total_weeks = p["week_num"].max()
        p_rel = p["week_num"].values / total_weeks
        p_cum = p["cumulative_progress"].values

        # 插值到统一网格
        interp = np.interp(grid, p_rel, p_cum, left=0.0, right=p_cum[-1])
        all_curves[proj] = interp

    curves_df = pd.DataFrame(all_curves, index=grid)
    curves_df.index.name = "relative_position"

    # 统计 + 各项目列
    result = pd.DataFrame({
        "相对位置": grid,
        "基准中位数": curves_df.median(axis=1),
        "基准P25": curves_df.quantile(0.25, axis=1),
        "基准P75": curves_df.quantile(0.75, axis=1),
        "最小值": curves_df.min(axis=1),
        "最大值": curves_df.max(axis=1),
    })
    for proj in curves_df.columns:
        result[proj] = curves_df[proj].values

    return result, curves_df


# ============================================================
# 2. 估算当前项目的总工期
# ============================================================

def estimate_total_weeks(daily_df, project_code):
    """根据日报项目的活动模式估算总工期（周）。"""
    proj = daily_df[daily_df["project_code"] == project_code].sort_values("week_num")
    current_week = proj["week_num"].max()

    # 方法1: 甘特图项目平均工期
    gantt = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")
    gantt_avg = gantt.groupby("project_code")["week_num"].max().median()

    # 方法2: 根据人员/活动趋势判断阶段
    if "total_items_week" in proj.columns:
        recent_activity = proj["total_items_week"].tail(4).mean()
        peak_activity = proj["total_items_week"].max()

        if peak_activity > 0 and recent_activity > peak_activity * 0.7:
            # 活动还在高峰期 → 可能还有 30-50% 剩余
            stage_factor = 1.5
        elif recent_activity > peak_activity * 0.3:
            # 活动中等 → 约在中期偏后
            stage_factor = 1.3
        else:
            # 活动低 → 可能在收尾
            stage_factor = 1.1
    else:
        stage_factor = 1.3

    # 综合估算
    estimated = max(current_week + 4, current_week * stage_factor)
    estimated = min(estimated, gantt_avg * 1.5)  # 不超过甘特图均值的1.5倍

    return int(estimated)


# ============================================================
# 3. 对比分析
# ============================================================

def compare_to_benchmark(daily_df, project_code, s_curve):
    """
    将指定项目与基准对比，输出评估报告。

    返回: dict
        - current_week: 当前周数
        - estimated_total: 估算总工期（周）
        - relative_position: 相对位置
        - benchmark_progress: 同阶段应有进度
        - activity_level: 近4周活动量
        - activity_trend: 上升/平稳/下降
        - assessment: 快/正常/慢
    """
    proj = daily_df[daily_df["project_code"] == project_code].sort_values("week_num")
    current_week = proj["week_num"].max()
    estimated_total = estimate_total_weeks(daily_df, project_code)
    rel_pos = min(current_week / estimated_total, 1.0)

    # 查找最近的基准点
    closest = s_curve.iloc[(s_curve["相对位置"] - rel_pos).abs().argsort()[:1]]
    closest_pos = float(closest["相对位置"].values[0])
    benchmark = float(closest["基准中位数"].values[0])
    p25 = float(closest["基准P25"].values[0])
    p75 = float(closest["基准P75"].values[0])

    # 各已完工项目在同位置的完成百分比
    aggregate_cols = ["相对位置", "基准中位数", "基准P25", "基准P75", "最小值", "最大值"]
    project_names = [c for c in s_curve.columns if c not in aggregate_cols]
    per_project = {}
    for pname in project_names:
        per_project[pname] = float(closest[pname].values[0])

    # 活动趋势
    if "total_items_week" in proj.columns:
        recent = proj["total_items_week"].tail(4)
        if len(recent) >= 4:
            first2, last2 = recent.head(2).mean(), recent.tail(2).mean()
            if last2 > first2 * 1.15:
                trend = "上升"
            elif last2 < first2 * 0.85:
                trend = "下降"
            else:
                trend = "平稳"
        else:
            trend = "数据不足"
        activity_level = recent.mean()
        peak = proj["total_items_week"].max()
        activity_vs_peak = recent.mean() / peak if peak > 0 else 0
    else:
        trend = "无数据"
        activity_level = 0
        activity_vs_peak = 0

    # 评估（基于甘特图历史模式）
    if rel_pos < 0.15:
        assessment = "项目早期，参考价值有限"
    elif activity_vs_peak > 0.7 and rel_pos < 0.6:
        assessment = "施工高峰期，进度正常"
    elif activity_vs_peak < 0.4 and rel_pos > 0.7:
        assessment = "活动量下降，可能在收尾阶段"
    elif trend == "下降" and activity_vs_peak < 0.5:
        assessment = "活动减速，关注是否滞后"
    elif trend == "上升":
        assessment = "活动加速，进度追赶中"
    else:
        assessment = "进度平稳推进"

    # 人员稳定度
    if "avg_workers" in proj.columns:
        recent_w = proj["avg_workers"].tail(4)
        workers_now = recent_w.mean()
        workers_stability = 1 - (recent_w.std() / (recent_w.mean() + 1)) if recent_w.mean() > 0 else 0
    else:
        workers_now = 0
        workers_stability = 0

    return {
        "project_code": project_code,
        "current_week": current_week,
        "estimated_total_weeks": estimated_total,
        "relative_position": rel_pos,
        "closest_benchmark_position": closest_pos,
        "benchmark_progress": benchmark,
        "benchmark_range": (p25, p75),
        "per_project": per_project,
        "activity_level": activity_level,
        "activity_trend": trend,
        "activity_vs_peak": activity_vs_peak,
        "workers_now": workers_now,
        "workers_stability": workers_stability,
        "assessment": assessment,
    }


# ============================================================
# 4. 输出报告
# ============================================================

def print_report(results):
    """打印多项目对比报告。"""
    print("=" * 70)
    print("  工期基准评估报告")
    print("=" * 70)

    for r in results:
        proj = r["project_code"]
        print(f"\n  ── {proj} ──")
        print(f"  当前第 {r['current_week']} 周 / 估算总工期 {r['estimated_total_weeks']} 周 "
              f"(相对位置 {r['relative_position']:.0%})")
        print(f"  同位置甘特图基准: 应完成 {r['benchmark_progress']:.0%} "
              f"(范围 {r['benchmark_range'][0]:.0%} ~ {r['benchmark_range'][1]:.0%})")
        print(f"  近4周活动量: {r['activity_level']:.0f} 条/周 (趋势: {r['activity_trend']})")
        print(f"  当前人员: {r['workers_now']:.0f} 人 (稳定性: {r['workers_stability']:.0%})")
        print(f"  评估: {r['assessment']}")

    print(f"\n{'='*70}")


def print_s_curve_table(s_curve):
    """打印S曲线基准表。"""
    print(f"\n  S曲线基准 (5个已完工项目)")
    print(f"  {'相对位置':<10} {'P25':>8} {'中位数':>8} {'P75':>8}")
    print(f"  {'-'*35}")
    for _, row in s_curve.iterrows():
        print(f"  {row['相对位置']:<10.0%} {row['基准P25']:>8.1%} "
              f"{row['基准中位数']:>8.1%} {row['基准P75']:>8.1%}")


# ============================================================
# 5. 主入口
# ============================================================

def main():
    # 构建基准
    print("[1] 构建甘特图 S曲线基准...")
    gantt = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")
    s_curve, all_curves = build_s_curve(gantt)
    print_s_curve_table(s_curve)

    # 对比日报项目
    print("\n[2] 对比当前项目...")
    daily = pd.read_csv(DAILY_PATH, encoding="utf-8-sig")

    results = []
    for proj in ["P001", "P003"]:
        r = compare_to_benchmark(daily, proj, s_curve)
        results.append(r)

    print_report(results)

    # 保存
    out = os.path.join(os.path.dirname(GANTT_PATH), "benchmark.csv")
    s_curve.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n  基准表: {out}")


if __name__ == "__main__":
    main()
