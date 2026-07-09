"""
下周预测接口

输入: 项目最近几周的日报周级数据 (weekly_daily.csv 格式)
输出: 下周的人员、机械、活动预测 + 工期基准评估

用法:
  python src/predict_forecast.py --project P003 -o 报告.txt
  python src/predict_forecast.py --input my_project.csv
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
import joblib
from datetime import timedelta

MODEL_DIR = r"D:\日报预测\models\forecast"
DATA_PATH = r"D:\日报预测\data\processed\weekly_daily.csv"

CONSTANT_EQUIPMENT = ["塔吊数量", "装载机数量"]

POST_RULES = {
    "日均施工人员": {"min": 0, "max_change_ratio": 0.3},
    "最大施工人员": {"min": 0, "max_change_ratio": 0.3},
    "塔吊数量":     {"min": 0, "max_change_abs": 0},
    "装载机数量":   {"min": 0, "max_change_abs": 1},
    "挖机数量":     {"min": 0, "max_change_abs": 2},
    "降雨天数":     {"min": 0, "max": 7},
    "每日施工条目数":{"min": 0, "max_change_ratio": 0.5},
    "每周施工条目数":{"min": 0, "max_change_ratio": 0.5},
    "土建活动频次": {"min": 0, "max_change_ratio": 0.5},
    "钢结构活动频次":{"min": 0, "max_change_ratio": 0.5},
    "设备安装活动频次":{"min": 0, "max_change_ratio": 0.5},
    "装修活动频次":{"min": 0, "max_change_ratio": 0.5},
}

BASE_FEATURES = [
    "week_num", "month_sin", "month_cos",
    "rain_days", "extreme_days", "avg_temp", "n_days",
    "avg_workers", "max_workers", "sub_count",
    "avg_excavator", "avg_crane", "avg_loader", "avg_mobile_crane",
    "total_equip", "avg_items_per_day", "total_items_week",
    "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
    "sub_diversity", "new_sub_areas", "sub_entropy", "cum_sub_areas",
]

# 各目标的 CV MAE（从训练报告加载，默认值作为兜底）
DEFAULT_CV_MAE = {
    "日均施工人员": 255, "最大施工人员": 237,
    "挖机数量": 1.8, "汽车吊数量": 6.0, "装载机数量": 1.0, "塔吊数量": 1.7,
    "机械设备总数": 9.0, "每日施工条目数": 9.4, "每周施工条目数": 70,
    "土建活动频次": 40, "钢结构活动频次": 18, "设备安装活动频次": 42,
    "装修活动频次": 5.0, "降雨天数": 1.5,
}


def load_models(model_dir=MODEL_DIR):
    pkl_files = [f for f in os.listdir(model_dir) if f.endswith(".pkl")]
    if not pkl_files:
        raise FileNotFoundError(f"{model_dir} 中未找到模型文件，请先运行 train_forecast.py")
    models = {}
    for f in sorted(pkl_files):
        name = f.rsplit("_", 2)[0]
        models[name] = joblib.load(os.path.join(model_dir, f))
    feat_path = os.path.join(model_dir, "feature_columns.txt")
    with open(feat_path, encoding="utf-8") as f:
        feature_cols = [l.strip() for l in f if l.strip()]
    print(f"加载 {len(models)} 个模型 ({len(feature_cols)} 个特征)")
    return models, feature_cols


def build_features(df):
    df = df.sort_values("week_num").copy()
    if "month" not in df.columns:
        df["month"] = pd.to_datetime(df["week_start"]).dt.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    lag_cols = ["avg_workers", "total_equip", "avg_items_per_day",
                "rain_days", "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
                "sub_diversity", "sub_entropy"]
    sub_cols = [c for c in df.columns if c.startswith("sub_")
                and c not in {"sub_count", "sub_diversity", "sub_entropy",
                               "cum_sub_areas", "new_sub_areas"}]
    lag_cols.extend(sub_cols)
    for col in lag_cols:
        if col in df.columns:
            df[f"{col}_lag1"] = df[col].shift(1)
            df[f"{col}_lag2"] = df[col].shift(2)
            df[f"{col}_lag3"] = df[col].shift(3)
            df[f"{col}_ma3"] = df[col].shift(1).rolling(3, min_periods=1).mean()
            df[f"{col}_ma5"] = df[col].shift(1).rolling(5, min_periods=1).mean()
    if "avg_workers" in df.columns:
        df["workers_trend"] = df["avg_workers"].shift(1) - df["avg_workers"].shift(2)
        df["workers_change_rate"] = (df["avg_workers"].shift(1) - df["avg_workers"].shift(2)) / (df["avg_workers"].shift(2) + 1)
    if "total_items_week" in df.columns:
        df["activity_trend"] = df["total_items_week"].shift(1) - df["total_items_week"].shift(2)
    if "total_equip" in df.columns:
        df["equip_trend"] = df["total_equip"].shift(1) - df["total_equip"].shift(2)
    activity_cols = ["cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修"]
    existing = [c for c in activity_cols if c in df.columns]
    if existing:
        df["total_activity"] = df[existing].sum(axis=1)
        for c in existing:
            df[f"{c}_ratio"] = df[c] / (df["total_activity"] + 1)
        if all(c in existing for c in ["cat_土建", "cat_设备安装", "cat_装修"]):
            df["stage_early_score"] = df["cat_土建"] / (df["total_activity"] + 1)
            df["stage_mid_score"] = df["cat_设备安装"] / (df["total_activity"] + 1)
            df["stage_late_score"] = df["cat_装修"] / (df["total_activity"] + 1)
            df["stage_transition"] = (
                (df["stage_late_score"].shift(1) - df["stage_late_score"].shift(3))
                - (df["stage_early_score"].shift(1) - df["stage_early_score"].shift(3))
            )
    return df


def predict_next_week(df, models, feature_cols):
    df = build_features(df)
    last = df.iloc[-1:].copy()
    this_week_data = df.iloc[-1]
    last["week_num"] = last["week_num"] + 1
    new_month = (pd.to_datetime(last["week_start"]) + timedelta(days=7)).dt.month.values[0]
    last["month"] = new_month
    last["month_sin"] = np.sin(2 * np.pi * new_month / 12)
    last["month_cos"] = np.cos(2 * np.pi * new_month / 12)
    for c in feature_cols:
        if c not in last.columns:
            last[c] = 0.0
    X = last[feature_cols].fillna(0).astype(float)

    predictions = {}
    en_to_cn = {
        "avg_excavator": "挖机数量", "avg_mobile_crane": "汽车吊数量",
        "avg_loader": "装载机数量", "avg_crane": "塔吊数量",
        "avg_workers": "日均施工人员", "max_workers": "最大施工人员",
        "total_equip": "机械设备总数",
        "avg_items_per_day": "每日施工条目数", "total_items_week": "每周施工条目数",
        "cat_土建": "土建活动频次", "cat_钢结构": "钢结构活动频次",
        "cat_设备安装": "设备安装活动频次", "cat_装修": "装修活动频次",
        "rain_days": "降雨天数",
    }

    for cn_name in CONSTANT_EQUIPMENT:
        en_name = {v: k for k, v in en_to_cn.items()}.get(cn_name)
        if en_name and en_name in this_week_data.index:
            predictions[cn_name] = round(float(this_week_data[en_name]), 1)

    for name, model in models.items():
        if name in predictions:
            continue
        try:
            pred = model.predict(X)[0]
            predictions[name] = round(float(pred), 1)
        except Exception:
            predictions[name] = None

    for name in predictions:
        if name not in POST_RULES or predictions[name] is None:
            continue
        rules = POST_RULES[name]
        val = predictions[name]
        if "min" in rules:
            val = max(val, rules["min"])
        if "max" in rules and "max" in rules:
            val = min(val, rules["max"])
        en_name = {v: k for k, v in en_to_cn.items()}.get(name)
        if en_name and en_name in this_week_data.index:
            last_val = this_week_data[en_name]
            if last_val > 0 and "max_change_ratio" in rules:
                max_change = last_val * rules["max_change_ratio"]
                val = max(val, last_val - max_change * 1.5)
                val = min(val, last_val + max_change * 1.5)
            elif "max_change_abs" in rules and last_val > 0:
                abs_max = rules["max_change_abs"]
                val = max(val, last_val - abs_max * 2)
                val = min(val, last_val + abs_max * 2)
        predictions[name] = round(float(val), 1)

    return predictions, last


def format_output(predictions, last_row, project_code):
    last_week = int(last_row["week_num"].values[0])
    last_date = pd.to_datetime(last_row["week_start"].values[0])
    next_date = last_date + timedelta(days=7)

    lines = []
    lines.append("=" * 65)
    lines.append(f"  项目 {project_code} 下周综合预测报告")
    lines.append(f"  基于第 {last_week-1} 周 ({last_date.date()})")
    lines.append(f"  预测第 {last_week} 周 ({next_date.date()} ~ {next_date.date() + timedelta(days=6)})")
    lines.append("=" * 65)

    lines.append(f"\n  {'='*40}")
    lines.append(f"  一、施工人员预测")
    lines.append(f"  {'='*40}")
    for k in ["日均施工人员", "最大施工人员"]:
        if k in predictions:
            mae = DEFAULT_CV_MAE.get(k, 250)
            lo = predictions[k] - mae
            hi = predictions[k] + mae
            lines.append(f"    {k}: {predictions[k]:.0f} 人  [区间 {lo:.0f} ~ {hi:.0f}]")

    lines.append(f"\n  {'='*40}")
    lines.append(f"  二、施工机械预测")
    lines.append(f"  {'='*40}")
    equip_keys = ["挖机数量", "汽车吊数量", "装载机数量", "塔吊数量", "机械设备总数"]
    for k in equip_keys:
        if k in predictions:
            tag = " [沿用上周]" if k in CONSTANT_EQUIPMENT else ""
            lines.append(f"    {k}: {predictions[k]:.1f} 台{tag}")

    lines.append(f"\n  {'='*40}")
    lines.append(f"  三、施工活动频次预测")
    lines.append(f"  {'='*40}")
    activity_keys = ["每日施工条目数", "每周施工条目数",
                     "土建活动频次", "钢结构活动频次", "设备安装活动频次", "装修活动频次"]
    for k in activity_keys:
        if k in predictions:
            lines.append(f"    {k}: {predictions[k]:.0f}")

    lines.append(f"\n  {'='*40}")
    lines.append(f"  四、天气预测")
    lines.append(f"  {'='*40}")
    if "降雨天数" in predictions:
        lines.append(f"    预计降雨: {predictions['降雨天数']:.0f} 天")

    bench = predictions.get("_benchmark")
    if bench:
        lines.append(f"\n  {'='*40}")
        lines.append(f"  五、工期基准评估（5个已完工项目对比）")
        lines.append(f"  {'='*40}")
        lines.append(f"    当前第 {bench['current_week']} 周 / 估算总工期 {bench['estimated_total_weeks']} 周")
        lines.append(f"    相对位置: {bench['relative_position']:.0%}")
        lines.append(f"    同位置已完工项目平均完成: {bench['benchmark_progress']:.0%}")
        lines.append(f"    范围: {bench['benchmark_range'][0]:.0%} ~ {bench['benchmark_range'][1]:.0%}")
        lines.append(f"    活动趋势: {bench['activity_trend']} | "
                     f"人员: {bench['workers_now']:.0f}人 (稳定性 {bench['workers_stability']:.0%})")
        lines.append(f"    综合评估: {bench['assessment']}")

    lines.append(f"\n{'='*65}")
    lines.append(f"  报告结束")
    lines.append(f"{'='*65}")
    return lines


def main():
    parser = argparse.ArgumentParser(description="下周预测")
    parser.add_argument("--project", "-p", help="项目代码 (P001/P003)")
    parser.add_argument("--input", "-i", help="自定义周级CSV文件")
    parser.add_argument("--weeks", "-w", type=int, default=4, help="使用最近几周")
    parser.add_argument("--data", default=DATA_PATH, help="周级数据路径")
    parser.add_argument("--output", "-o", help="输出文件路径")
    args = parser.parse_args()

    models, feature_cols = load_models()

    if args.input:
        df = pd.read_csv(args.input, encoding="utf-8-sig")
        if "week_start" in df.columns:
            df["week_start"] = pd.to_datetime(df["week_start"])
        proj = df["project_code"].iloc[0] if "project_code" in df.columns else "UNKNOWN"
    elif args.project:
        df = pd.read_csv(args.data, encoding="utf-8-sig")
        df["week_start"] = pd.to_datetime(df["week_start"])
        df = df[df["project_code"] == args.project]
        proj = args.project
    else:
        print("请指定 --project 或 --input")
        return

    if len(df) < 2:
        print(f"数据不足，至少需要2周")
        return

    df = df.sort_values("week_num").tail(args.weeks)
    print(f"输入: {proj}, {len(df)}周 (第{df['week_num'].min()}周 ~ 第{df['week_num'].max()}周)")

    predictions, last_row = predict_next_week(df, models, feature_cols)

    # 基准评估
    from benchmark import compare_to_benchmark, build_s_curve
    project_root = os.path.dirname(os.path.dirname(MODEL_DIR))
    gantt_path = os.path.join(project_root, "data", "processed", "weekly_gantt.csv")
    if os.path.exists(gantt_path):
        gantt_df = pd.read_csv(gantt_path, encoding="utf-8-sig")
        s_curve, _ = build_s_curve(gantt_df)
        full_daily = pd.read_csv(args.data, encoding="utf-8-sig")
        if "week_start" in full_daily.columns:
            full_daily["week_start"] = pd.to_datetime(full_daily["week_start"])
        bench = compare_to_benchmark(full_daily, proj, s_curve)
        predictions["_benchmark"] = bench

    lines = format_output(predictions, last_row, proj)
    report = "\n".join(lines)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"输出已保存: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
