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
import math
import numpy as np
import pandas as pd
import joblib
from datetime import timedelta

# 必须为整数的指标（人员、机械台数、活动频次、降雨天数）
_INTEGER_METRICS = {
    "日均施工人员", "最大施工人员",
    "挖机数量", "汽车吊数量", "装载机数量", "塔吊数量", "机械设备总数",
    "每日施工条目数", "每周施工条目数",
    "土建活动频次", "钢结构活动频次", "设备安装活动频次", "装修活动频次",
    "降雨天数",
}


def _ceil_int(v):
    """小数则向上取整，已经是整数则保持"""
    if v is None:
        return None
    v = float(v)
    if v == int(v):
        return int(v)
    return int(math.ceil(v))


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


def predict(project_code, weeks=4, last_day_text=""):
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
            v = float(last_row[en_name])
            predictions[cn_name] = _ceil_int(v)

    for name, model in models.items():
        if name in predictions:
            continue
        try:
            val = float(model.predict(X)[0])
            predictions[name] = _ceil_int(val) if name in _INTEGER_METRICS else round(val, 1)
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

    # 生成预测日报文本
    result["report_text"] = _generate_report_text(result, predictions, last_row, last_day_text)

    return result


# ---- CN 到 EN 列名映射（用于迭代预测构造合成行） ----
CN_TO_EN_COL = {
    "日均施工人员": "avg_workers", "最大施工人员": "max_workers",
    "挖机数量": "avg_excavator", "汽车吊数量": "avg_mobile_crane",
    "装载机数量": "avg_loader", "塔吊数量": "avg_crane",
    "机械设备总数": "total_equip",
    "每日施工条目数": "avg_items_per_day", "每周施工条目数": "total_items_week",
    "土建活动频次": "cat_土建", "钢结构活动频次": "cat_钢结构",
    "设备安装活动频次": "cat_设备安装", "装修活动频次": "cat_装修",
    "降雨天数": "rain_days",
}


def _predict_one(models, feature_cols, df, last_day_text=""):
    """核心单周预测（接收 build_features 后的 DataFrame），返回 result dict"""
    last_row = df.iloc[-1]
    next_week_num = int(last_row["week_num"]) + 1
    last_date = pd.to_datetime(last_row["week_start"])
    next_date = last_date + timedelta(days=7)

    last = last_row.to_frame().T.copy()
    last["week_num"] = next_week_num
    new_month = next_date.month
    last["month"] = new_month
    last["month_sin"] = np.sin(2 * np.pi * new_month / 12)
    last["month_cos"] = np.cos(2 * np.pi * new_month / 12)
    for c in feature_cols:
        if c not in last.columns:
            last[c] = 0.0
    X = last[feature_cols].fillna(0).astype(float)

    predictions = {}
    for cn_name in CONSTANT_EQUIPMENT:
        en_name = {v: k for k, v in EN_TO_CN.items()}.get(cn_name)
        if en_name and en_name in last_row.index:
            v = float(last_row[en_name])
            predictions[cn_name] = _ceil_int(v)

    for name, model in models.items():
        if name in predictions:
            continue
        try:
            val = float(model.predict(X)[0])
            predictions[name] = _ceil_int(val) if name in _INTEGER_METRICS else round(val, 1)
        except Exception:
            predictions[name] = None

    result = {
        "based_on_week": _py(last_row["week_num"]),
        "based_on_date": str(last_date.date()),
        "predict_week": _py(next_week_num),
        "predict_dates": f"{next_date.date()} ~ {next_date.date() + timedelta(days=6)}",
    }

    personnel = {}
    for k in ["日均施工人员", "最大施工人员"]:
        if k in predictions and predictions[k] is not None:
            mae = CV_MAE.get(k, 250)
            v = _py(predictions[k])
            personnel[k] = {
                "value": v, "unit": "人",
                "range": [_py(max(0, v - mae)), _py(v + mae)],
            }
    result["personnel"] = personnel

    equipment = {}
    for k in ["挖机数量", "汽车吊数量", "装载机数量", "塔吊数量", "机械设备总数"]:
        if k in predictions and predictions[k] is not None:
            equipment[k] = {
                "value": _py(predictions[k]), "unit": "台",
                "rule_based": k in CONSTANT_EQUIPMENT,
            }
    result["equipment"] = equipment

    activity = {}
    for k in ["每日施工条目数", "每周施工条目数",
              "土建活动频次", "钢结构活动频次", "设备安装活动频次", "装修活动频次"]:
        if k in predictions and predictions[k] is not None:
            activity[k] = {"value": _py(max(0, predictions[k])), "unit": "次"}
    result["activity"] = activity

    rain_val = predictions.get("降雨天数")
    if rain_val is not None:
        result["weather"] = {"rain_days": _py(max(0, min(7, int(rain_val))))}

    # 生成预测日报文本
    result["report_text"] = _generate_report_text(result, predictions, last_row, last_day_text)

    return result, predictions, next_week_num, next_date


def _generate_report_text(result, predictions, last_row, last_day_text=""):
    """根据预测结果生成符合原始日报格式的文本，以最后一天原文为模板"""
    date_str = result.get("predict_dates", "").split(" ~ ")[0]
    rain = result.get("weather", {}).get("rain_days", 0)

    # 天气描述
    if rain <= 1:
        weather_desc = "晴"
    elif rain <= 3:
        weather_desc = "多云"
    else:
        weather_desc = "阴有雨"

    # 如果有最后一天的原文，用它做模板只替换日期行
    if last_day_text:
        lines = last_day_text.split("\n")
        # 替换第一行（日期行）的日期和天气
        if lines:
            first = lines[0]
            # 替换日期: 2025-04-12 → 预测日期
            import re as _re
            old_date = _re.search(r"(\d{4}-\d{1,2}-\d{1,2})", first)
            if old_date:
                first = first.replace(old_date.group(1), date_str)
            # 替换天气
            old_weather = _re.search(r"（[^）]+）", first)
            if old_weather:
                first = first.replace(old_weather.group(0), f"（{weather_desc}）")
            lines[0] = first
        return "\n".join(lines)

    # 没有原文时用汇总数据生成
    avg_temp = float(last_row.get("avg_temp", 20)) if "avg_temp" in last_row.index else 20
    temp_low = max(-30, int(avg_temp - 5))
    temp_high = min(50, int(avg_temp + 5))

    lines = []
    lines.append(f"{date_str}（{weather_desc}），气温：{temp_low}°~{temp_high}°")

    personnel = result.get("personnel", {})
    avg_w = personnel.get("日均施工人员", {}).get("value", 0)
    max_w = personnel.get("最大施工人员", {}).get("value", 0)
    lines.append(f"一、施工人员：日均 {avg_w} 人，最多 {max_w} 人")

    equipment = result.get("equipment", {})
    equip_parts = []
    for name in ["挖机数量", "装载机数量", "汽车吊数量", "塔吊数量", "机械设备总数"]:
        if name in equipment:
            label = name.replace("数量", "")
            equip_parts.append(f"{label} {equipment[name]['value']} 台")
    lines.append(f"二、施工机械：{'，'.join(equip_parts)}")

    activity = result.get("activity", {})
    lines.append("三、施工情况：")
    act_categories = [
        ("土建活动频次", "土建"),
        ("钢结构活动频次", "钢结构"),
        ("设备安装活动频次", "设备安装"),
        ("装修活动频次", "装修"),
    ]
    idx = 1
    for key, label in act_categories:
        if key in activity:
            lines.append(f"{idx}.{label}活动：{activity[key]['value']} 次；")
            idx += 1

    daily_items = activity.get("每日施工条目数", {}).get("value", 0)
    weekly_items = activity.get("每周施工条目数", {}).get("value", 0)
    lines.append(f"每日施工条目数约 {daily_items} 条，本周预计总条目数约 {weekly_items} 条。")
    lines.append(f"四、天气情况：预计本周降雨 {rain} 天。")
    lines.append("五、备注：以上为基于历史数据的模型预测结果，仅供参考。")

    return "\n".join(lines)


def predict_from_dataframe(weekly_df, predict_weeks=1, last_day_text=""):
    """
    从周级DataFrame直接预测（不读CSV）。

    参数:
        weekly_df: process_daily 输出的 DataFrame，需含 project_code, week_num, week_start 及所有特征列
        predict_weeks: 预测未来几周（1-4）
        last_day_text: 最后一天日报原文，用于生成预测日报文本

    返回: {"weeks": [...]}
    """
    models, feature_cols = load_models()
    df = weekly_df.copy()
    df["week_start"] = pd.to_datetime(df["week_start"])
    df = df.sort_values("week_num")

    if len(df) < 4:
        raise RuntimeError(f"数据不足（{len(df)}周），至少需要4周")

    # 补全可能缺失的列
    for c in feature_cols:
        if c not in df.columns:
            df[c] = 0.0

    results = []
    current_df = df.copy()

    for i in range(min(predict_weeks, 4)):
        # 用最近4周做特征
        recent = current_df.tail(4).copy()
        df_feat = build_features(recent)

        # 补全特征列
        for c in feature_cols:
            if c not in df_feat.columns:
                df_feat[c] = 0.0

        result, preds, next_week_num, next_date = _predict_one(
            models, feature_cols, df_feat, last_day_text if i == 0 else ""
        )
        results.append(result)

        # 构造下一周的合成行，用于迭代预测
        if i < predict_weeks - 1:
            synthetic = {}
            last_real = current_df.iloc[-1].to_dict()

            # 基本列
            synthetic["week_num"] = next_week_num
            synthetic["week_start"] = next_date
            synthetic["week_end"] = next_date + timedelta(days=6)
            synthetic["month"] = next_date.month
            synthetic["project_code"] = last_real.get("project_code", "UPLOAD")

            # 预测覆盖的列
            for cn_name, en_col in CN_TO_EN_COL.items():
                if cn_name in preds and preds[cn_name] is not None:
                    synthetic[en_col] = float(preds[cn_name])

            # 未预测到的列从上一周继承
            inherit_cols = ["n_days", "extreme_days", "avg_temp",
                          "sub_count", "sub_diversity", "sub_entropy",
                          "cum_sub_areas", "new_sub_areas"]
            for col in inherit_cols:
                if col in last_real:
                    synthetic[col] = last_real[col]

            # sub_ 子项列继承
            for col in current_df.columns:
                if col.startswith("sub_") and col not in synthetic:
                    synthetic[col] = last_real.get(col, 0)

            # 确保所有特征列存在
            for c in feature_cols:
                if c not in synthetic:
                    synthetic[c] = 0.0

            synthetic["new_sub_areas"] = 0
            synthetic["weekly_progress"] = None
            synthetic["cumulative_progress"] = None

            new_row = pd.DataFrame([synthetic])
            current_df = pd.concat([current_df, new_row], ignore_index=True)

    return {"weeks": results}


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
