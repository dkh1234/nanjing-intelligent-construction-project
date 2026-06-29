"""日报数据质量诊断 —— 一次性分析脚本"""
import pandas as pd
import numpy as np

DAILY_PATH = r"D:\日报预测\data\processed\weekly_daily.csv"
GANTT_PATH = r"D:\日报预测\data\processed\weekly_gantt.csv"

daily = pd.read_csv(DAILY_PATH, encoding="utf-8-sig")
gantt = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")

print("=" * 60)
print("日报周级数据质量报告")
print("=" * 60)

# 1. 基本统计
for proj in daily["project_code"].unique():
    p = daily[daily["project_code"] == proj]
    print(f"\n--- {proj}: {len(p)}周 ---")
    print(f"  日期: {p['week_start'].min()} ~ {p['week_start'].max()}")
    print(f"  每周天数: mean={p['n_days'].mean():.1f} (理想=7)")
    print(f"  降雨: {p['rain_days'].sum()}天, 降雨周比例={(p['rain_days']>0).mean():.1%}")
    print(f"  极端天气: {p['extreme_days'].sum()}天")
    print(f"  均温: {p['avg_temp'].mean():.1f}度 (min={p['avg_temp'].min():.0f}, max={p['avg_temp'].max():.0f})")
    print(f"  均人数: {p['avg_workers'].mean():.0f}人 (min={p['avg_workers'].min():.0f}, max={p['avg_workers'].max():.0f})")
    print(f"  零工人周: {(p['avg_workers'] == 0).sum()}")

# 2. 缺失值检查
print("\n--- 缺失值 ---")
for col in daily.columns:
    na = daily[col].isna().sum()
    if na > 0:
        print(f"  {col}: {na}/{len(daily)} ({na/len(daily):.1%})")

# 3. 施工活动多样性
print("\n--- 施工活动分布 ---")
cat_cols = [c for c in daily.columns if c.startswith("cat_")]
for col in cat_cols:
    nonzero = (daily[col] > 0).sum()
    print(f"  {col}: {nonzero}/{len(daily)}周有活动 ({nonzero/len(daily):.1%})")

# 4. 人员-机械相关性（日报内部验证）
print("\n--- 日报内部相关性 ---")
corr_cols = ["avg_workers", "avg_excavator", "avg_crane", "avg_items_per_day", "rain_days"]
corr = daily[corr_cols].corr()
print(corr.round(3))

# 5. 甘特图 vs 日报 数值范围对比
print("\n--- 甘特图 vs 日报 数值范围 ---")
print(f"  甘特图 active_tasks: {gantt['active_tasks'].mean():.0f} (范围 {gantt['active_tasks'].min():.0f}-{gantt['active_tasks'].max():.0f})")
print(f"  日报 avg_items_per_day: {daily['avg_items_per_day'].mean():.1f} (范围 {daily['avg_items_per_day'].min():.1f}-{daily['avg_items_per_day'].max():.1f})")
print(f"  日报 total_items_week: {daily['total_items_week'].mean():.1f}")
print(f"  甘特图 completed_this_week: {gantt['completed_this_week'].mean():.1f}")

print("\n" + "=" * 60)
print("报告结束。关键问题：")
print("1. 日报每周天数是否接近7？（日报应有连续记录）")
print("2. 天气/人力/机械数值是否合理范围？")
print("3. 施工活动覆盖面是否足够？")
print("4. 甘特图和日报的活跃度量级是否可比？")
print("=" * 60)
