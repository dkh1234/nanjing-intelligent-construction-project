"""逐项目/逐周误差分析 —— 理解当前模型弱点"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import sys
sys.path.insert(0, "src")
from train_model import build_features, GANTT_FEATURES

GANTT_PATH = r"D:\日报预测\data\processed\weekly_gantt.csv"

df = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")
df["week_start"] = pd.to_datetime(df["week_start"])
df = build_features(df)

print("=" * 60)
print("甘特图项目特征分布分析")
print("=" * 60)

# 1. 每个项目的进度曲线形态
for proj, grp in df.groupby("project_code"):
    p = grp.sort_values("week_num")
    print(f"\n--- {proj}: {len(p)}周 ---")
    print(f"  周均进度: {p['weekly_progress'].mean():.4f}")
    print(f"  进度标准差: {p['weekly_progress'].std():.4f}")
    print(f"  零进度周: {(p['weekly_progress']==0).sum()} ({(p['weekly_progress']==0).mean():.1%})")
    max_idx = p['weekly_progress'].idxmax()
    max_week = p.loc[max_idx, 'week_num'] if pd.notna(max_idx) else '?'
    print(f"  最大单周: {p['weekly_progress'].max():.4f} (第{max_week}周)")
    print(f"  active_tasks均值: {p['active_tasks'].mean():.1f}")
    print(f"  前10周均值 vs 后10周均值: "
          f"{p['weekly_progress'].head(10).mean():.4f} vs {p['weekly_progress'].tail(10).mean():.4f}")
    # S曲线形态：累计进度达25%/50%/75%时的周数
    c = p["cumulative_progress"]
    for pct_val in [0.25, 0.50, 0.75]:
        if c.max() >= pct_val:
            week_at = p[c >= pct_val]["week_num"].min()
            print(f"  达{pct_val:.0%}进度: 第{week_at}周 ({week_at/len(p):.1%}位置)")

# 2. 项目间特征差异
print("\n--- 项目间特征变异系数 ---")
feat_cols = [c for c in GANTT_FEATURES if c in df.columns]
for col in feat_cols:
    proj_means = df.groupby("project_code")[col].mean()
    cv = proj_means.std() / (proj_means.mean() + 1e-8)
    if abs(cv) > 0.5:  # 高变异特征
        print(f"  {col}: CV={cv:.2f} (各项目均值: {proj_means.round(3).to_dict()})")

# 3. 项目间相似度
print("\n--- 项目间特征欧氏距离 ---")
feat_data = df[feat_cols].fillna(0)
scaler = StandardScaler().fit(feat_data)
scaled = scaler.transform(feat_data)
proj_ids = df["project_code"].values
distances = []
for proj_a in df["project_code"].unique():
    mask_a = proj_ids == proj_a
    centroid_a = scaled[mask_a].mean(axis=0)
    for proj_b in df["project_code"].unique():
        if proj_a >= proj_b:
            continue
        mask_b = proj_ids == proj_b
        centroid_b = scaled[mask_b].mean(axis=0)
        dist = np.linalg.norm(centroid_a - centroid_b)
        distances.append((proj_a, proj_b, dist))
for a, b, d in sorted(distances, key=lambda x: x[2]):
    print(f"  {a} <-> {b}: {d:.2f}")

print("\n" + "=" * 60)
print("报告结束。关键问题：")
print("1. 哪个项目的进度模式最特殊？（可能是最难预测的）")
print("2. 哪些特征在项目间变异最大？（可能是项目特有而非通用的）")
print("3. 哪些项目对最相似？（合并训练可能效果好）")
print("=" * 60)
