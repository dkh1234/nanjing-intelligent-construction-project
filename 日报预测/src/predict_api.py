"""
预测接口 —— 供前端/其他系统调用

输入: 项目编号 (P001/P003) + 可选参数
输出: JSON 格式预测结果

用法:
  python src/predict_api.py --project P003           # 打印 JSON
  python src/predict_api.py --project P003 --json    # 仅 JSON
  python src/predict_api.py --list-projects           # 列出可用项目
"""
import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
import joblib
from datetime import timedelta


def _py(v):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "forecast")
DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "weekly_daily.csv")
GANTT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed", "weekly_gantt.csv")

CONSTANT_EQUIPMENT = ["塔吊数量", "装载机数量"]

CV_MAE = {
    "日均施工人员": 255, "最大施工人员": 237,
    "挖机数量": 1.8, "汽车吊数量": 6.0, "机械设备总数": 9.0,
    "每日施工条目数": 9.4, "每周施工条目数": 70,
    "土建活动频次": 40, "钢结构活动频次": 18, "设备安装活动频次": 42,
    "装修活动频次": 5.0, "降雨天数": 1.5,
}

EN_TO_CN = {
    "avg_excavator": "挖机数量", "avg_mobile_crane": "汽车吊数量",
    "avg_loader": "装载机数量", "avg_crane": "塔吊数量",
    "avg_workers": "日均施工人员", "max_workers": "最大施工人员",
    "total_equip": "机械设备总数",
    "avg_items_per_day": "每日施工条目数", "total_items_week": "每周施工条目数",
    "cat_土建": "土建活动频次", "cat_钢结构": "钢结构活动频次",
    "cat_设备安装": "设备安装活动频次", "cat_装修": "装修活动频次",
    "rain_days": "降雨天数",
}


def load_models():
    pkl_files = [f for f in os.listdir(MODEL_DIR) if f.endswith(".pkl")]
    models = {}
    for f in sorted(pkl_files):
        name = f.rsplit("_", 2)[0]
        models[name] = joblib.load(os.path.join(MODEL_DIR, f))
    feat_path = os.path.join(MODEL_DIR, "feature_columns.txt")
    with open(feat_path, encoding="utf-8") as f:
        feature_cols = [l.strip() for l in f if l.strip()]
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


def predict(project_code, weeks=4):
    """核心预测函数，返回 dict 可直接序列化为 JSON。"""
    # 加载
    models, feature_cols = load_models()
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["week_start"] = pd.to_datetime(df["week_start"])

    if project_code not in df["project_code"].values:
        return {"error": f"项目 {project_code} 不存在", "available": df["project_code"].unique().tolist()}

    proj_data = df[df["project_code"] == project_code].sort_values("week_num")
    if len(proj_data) < 2:
        return {"error": f"项目 {project_code} 数据不足（{len(proj_data)}周），至少需要2周"}

    recent = proj_data.tail(weeks).copy()
    df_feat = build_features(recent)

    last_row = df_feat.iloc[-1]
    next_week_num = int(last_row["week_num"]) + 1
    last_date = pd.to_datetime(last_row["week_start"])
    next_date = last_date + timedelta(days=7)

    # 构造预测输入
    last = last_row.to_frame().T.copy()
    last["week_num"] = next_week_num
    new_month = (next_date + timedelta(days=7)).month
    last["month"] = new_month
    last["month_sin"] = np.sin(2 * np.pi * new_month / 12)
    last["month_cos"] = np.cos(2 * np.pi * new_month / 12)
    for c in feature_cols:
        if c not in last.columns:
            last[c] = 0.0
    X = last[feature_cols].fillna(0).astype(float)

    # 预测
    predictions = {}
    for cn_name in CONSTANT_EQUIPMENT:
        en_name = {v: k for k, v in EN_TO_CN.items()}.get(cn_name)
        if en_name and en_name in last_row.index:
            predictions[cn_name] = round(float(last_row[en_name]), 1)

    for name, model in models.items():
        if name in predictions:
            continue
        try:
            predictions[name] = round(float(model.predict(X)[0]), 1)
        except Exception:
            predictions[name] = None

    # ---- 组装输出 ----
    result = {
        "project_code": project_code,
        "based_on_week": _py(last_row["week_num"]),
        "based_on_date": str(last_date.date()),
        "predict_week": _py(next_week_num),
        "predict_dates": f"{next_date.date()} ~ {next_date.date() + timedelta(days=6)}",
    }

    # 人员
    personnel = {}
    for k in ["日均施工人员", "最大施工人员"]:
        if k in predictions and predictions[k] is not None:
            mae = CV_MAE.get(k, 250)
            v = _py(predictions[k])
            personnel[k] = {
                "value": v,
                "unit": "人",
                "range": [_py(max(0, v - mae)), _py(v + mae)],
            }
    result["personnel"] = personnel

    # 机械
    equipment = {}
    for k in ["挖机数量", "汽车吊数量", "装载机数量", "塔吊数量", "机械设备总数"]:
        if k in predictions and predictions[k] is not None:
            equipment[k] = {
                "value": _py(predictions[k]),
                "unit": "台",
                "rule_based": k in CONSTANT_EQUIPMENT,
            }
    result["equipment"] = equipment

    # 活动
    activity = {}
    for k in ["每日施工条目数", "每周施工条目数",
              "土建活动频次", "钢结构活动频次", "设备安装活动频次", "装修活动频次"]:
        if k in predictions and predictions[k] is not None:
            activity[k] = {"value": _py(max(0, predictions[k])), "unit": "次"}
    result["activity"] = activity

    # 天气
    rain_val = predictions.get("降雨天数")
    if rain_val is not None:
        result["weather"] = {"rain_days": _py(max(0, min(7, int(rain_val))))}

    # 基准
    if os.path.exists(GANTT_PATH):
        sys.path.insert(0, os.path.dirname(__file__))
        from benchmark import compare_to_benchmark, build_s_curve
        gantt_df = pd.read_csv(GANTT_PATH, encoding="utf-8-sig")
        s_curve, _ = build_s_curve(gantt_df)
        bench = compare_to_benchmark(df, project_code, s_curve)
        result["benchmark"] = {
            "current_week": _py(bench["current_week"]),
            "estimated_total_weeks": _py(bench["estimated_total_weeks"]),
            "relative_position": _py(round(bench["relative_position"], 2)),
            "avg_completion": _py(round(bench["benchmark_progress"], 2)),
            "completion_range": [_py(round(bench["benchmark_range"][0], 2)), _py(round(bench["benchmark_range"][1], 2))],
            "activity_trend": bench["activity_trend"],
            "workers_stability": _py(round(bench["workers_stability"], 2)),
            "assessment": bench["assessment"],
        }

    return result


def list_projects():
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    projects = []
    for p in sorted(df["project_code"].unique()):
        pdata = df[df["project_code"] == p]
        projects.append({
            "code": p,
            "weeks": len(pdata),
            "date_range": [str(pdata["week_start"].min()), str(pdata["week_start"].max())],
        })
    return projects


def main():
    parser = argparse.ArgumentParser(description="预测 API")
    parser.add_argument("--project", "-p", help="项目代码")
    parser.add_argument("--weeks", "-w", type=int, default=4)
    parser.add_argument("--list-projects", action="store_true", help="列出可用项目")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON（不打印加载信息）")
    args = parser.parse_args()

    if args.list_projects:
        projects = list_projects()
        print(json.dumps(projects, ensure_ascii=False, indent=2))
        return

    if not args.project:
        print(json.dumps({"error": "请指定 --project 或 --list-projects"}, ensure_ascii=False))
        return

    # 预测（重定向 stderr 以屏蔽警告）
    import warnings
    warnings.filterwarnings("ignore")
    old_stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")

    result = predict(args.project, args.weeks)

    sys.stderr = old_stderr

    if not args.json:
        # 打印加载信息到 stderr（已屏蔽），只输出 JSON
        pass
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
