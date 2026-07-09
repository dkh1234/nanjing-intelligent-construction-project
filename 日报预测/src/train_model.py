"""
模型训练模块
- 主训练数据: weekly_gantt.csv (5项目, 有标签 weekly_progress)
- 补充数据:   weekly_daily.csv (2项目, 无标签, 仅用于预测)
- 验证方法:   GroupKFold Leave-One-Project-Out (5折)
- 预测目标:   每周进度增量 → 滚动累计 → 预计完工日期
"""
import os
import warnings
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta

from sklearn.model_selection import GroupKFold
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

warnings.filterwarnings("ignore")

RANDOM_STATE = 42


# ============================================================
# 1. 特征工程
# ============================================================

def build_features(df):
    """
    构造训练特征。

    重要约束：所有特征必须在预测时点可用（无未来信息泄漏）。
    lag/rolling 特征使用 shift(1) 确保只用历史数据。
    """
    df = df.sort_values(["project_code", "week_num"]).copy()

    # ---- 时间编码 ----
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # ---- S曲线形态: 进度位置的非线性变换 ----
    df["cum_sqrt"] = np.sqrt(df["cumulative_progress"].clip(0, 1))
    df["cum_sq"] = df["cumulative_progress"].clip(0, 1) ** 2
    df["remaining"] = (1.0 - df["cumulative_progress"]).clip(0, 1)

    # ---- 任务密度（仅甘特图有） ----
    if "active_tasks" in df.columns:
        df["new_start_rate"] = df["new_starts"] / (df["active_tasks"] + 1)
        df["overdue_rate"] = df["overdue_tasks"] / (df["active_tasks"] + 1)
        df["work_per_task"] = df["total_remaining_work"] / (df["active_tasks"] + 1)

    # ---- 历史滞后特征（项目内分组，无泄漏） ----
    for lag in [1, 2, 3]:
        col = f"progress_lag{lag}"
        df[col] = df.groupby("project_code")["weekly_progress"].shift(lag)

    df["progress_ma3"] = df.groupby("project_code")["weekly_progress"].transform(
        lambda x: x.shift(1).rolling(3, min_periods=1).mean()
    )
    df["progress_ma5"] = df.groupby("project_code")["weekly_progress"].transform(
        lambda x: x.shift(1).rolling(5, min_periods=1).mean()
    )
    df["progress_trend"] = df["progress_lag1"] - df["progress_lag2"]

    # ---- 交互 ----
    if "work_per_task" in df.columns:
        df["pressure"] = df["total_remaining_work"] * df["overdue_rate"]
        df["momentum"] = df["new_starts"] * df["progress_ma3"].fillna(0)

    return df


# ---- 特征列定义 ----

# 甘特图可用特征（有标签训练用）
GANTT_FEATURES = [
    "week_num", "month_sin", "month_cos",
    "cumulative_progress", "cum_sqrt", "cum_sq", "remaining",
    "active_tasks", "new_starts", "overdue_tasks",
    "new_start_rate", "overdue_rate", "work_per_task",
    "delay_ratio_to_date", "avg_task_dur",
    "completed_this_week", "total_remaining_work",
    "progress_lag1", "progress_lag2", "progress_lag3",
    "progress_ma3", "progress_ma5", "progress_trend",
    "pressure", "momentum",
]

# 日报可用特征（无标签预测用, 是甘特图特征的子集 + 日报独有特征）
DAILY_FEATURES = [
    "week_num", "month_sin", "month_cos",
    "n_days", "rain_days", "extreme_days", "avg_temp",
    "avg_workers", "max_workers", "sub_count",
    "avg_excavator", "avg_crane", "avg_loader", "avg_mobile_crane", "total_equip",
    "avg_items_per_day", "total_items_week",
    "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
]


# ============================================================
# 2. 训练与交叉验证
# ============================================================

def _clone(model):
    return type(model)(**model.get_params())


def cross_validate(X, y, groups, model, n_splits=5):
    """GroupKFold 交叉验证。"""
    gkf = GroupKFold(n_splits=n_splits)
    folds = []
    y_hat = np.zeros(len(y))
    importances = []

    for fold, (tr_idx, te_idx) in enumerate(gkf.split(X, y, groups)):
        X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
        y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]
        test_proj = groups.iloc[te_idx].unique()

        m = _clone(model)
        m.fit(X_tr, y_tr)
        pred = m.predict(X_te)
        y_hat[te_idx] = pred

        folds.append({
            "fold": fold + 1,
            "test_project": ",".join(test_proj),
            "n": len(y_te),
            "mae": mean_absolute_error(y_te, pred),
            "rmse": np.sqrt(mean_squared_error(y_te, pred)),
            "r2": r2_score(y_te, pred),
        })

        if hasattr(m, "feature_importances_"):
            importances.append(m.feature_importances_)

        print(f"    Fold{fold+1} [{test_proj[0]}]: MAE={folds[-1]['mae']:.4f}  "
              f"RMSE={folds[-1]['rmse']:.4f}  R2={folds[-1]['r2']:.4f}")

    scores = pd.DataFrame(folds)
    avg_imp = np.mean(importances, axis=0) if importances else None

    return {
        "scores": scores,
        "mean_mae": scores["mae"].mean(),
        "std_mae": scores["mae"].std(),
        "mean_rmse": scores["rmse"].mean(),
        "mean_r2": scores["r2"].mean(),
        "overall_mae": mean_absolute_error(y, y_hat),
        "overall_r2": r2_score(y, y_hat),
        "y_pred": y_hat,
        "feature_importance": avg_imp,
    }


def train_final(model, X, y):
    m = _clone(model)
    m.fit(X, y)
    return m


# ============================================================
# 3. 工期预测模拟
# ============================================================

def simulate_project(model, df, project_code, feature_cols, max_extra_weeks=30):
    """
    对单个项目进行工期预测模拟：
    从前3周开始，逐周滚动预测进度增量，直到累计≥99%。
    """
    proj = df[df["project_code"] == project_code].sort_values("week_num").copy()

    if len(proj) <= 3:
        return None

    # 用前3周初始化
    start_idx = 3
    cum = proj["cumulative_progress"].iloc[start_idx - 1]
    if pd.isna(cum):
        # 日报没有累计进度, 从实际数据推算
        cum = 0.0

    pred_weeks = start_idx
    actual_weeks = len(proj)

    for i in range(start_idx, len(proj) + max_extra_weeks):
        if cum >= 0.99:
            break

        if i < len(proj):
            row = proj.iloc[i : i + 1][feature_cols].copy()
        else:
            # 超出已有数据: 用最后一周近似
            row = proj.iloc[-1:][feature_cols].copy()
            row["week_num"] = i + 1
            # 更新进度特征
            row["cumulative_progress"] = cum
            row["cum_sqrt"] = np.sqrt(cum)
            row["cum_sq"] = cum ** 2
            row["remaining"] = 1.0 - cum

        row = row.fillna(0)
        if row.isna().any().any():
            break

        pred = model.predict(row)[0]
        cum += max(pred, 0)
        pred_weeks += 1

    return {
        "project_code": project_code,
        "actual_weeks": actual_weeks,
        "predicted_weeks": pred_weeks,
        "error_weeks": pred_weeks - actual_weeks,
        "error_pct": (pred_weeks - actual_weeks) / actual_weeks * 100,
    }


# ============================================================
# 4. 结果输出
# ============================================================

def print_feature_importance(importance, feature_names, top_n=15):
    if importance is None:
        return
    idx = np.argsort(importance)[::-1]
    print(f"\n  {'Rank':<5} {'Feature':<28} {'Importance':<10}")
    print(f"  {'-'*43}")
    for i in range(min(top_n, len(feature_names))):
        print(f"  {i+1:<5} {feature_names[idx[i]]:<28} {importance[idx[i]]:.4f}")


def save_model(model, name, model_dir="models"):
    os.makedirs(model_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(model_dir, f"{name}_{ts}.pkl")
    joblib.dump(model, path)
    print(f"  模型: {path}")
    return path


# ============================================================
# 5. 主入口
# ============================================================

def load_and_merge(data_dir):
    """加载甘特图数据，如有日报伪标签数据则合并。"""
    gantt_path = os.path.join(data_dir, "weekly_gantt.csv")
    df = pd.read_csv(gantt_path, encoding="utf-8-sig")
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["source"] = "gantt"
    extra_features = []
    print(f"  [甘特图] {len(df)}周, {df['project_code'].nunique()}个项目")

    daily_path = os.path.join(data_dir, "weekly_daily_labeled.csv")
    if os.path.exists(daily_path):
        daily = pd.read_csv(daily_path, encoding="utf-8-sig")
        daily["week_start"] = pd.to_datetime(daily["week_start"])
        daily["source"] = "daily"

        # 日报独有特征（甘特图没有的）
        extra_features = [
            "rain_days", "extreme_days", "avg_temp",
            "avg_workers", "max_workers", "total_equip",
            "avg_items_per_day", "total_items_week",
            "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
        ]
        extra_features = [c for c in extra_features if c in daily.columns]

        # 甘特图独有特征在日报里填0
        for c in GANTT_FEATURES:
            if c not in daily.columns:
                daily[c] = 0.0

        # 日报独有特征在甘特图里填0
        for c in extra_features:
            if c not in df.columns:
                df[c] = 0.0

        # 合并
        base_cols = ["project_code", "week_start", "week_end", "week_num",
                     "month", "weekly_progress", "cumulative_progress", "source"]
        all_needed = base_cols + GANTT_FEATURES + extra_features
        # 去重保序
        seen = set()
        common_cols = []
        for c in all_needed:
            if c not in seen and c in df.columns and c in daily.columns:
                common_cols.append(c)
                seen.add(c)

        df = pd.concat([df[common_cols], daily[common_cols]], ignore_index=True)
        print(f"  [日报] {len(daily)}周 → 合并后 {len(df)}周, {df['project_code'].nunique()}个项目")
        print(f"  [日报独有特征] {extra_features}")
    else:
        print(f"  [日报] 未找到 weekly_daily_labeled.csv, 仅用甘特图训练")

    return df, extra_features


def train(data_dir, model_dir="models"):
    """
    完整训练流程：
    - 加载甘特图周级数据 + 日报伪标签数据（如有）
    - 特征工程
    - 多模型训练 + Leave-One-Project-Out CV
    - 保存最佳模型 + 特征列表
    """
    print("=" * 70)
    print("模型训练 (CV=Leave-One-Project-Out)")
    print("=" * 70)

    # ---- 加载数据 ----
    print("\n[加载]")
    df, extra_features = load_and_merge(data_dir)
    print(f"  标签均值: {df['weekly_progress'].mean():.4f}  "
          f"中位数: {df['weekly_progress'].median():.4f}  "
          f"零值率: {(df['weekly_progress']==0).mean():.1%}")

    # ---- 特征工程 ----
    print("\n[特征工程]")
    df = build_features(df)

    # 筛选可用特征
    all_feature_candidates = GANTT_FEATURES + extra_features
    available = [c for c in all_feature_candidates if c in df.columns]
    missing = [c for c in all_feature_candidates if c not in df.columns]
    if missing:
        print(f"  缺失特征: {missing}")

    df_model = df.dropna(subset=available + ["weekly_progress"])
    X = df_model[available]
    y = df_model["weekly_progress"]
    groups = df_model["project_code"]
    print(f"  特征: {len(available)}个  有效样本: {len(X)}")
    print(f"  项目: {groups.unique().tolist()}")

    # ---- 训练 ----
    print(f"\n[训练] GroupKFold (n_splits=5)")

    models = {
        "Ridge": Ridge(alpha=1.0, random_state=RANDOM_STATE),
        "RandomForest": RandomForestRegressor(
            n_estimators=200, max_depth=6,
            min_samples_leaf=3, min_samples_split=5,
            max_features="sqrt", random_state=RANDOM_STATE, n_jobs=-1,
        ),
        "XGBoost": xgb.XGBRegressor(
            n_estimators=200, max_depth=4,
            learning_rate=0.03, subsample=0.8,
            colsample_bytree=0.8, min_child_weight=3,
            reg_alpha=0.5, reg_lambda=1.0,
            random_state=RANDOM_STATE, n_jobs=-1, verbosity=0,
        ),
    }

    results = {}
    for name, mdl in models.items():
        print(f"\n  --- {name} ---")
        results[name] = cross_validate(X, y, groups, mdl)

    # ---- 对比 ----
    print(f"\n{'='*70}")
    print(f"模型对比")
    print(f"{'='*70}")
    print(f"  {'模型':<18} {'CV MAE':<10} {'+-std':<10} {'CV R2':<10} {'Overall R2':<10}")
    print(f"  {'-'*58}")
    for name, r in results.items():
        print(f"  {name:<18} {r['mean_mae']:<10.4f} {r['std_mae']:<10.4f} "
              f"{r['mean_r2']:<10.4f} {r['overall_r2']:<10.4f}")

    # 朴素基线
    if "progress_lag1" in X.columns:
        lag_mask = X["progress_lag1"].notna()
        naive_mae = mean_absolute_error(y[lag_mask], X.loc[lag_mask, "progress_lag1"])
        print(f"\n  朴素基线(上周值=本周预测): MAE={naive_mae:.4f}")

    # ---- 选择最佳模型 ----
    best_name = min(results, key=lambda k: results[k]["mean_mae"])
    best_result = results[best_name]
    print(f"\n最佳模型: {best_name} (MAE={best_result['mean_mae']:.4f})")

    # 特征重要性
    if best_result["feature_importance"] is not None:
        print(f"\n--- {best_name} 特征重要性 TOP15 ---")
        print_feature_importance(best_result["feature_importance"], available)

    # ---- 全量训练 & 保存 ----
    print(f"\n[保存]")
    final_model = train_final(models[best_name], X, y)
    model_path = save_model(final_model, f"weekly_{best_name.lower()}", model_dir)

    # 保存特征列表
    feat_path = os.path.join(model_dir, "feature_columns.txt")
    with open(feat_path, "w", encoding="utf-8") as f:
        f.write("\n".join(available))
    print(f"  特征列表: {feat_path}")

    # ---- 工期模拟 ----
    print(f"\n[工期预测模拟]")
    sims = []
    for proj in sorted(df["project_code"].unique()):
        s = simulate_project(final_model, df, proj, available)
        if s:
            sims.append(s)
            print(f"  {s['project_code']}: 实际{s['actual_weeks']}周 → "
                  f"预测{s['predicted_weeks']}周 (误差{s['error_weeks']:+d}周, {s['error_pct']:+.1f}%)")

    if sims:
        sim_df = pd.DataFrame(sims)
        print(f"\n  工期预测MAE: {np.mean(np.abs(sim_df['error_weeks'])):.1f}周")

    print(f"\n{'='*70}")
    print("训练完成!")
    print(f"{'='*70}")

    return final_model, available


if __name__ == "__main__":
    train(
        data_dir=r"D:\日报预测\data\processed",
        model_dir=r"D:\日报预测\models",
    )
