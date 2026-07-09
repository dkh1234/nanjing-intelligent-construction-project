"""
新数据验证脚本
用 P001 全部 + P003 旧数据训练，留出 P003 新周做验证
"""
import os, sys, warnings
import numpy as np
import pandas as pd
import joblib
from datetime import timedelta
from sklearn.metrics import mean_absolute_error

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from train_forecast import (TARGETS, TARGET_PARAM_GROUP, TARGET_PARAMS,
                             CONSTANT_EQUIPMENT, POST_RULES)

DATA_PATH = r"D:\日报预测\data\processed\weekly_daily.csv"
OUTPUT_FILE = r"D:\日报预测\validation_result.txt"

BASE_FEATURES = [
    "week_num", "month_sin", "month_cos",
    "rain_days", "extreme_days", "avg_temp", "n_days",
    "avg_workers", "max_workers", "sub_count",
    "avg_excavator", "avg_crane", "avg_loader", "avg_mobile_crane",
    "total_equip", "avg_items_per_day", "total_items_week",
    "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
]


def build_features(df):
    df = df.sort_values("week_num").copy()
    if "month" not in df.columns:
        df["month"] = pd.to_datetime(df["week_start"]).dt.month
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    lag_cols = ["avg_workers", "total_equip", "avg_items_per_day",
                "rain_days", "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修"]
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


def build_pairs(df):
    """本周→下周配对，与 train_forecast.py 一致"""
    df = build_features(df)
    pairs = []
    for proj in df["project_code"].unique():
        p = df[df["project_code"] == proj].sort_values("week_num")
        for i in range(len(p) - 1):
            tw = p.iloc[i]
            nw = p.iloc[i + 1]
            pair = {"project_code": proj, "week_num": int(tw["week_num"])}
            for c in BASE_FEATURES:
                if c in p.columns:
                    pair[c] = tw[c]
            for col in p.columns:
                if any(col.endswith(s) for s in ["_lag1","_lag2","_lag3","_ma3","_ma5","_trend","_rate","_ratio","_score","_transition"]):
                    pair[col] = tw[col]
            for cn, en in TARGETS.items():
                if en in p.columns:
                    pair[cn] = nw[en]
            pairs.append(pair)
    result = pd.DataFrame(pairs)
    feat_cols = [c for c in result.columns if c not in list(TARGETS.keys()) + ["project_code", "week_num"]]
    label_cols = [k for k in TARGETS.keys() if k in result.columns]
    return result, feat_cols, label_cols


def main():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["week_start"] = pd.to_datetime(df["week_start"])

    p003 = df[df["project_code"] == "P003"].sort_values("week_num")
    p001 = df[df["project_code"] == "P001"]

    print(f"P001: {len(p001)}周")
    print(f"P003: {len(p003)}周 (新增最后3周: 第{p003['week_num'].iloc[-3]}-{p003['week_num'].iloc[-1]}周)")
    print(f"  新周日期: {p003['week_start'].iloc[-3].date()} ~ {p003['week_start'].iloc[-1].date()}")
    print()

    # 训练集：P001全部 + P003前58周
    train_data = pd.concat([p001, p003.head(58)])
    pairs, feature_cols, label_cols = build_pairs(train_data)
    X_train = pairs[feature_cols].fillna(0)

    # 测试集：P003最后3周（用前4周特征预测）
    p003_full = build_features(p003)
    test_weeks = [59, 60, 61]

    from xgboost import XGBRegressor
    results = {}

    for cn_name in label_cols:
        # 恒定设备跳过训练
        if cn_name in CONSTANT_EQUIPMENT:
            continue

        y_train = pairs[cn_name]
        mask = y_train.notna()
        if mask.sum() < 10:
            continue

        param_group = TARGET_PARAM_GROUP.get(cn_name, "personnel")
        params = dict(TARGET_PARAMS[param_group])
        params["random_state"] = 42
        params["n_jobs"] = -1
        params["verbosity"] = 0

        model = XGBRegressor(**params)
        model.fit(X_train[mask], y_train[mask])

        # 恒定设备预测（直接取历史值）
        if cn_name in CONSTANT_EQUIPMENT:
            continue  # 用规则处理，后面统一加

        preds = []
        actuals = []
        for tw in test_weeks:
            hist = p003_full[p003_full["week_num"] < tw]
            if len(hist) < 2:
                continue
            feat_row = hist.iloc[-1:].copy()
            feat_row["week_num"] = tw
            new_month = pd.to_datetime(feat_row["week_start"]) + timedelta(days=7)
            feat_row["month"] = new_month.dt.month.values[0]
            feat_row["month_sin"] = np.sin(2 * np.pi * feat_row["month"] / 12)
            feat_row["month_cos"] = np.cos(2 * np.pi * feat_row["month"] / 12)

            X_test = feat_row[feature_cols].fillna(0)
            pred = model.predict(X_test)[0]

            # 后处理
            actual_row = p003_full[p003_full["week_num"] == tw]
            if len(actual_row) > 0:
                en_col = TARGETS[cn_name]
                actual = actual_row[en_col].values[0]

                # 对人员/活动做环比裁剪
                if cn_name in POST_RULES:
                    rules = POST_RULES[cn_name]
                    if "max_change_ratio" in rules and hist.iloc[-1][en_col] > 0:
                        cap = hist.iloc[-1][en_col] * (1 + rules["max_change_ratio"])
                        floor = hist.iloc[-1][en_col] * (1 - rules["max_change_ratio"])
                        pred = max(min(pred, cap), floor)
                    if "min" in rules:
                        pred = max(pred, rules["min"])
                    if "max" in rules and "max" in rules:
                        pred = min(pred, rules["max"])

                preds.append(pred)
                actuals.append(actual)

        if preds and actuals:
            mae = mean_absolute_error(actuals, preds)
            results[cn_name] = {
                "predictions": preds,
                "actuals": actuals,
                "mae": mae,
                "weeks": test_weeks[:len(preds)],
            }

    # 补充恒定设备的验证结果
    for cn_name in CONSTANT_EQUIPMENT:
        if cn_name not in TARGETS:
            continue
        en_col = TARGETS[cn_name]
        preds = []
        actuals = []
        for tw in test_weeks:
            hist = p003_full[p003_full["week_num"] < tw]
            actual_row = p003_full[p003_full["week_num"] == tw]
            if len(hist) > 0 and len(actual_row) > 0:
                preds.append(hist.iloc[-1][en_col])
                actuals.append(actual_row[en_col].values[0])
        if preds:
            mae = mean_absolute_error(actuals, preds)
            results[cn_name] = {
                "predictions": preds, "actuals": actuals,
                "mae": mae, "weeks": test_weeks[:len(preds)],
                "rule_based": True,
            }

        if preds and actuals:
            mae = mean_absolute_error(actuals, preds)
            results[cn_name] = {
                "predictions": preds,
                "actuals": actuals,
                "mae": mae,
                "weeks": test_weeks[:len(preds)],
            }

    # 输出
    lines = []
    lines.append("=" * 75)
    lines.append("  P003 新数据验证: 第59-61周 预测 vs 实际")
    lines.append("=" * 75)
    lines.append("")

    # 按类别分组
    categories = [
        ("施工人员", ["日均施工人员", "最大施工人员"]),
        ("施工机械", ["挖机数量", "汽车吊数量", "装载机数量", "塔吊数量", "机械设备总数"]),
        ("施工活动", ["每日施工条目数", "每周施工条目数", "土建活动频次", "钢结构活动频次", "设备安装活动频次", "装修活动频次"]),
        ("天气", ["降雨天数"]),
    ]

    for cat_name, keys in categories:
        lines.append(f"  [{cat_name}]")
        lines.append(f"  {'指标':<18} {'第59周':>10} {'第60周':>10} {'第61周':>10}  {'MAE':>10}")
        lines.append(f"  {'-'*58}")
        for k in keys:
            if k not in results:
                continue
            r = results[k]
            vals = []
            for i in range(3):
                if i < len(r["predictions"]):
                    vals.append(f'{r["predictions"][i]:>8.1f}')
                else:
                    vals.append(f'{">>":>8}')
            act_vals = []
            for i in range(3):
                if i < len(r["actuals"]):
                    act_vals.append(f'{r["actuals"][i]:>8.1f}')
                else:
                    act_vals.append(f'{">>":>8}')
            lines.append(f"  {k:<18} 预测 {vals[0]} {vals[1]} {vals[2]}  {r['mae']:>8.1f}" +
                         (" [规则]" if r.get("rule_based") else " [模型]"))
            lines.append(f"  {'':<18} 实际 {act_vals[0]} {act_vals[1]} {act_vals[2]}")
        lines.append("")

    n_model = sum(1 for r in results.values() if not r.get("rule_based"))
    n_rule = sum(1 for r in results.values() if r.get("rule_based"))
    lines.append(f"  模型预测: {n_model}项 | 规则直出: {n_rule}项 (恒定设备)")
    lines.append("=" * 75)

    output = "\n".join(lines)
    print(output)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(output)
    print(f"\n结果已保存: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
