"""
活动序列挖掘模块
从 weekly_daily.csv 学习每个子区域（路径）的工种演变规律。

核心思路：
  - 对每个子区域，按"首次活跃后的周数（age）"分组
  - 统计每个 age 段的工种分布（土建/钢结构/设备安装/装修）
  - 学习工种演变的典型先后顺序
  - 保存为 JSON 工件，供 predict_sequences.py 使用
"""
import os
import sys
import json
import numpy as np
import pandas as pd
from collections import defaultdict
from datetime import datetime

# 确保能引用项目内模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 工种分类列
CAT_COLS = ["cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修"]
CAT_LABELS = ["土建", "钢结构", "设备安装", "装修"]


def load_weekly_data(data_dir="data/processed"):
    """加载 P001 和 P003 的周级日报数据"""
    path = os.path.join(data_dir, "weekly_daily.csv")
    if not os.path.exists(path):
        # 尝试相对于 src 目录
        alt = os.path.join(os.path.dirname(__file__), "..", data_dir, "weekly_daily.csv")
        if os.path.exists(alt):
            path = alt
        else:
            raise FileNotFoundError(f"找不到 weekly_daily.csv: 尝试了 {path} 和 {alt}")

    df = pd.read_csv(path, encoding="utf-8-sig")
    df["week_start"] = pd.to_datetime(df["week_start"])
    return df


def _get_sub_cols(df):
    """获取所有子区域列（sub_前缀，排除衍生的统计列）"""
    skip = {"sub_count", "sub_diversity", "sub_entropy", "cum_sub_areas", "new_sub_areas"}
    return sorted([c for c in df.columns
                   if c.startswith("sub_") and c not in skip])


def _extract_sub_name(col):
    """从 sub_xxx 列名提取子区域中文名"""
    return col.replace("sub_", "")


def build_sub_work_profile(df):
    """
    为每个子区域构建工种演变画像。

    对每个子区域，在每个项目中：
      1. 找到该子区域首次活跃的周
      2. 按 age（距首次活跃的周数）分组
      3. 统计每组的工种分布

    返回:
        dict: {
            "子区域名": {
                "total_active_weeks": int,        # 所有项目中活跃的总周数
                "projects": [str],                 # 出现的项目列表
                "age_profile": {                    # 按 age 段的工种分布
                    "0-3": {"土建": 0.6, ...},
                    "4-8": {"土建": 0.4, ...},
                    ...
                },
                "overall_profile": {"土建": 0.4, ...},  # 总体分布
                "typical_sequence": ["土建", "钢结构", ...],  # 工种先后顺序
            },
            ...
        }
    """
    sub_cols = _get_sub_cols(df)
    work_profile = {}

    for col in sub_cols:
        sub_name = _extract_sub_name(col)
        # skip non-sub-area columns
        if not sub_name or sub_name in ("其他", "未分类"):
            continue

        # collect all active records for this sub-area
        all_ages = []  # (age, cat_dict)

        for proj in df["project_code"].unique():
            pdf = df[df["project_code"] == proj].sort_values("week_num").copy()
            if col not in pdf.columns or (pdf[col] > 0).sum() == 0:
                continue

            # 找首次活跃周
            active_mask = pdf[col] > 0
            first_idx = active_mask.idxmax() if active_mask.any() else None
            if first_idx is None:
                continue

            first_week_num = pdf.loc[first_idx, "week_num"]

            # 对每个活跃周，记录 age 和工种计数
            active_rows = pdf[active_mask]
            for _, row in active_rows.iterrows():
                age = int(row["week_num"] - first_week_num)
                cat_dict = {}
                for cat_col, label in zip(CAT_COLS, CAT_LABELS):
                    if cat_col in row.index:
                        cat_dict[label] = float(row[cat_col])
                all_ages.append((age, cat_dict))

        if not all_ages:
            continue

        # 按 age 分段统计工种分布
        age_groups = _define_age_groups(all_ages)
        age_profile = {}

        for group_name, (age_min, age_max) in age_groups.items():
            group_records = [r for age, r in all_ages if age_min <= age <= age_max]
            if not group_records:
                continue
            # 汇总该段所有记录的工种计数
            totals = defaultdict(float)
            for r in group_records:
                for label in CAT_LABELS:
                    totals[label] += r.get(label, 0)
            # 归一化
            total = sum(totals.values())
            if total > 0:
                age_profile[group_name] = {k: round(v / total, 3) for k, v in totals.items()}
            else:
                age_profile[group_name] = {k: 0.0 for k in CAT_LABELS}

        # 总体分布
        overall_totals = defaultdict(float)
        for _, r in all_ages:
            for label in CAT_LABELS:
                overall_totals[label] += r.get(label, 0)
        total = sum(overall_totals.values())
        overall_profile = {k: round(v / total, 3) for k, v in overall_totals.items()} if total > 0 else {k: 0.0 for k in CAT_LABELS}

        # 推断工种先后顺序
        typical_sequence = _infer_sequence(age_profile)

        # 首次/最后出现信息
        ages = [a for a, _ in all_ages]
        work_profile[sub_name] = {
            "total_active_weeks": len(all_ages),
            "projects": sorted(df[df[col] > 0]["project_code"].unique().tolist()),
            "min_age": int(min(ages)),
            "max_age": int(max(ages)),
            "median_age": int(np.median(ages)),
            "age_profile": age_profile,
            "overall_profile": overall_profile,
            "typical_sequence": typical_sequence,
        }

    return work_profile


def _define_age_groups(all_ages):
    """根据数据范围自动定义 age 分组"""
    ages = sorted([a for a, _ in all_ages])
    if not ages:
        return {}
    max_age = ages[-1]

    # 分段: 0-3, 4-8, 9-15, 16-25, 26-40, 41+
    # 根据实际 max_age 调整
    groups = {}
    boundaries = [3, 8, 15, 25, 40]
    prev = 0
    for i, b in enumerate(boundaries):
        if prev <= max_age:
            groups[f"{prev}-{b}"] = (prev, b)
        prev = b + 1
    # 最后一段到 max_age
    if prev <= max_age:
        groups[f"{prev}+"] = (prev, max_age)

    return groups


def _infer_sequence(age_profile):
    """
    从 age_profile 推断工种先后顺序。
    对每段取主导工种，去重后得到序列。
    """
    sequence = []
    seen = set()
    # 按 age 从小到大排序
    sorted_groups = sorted(age_profile.items(), key=lambda x: _parse_group_min(x[0]))

    for group_name, dist in sorted_groups:
        if not dist:
            continue
        # 找该段的主导工种
        dominant = max(dist, key=dist.get)
        if dominant not in seen and dist[dominant] > 0.25:
            sequence.append(dominant)
            seen.add(dominant)

    return sequence


def _parse_group_min(name):
    """解析 age 组名的最小值，如 '4-8' -> 4, '41+' -> 41"""
    try:
        return int(name.split("-")[0].rstrip("+"))
    except (ValueError, IndexError):
        return 999


def build_transition_stats(df):
    """
    跨项目统计子区域活跃的"持续/衰减"概率。
    给定子区域本周活跃，下周继续活跃的概率（persistence）。

    返回:
        dict: {子区域名: {"persistence": float, "typical_duration_weeks": int}, ...}
    """
    sub_cols = _get_sub_cols(df)
    stats = {}

    for col in sub_cols:
        sub_name = _extract_sub_name(col)
        if not sub_name:
            continue

        # per-project persistence stats for this sub-area
        persist_ratios = []
        total_active = 0
        total_consecutive_pairs = 0

        for proj in df["project_code"].unique():
            pdf = df[df["project_code"] == proj].sort_values("week_num")
            if col not in pdf.columns:
                continue
            series = pdf[col].values
            active = series > 0
            total_active += active.sum()

            # 连续活跃的对数
            for i in range(len(active) - 1):
                if active[i]:
                    total_consecutive_pairs += 1
                    if active[i + 1]:
                        persist_ratios.append(1)

        persistence = len(persist_ratios) / max(total_consecutive_pairs, 1)

        # 典型活跃持续周数（连续活跃的最大长度中位数）
        durations = []
        for proj in df["project_code"].unique():
            pdf = df[df["project_code"] == proj].sort_values("week_num")
            if col not in pdf.columns:
                continue
            series = pdf[col].values
            current_dur = 0
            for v in series:
                if v > 0:
                    current_dur += 1
                else:
                    if current_dur > 0:
                        durations.append(current_dur)
                    current_dur = 0
            if current_dur > 0:
                durations.append(current_dur)

        typical_dur = int(np.median(durations)) if durations else 0

        stats[sub_name] = {
            "persistence": round(persistence, 3),
            "typical_duration_weeks": typical_dur,
            "durations": durations,
        }

    return stats


def save_artifacts(work_profile, transition_stats, model_dir="models/sequences"):
    """保存所有序列模型工件"""
    os.makedirs(model_dir, exist_ok=True)

    # 子区域工种画像
    with open(os.path.join(model_dir, "sub_work_profile.json"), "w", encoding="utf-8") as f:
        json.dump(work_profile, f, ensure_ascii=False, indent=2)

    # 持续/衰减统计
    with open(os.path.join(model_dir, "transition_stats.json"), "w", encoding="utf-8") as f:
        json.dump(transition_stats, f, ensure_ascii=False, indent=2)

    # 元信息
    meta = {
        "trained_date": datetime.now().isoformat(),
        "n_sub_areas": len(work_profile),
        "sub_areas": sorted(work_profile.keys()),
    }
    with open(os.path.join(model_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"序列模型工件已保存到 {model_dir}/")
    print(f"  子区域数: {len(work_profile)}")
    print(f"  文件: sub_work_profile.json, transition_stats.json, meta.json")


def main():
    """挖掘并保存序列模型"""
    import argparse
    parser = argparse.ArgumentParser(description="活动序列挖掘")
    parser.add_argument("--data-dir", default="data/processed", help="周级数据目录")
    parser.add_argument("--model-dir", default=None, help="模型输出目录（默认 models/sequences）")
    args = parser.parse_args()

    # 模型目录
    if args.model_dir:
        model_dir = args.model_dir
    else:
        model_dir = os.path.join(os.path.dirname(__file__), "..", "models", "sequences")
    model_dir = os.path.abspath(model_dir)

    print("=" * 60)
    print("  活动序列挖掘")
    print("=" * 60)

    # 加载数据
    df = load_weekly_data(args.data_dir)
    print(f"\n数据: {len(df)} 周, {df['project_code'].nunique()} 个项目")
    print(f"项目: {sorted(df['project_code'].unique())}")

    # 子区域工种画像
    print("\n[1/2] 构建子区域工种演变画像...")
    work_profile = build_sub_work_profile(df)
    for sub_name, profile in sorted(work_profile.items()):
        seq_str = " → ".join(profile["typical_sequence"]) if profile["typical_sequence"] else "无"
        print(f"  {sub_name}: 活跃{profile['total_active_weeks']}周, 序列: {seq_str}")

    # 转移统计
    print("\n[2/2] 统计持续性...")
    trans_stats = build_transition_stats(df)
    for sub_name, stats in sorted(trans_stats.items()):
        if stats["persistence"] > 0:
            print(f"  {sub_name}: persistence={stats['persistence']}, typical_dur={stats['typical_duration_weeks']}周")

    # 保存
    save_artifacts(work_profile, trans_stats, model_dir)

    print("\n完成！")


if __name__ == "__main__":
    main()
