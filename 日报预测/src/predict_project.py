"""
工期预测接口
加载训练好的模型，对新项目的周级特征逐周滚动预测，输出预计完工日期。

用法:
  python src/predict_project.py                          # 对已知项目做回测
  python src/predict_project.py --input new_project.csv  # 对新项目预测
"""
import os
import sys
import argparse
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

MODEL_DIR = r"D:\日报预测\models"


def load_latest_model(model_dir=MODEL_DIR):
    """加载最新的 XGBoost 模型和特征列表。"""
    pkl_files = [f for f in os.listdir(model_dir) if f.endswith(".pkl")]
    if not pkl_files:
        raise FileNotFoundError(f"{model_dir} 中未找到模型文件")
    latest = sorted(pkl_files)[-1]
    model = joblib.load(os.path.join(model_dir, latest))

    feat_path = os.path.join(model_dir, "feature_columns.txt")
    if os.path.exists(feat_path):
        with open(feat_path, encoding="utf-8") as f:
            features = [line.strip() for line in f if line.strip()]
    else:
        features = []

    print(f"模型: {latest}")
    print(f"特征数: {len(features)}")
    return model, features


def prepare_weekly_data(df, feature_cols):
    """
    对输入 DataFrame 做特征工程（与 train_model.build_features 对齐）。
    需包含列: project_code, week_num, weekly_progress(可选), cumulative_progress, month
    """
    from train_model import build_features
    df = df.sort_values(["project_code", "week_num"]).copy()

    # 确保必要列存在
    for c in ["weekly_progress", "cumulative_progress"]:
        if c not in df.columns:
            df[c] = 0.0
    if "month" not in df.columns:
        df["month"] = pd.to_datetime(df["week_start"]).dt.month

    df = build_features(df)

    # 补齐缺失特征
    for c in feature_cols:
        if c not in df.columns:
            df[c] = 0.0

    return df


def predict_duration(model, feature_cols, weekly_data, max_extra_weeks=50):
    """
    逐周滚动预测直到累计进度 >= 99%。

    参数:
        model: 训练好的模型
        feature_cols: 特征列名列表
        weekly_data: DataFrame，至少包含 feature_cols 中的特征 + week_num + cumulative_progress
        max_extra_weeks: 超出已有数据后最多预测周数

    返回:
        {predicted_weeks, final_cumulative, predictions_df}
    """
    df = prepare_weekly_data(weekly_data, feature_cols)

    if len(df) < 3:
        raise ValueError(f"至少需要3周数据来初始化lag特征, 当前{len(df)}周")

    # 用前3周初始化
    cum = df["cumulative_progress"].iloc[2]
    pred_weeks = 3
    predictions = []

    for i in range(3, len(df) + max_extra_weeks):
        if cum >= 0.99:
            break

        if i < len(df):
            row = df.iloc[i : i + 1][feature_cols].fillna(0)
        else:
            # 用最后一周特征外推
            row = df.iloc[-1:][feature_cols].copy()
            row["week_num"] = i + 1
            row["cumulative_progress"] = cum
            row["cum_sqrt"] = np.sqrt(max(cum, 0))
            row["cum_sq"] = cum ** 2
            row["remaining"] = max(1.0 - cum, 0)
            row = row.fillna(0)

        if row.isna().any().any():
            break

        pred = model.predict(row)[0]
        cum += max(pred, 0)
        pred_weeks += 1
        predictions.append({
            "week": i + 1,
            "predicted_progress": round(pred, 6),
            "cumulative": round(cum, 6),
        })

    return {
        "predicted_weeks": pred_weeks,
        "final_cumulative": round(cum, 4),
        "predictions": pd.DataFrame(predictions),
    }


def main():
    parser = argparse.ArgumentParser(description="工期预测")
    parser.add_argument("--input", "-i", help="新项目 CSV 文件路径")
    parser.add_argument("--model-dir", default=MODEL_DIR, help="模型目录")
    args = parser.parse_args()

    model, features = load_latest_model(args.model_dir)

    if args.input:
        df = pd.read_csv(args.input, encoding="utf-8-sig")
        if "week_start" in df.columns:
            df["week_start"] = pd.to_datetime(df["week_start"])
        for proj in df["project_code"].unique():
            proj_data = df[df["project_code"] == proj]
            result = predict_duration(model, features, proj_data)
            print(f"\n{proj}: 输入{len(proj_data)}周 → 预测完工{result['predicted_weeks']}周")
    else:
        # 默认：对已有数据做回测
        gantt_path = os.path.join(os.path.dirname(MODEL_DIR), "data", "processed", "weekly_gantt.csv")
        daily_path = os.path.join(os.path.dirname(MODEL_DIR), "data", "processed", "weekly_daily_labeled.csv")

        print("\n工期预测结果:")
        print(f"{'项目':<8} {'实际周数':<10} {'预测周数':<10} {'误差':<10} {'误差%':<10}")
        print("-" * 48)

        errors = []
        for path in [gantt_path, daily_path]:
            if not os.path.exists(path):
                continue
            df = pd.read_csv(path, encoding="utf-8-sig")
            if "week_start" in df.columns:
                df["week_start"] = pd.to_datetime(df["week_start"])
            for proj in sorted(df["project_code"].unique()):
                proj_data = df[df["project_code"] == proj]
                try:
                    result = predict_duration(model, features, proj_data)
                except ValueError as e:
                    print(f"  {proj:<8} (跳过: {e})")
                    continue
                actual = len(proj_data)
                error = result["predicted_weeks"] - actual
                errors.append(abs(error))
                print(f"  {proj:<8} {actual:<10} {result['predicted_weeks']:<10} "
                      f"{error:+d}周{'':>4} {error/actual*100:+.1f}%")

        if errors:
            print(f"\n工期预测 MAE: {np.mean(errors):.1f}周")


if __name__ == "__main__":
    main()
