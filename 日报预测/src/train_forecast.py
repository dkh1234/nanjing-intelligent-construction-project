"""
下周预测模型训练 —— 基于日报 P001/P003 周级配对

输入: 本周特征 (人员/机械/天气/活动)
输出: 下周预测 (日均人数、各机械数量、各工序频次)

训练数据: data/processed/weekly_daily.csv (107周, 2项目)
验证方式: Leave-One-Project-Out (2折)
"""
import os
import warnings
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold
import xgboost as xgb

warnings.filterwarnings("ignore")

RANDOM_STATE = 42
DATA_PATH = r"D:\日报预测\data\processed\weekly_daily.csv"
MODEL_DIR = r"D:\日报预测\models\forecast"

# ---- 目标列定义（中文名 → 数据列名） ----
TARGETS = {
    "日均施工人员":    "avg_workers",
    "最大施工人员":    "max_workers",
    "挖机数量":        "avg_excavator",
    "汽车吊数量":      "avg_mobile_crane",
    "装载机数量":      "avg_loader",
    "塔吊数量":        "avg_crane",
    "机械设备总数":    "total_equip",
    "每日施工条目数":  "avg_items_per_day",
    "每周施工条目数":  "total_items_week",
    "土建活动频次":    "cat_土建",
    "钢结构活动频次":  "cat_钢结构",
    "设备安装活动频次":"cat_设备安装",
    "装修活动频次":    "cat_装修",
    "降雨天数":        "rain_days",
}

# ---- 恒定设备规则：直接用上周值，不训练模型 ----
CONSTANT_EQUIPMENT = ["塔吊数量", "装载机数量"]

# ---- 分目标参数 ----
TARGET_PARAMS = {
    # 稳定型: 浅树、强正则、保守学习
    "stable": {
        "n_estimators": 80, "max_depth": 3, "learning_rate": 0.03,
        "subsample": 0.8, "min_child_weight": 5,
        "reg_alpha": 1.0, "reg_lambda": 2.0,
    },
    # 人员型: 平衡
    "personnel": {
        "n_estimators": 100, "max_depth": 4, "learning_rate": 0.05,
        "subsample": 0.8, "min_child_weight": 3,
        "reg_alpha": 0.5, "reg_lambda": 1.0,
    },
    # 波动型: 深树、敏感、低正则
    "volatile": {
        "n_estimators": 150, "max_depth": 5, "learning_rate": 0.05,
        "subsample": 0.8, "min_child_weight": 1,
        "reg_alpha": 0.1, "reg_lambda": 0.5,
    },
}

# 目标→参数组映射
TARGET_PARAM_GROUP = {
    "日均施工人员": "personnel",
    "最大施工人员": "personnel",
    "挖机数量": "stable",
    "汽车吊数量": "stable",
    "装载机数量": "stable",
    "塔吊数量": "stable",
    "机械设备总数": "stable",
    "每日施工条目数": "volatile",
    "每周施工条目数": "volatile",
    "土建活动频次": "volatile",
    "钢结构活动频次": "volatile",
    "设备安装活动频次": "volatile",
    "装修活动频次": "volatile",
    "降雨天数": "volatile",
}

# ---- 后处理规则：预测值不能突破的边界 ----
POST_RULES = {
    "日均施工人员": {"min": 0, "max_change_ratio": 0.3},    # 周环比不超过±30%
    "最大施工人员": {"min": 0, "max_change_ratio": 0.3},
    "塔吊数量":     {"min": 0, "max_change_abs": 0},         # 周间不变
    "装载机数量":   {"min": 0, "max_change_abs": 1},         # 周间最多±1
    "挖机数量":     {"min": 0, "max_change_abs": 2},
    "降雨天数":     {"min": 0, "max": 7},
    "每日施工条目数":{"min": 0, "max_change_ratio": 0.5},
    "每周施工条目数":{"min": 0, "max_change_ratio": 0.5},
}

# ---- 特征列（本周已知） ----
BASE_FEATURES = [
    "week_num", "month_sin", "month_cos",
    "rain_days", "extreme_days", "avg_temp",
    "n_days",
    "avg_workers", "max_workers", "sub_count",
    "avg_excavator", "avg_crane", "avg_loader", "avg_mobile_crane",
    "total_equip", "avg_items_per_day", "total_items_week",
    "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
    # 活动签名特征
    "sub_diversity", "new_sub_areas", "sub_entropy", "cum_sub_areas",
]

# 子项区域列在加载数据时动态追加


def _detect_features(df):
    """从数据中自动检测子项区域列和所有可用特征。"""
    sub_cols = sorted([c for c in df.columns
                       if c.startswith("sub_")
                       and c not in {"sub_count", "sub_diversity",
                                      "sub_entropy", "cum_sub_areas", "new_sub_areas"}])
    all_features = BASE_FEATURES + sub_cols
    return all_features, sub_cols


# ============================================================
# 1. 构造训练样本 (本周 → 下周配对)
# ============================================================

def build_training_pairs(df):
    """
    对每个项目，将相邻两周配成 (本周特征, 下周标签)。
    本周的特征列加上 lag/rolling，下周的数据作为标签。
    """
    df = df.sort_values(["project_code", "week_num"]).copy()

    # 时间编码
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # 动态检测子项区域列
    _, sub_cols = _detect_features(df)

    # 对每个项目单独处理
    all_pairs = []
    for proj in df["project_code"].unique():
        p = df[df["project_code"] == proj].sort_values("week_num").copy()

        # 滞后特征（3周/5周滑动均值）：基础列 + 子项区域列
        lag_cols = ["avg_workers", "total_equip", "avg_items_per_day",
                    "rain_days", "cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修",
                    "sub_diversity", "sub_entropy"]
        # 追加子项区域列
        sub_cols = [c for c in p.columns if c.startswith("sub_")
                    and c not in {"sub_count", "sub_diversity", "sub_entropy",
                                   "cum_sub_areas", "new_sub_areas"}]
        lag_cols.extend(sub_cols)
        for col in lag_cols:
            if col in p.columns:
                p[f"{col}_lag1"] = p[col].shift(1)
                p[f"{col}_lag2"] = p[col].shift(2)
                p[f"{col}_lag3"] = p[col].shift(3)
                p[f"{col}_ma3"] = p[col].shift(1).rolling(3, min_periods=1).mean()
                p[f"{col}_ma5"] = p[col].shift(1).rolling(5, min_periods=1).mean()

        # 趋势特征（变化方向与幅度）
        if "avg_workers" in p.columns:
            p["workers_trend"] = p["avg_workers"].shift(1) - p["avg_workers"].shift(2)
            p["workers_change_rate"] = (p["avg_workers"].shift(1) - p["avg_workers"].shift(2)) / (p["avg_workers"].shift(2) + 1)
        if "total_items_week" in p.columns:
            p["activity_trend"] = p["total_items_week"].shift(1) - p["total_items_week"].shift(2)
        if "total_equip" in p.columns:
            p["equip_trend"] = p["total_equip"].shift(1) - p["total_equip"].shift(2)

        # ---- 阶段推断特征（基于工序分布变化） ----
        # 活动总量
        activity_cols = ["cat_土建", "cat_钢结构", "cat_设备安装", "cat_装修"]
        existing = [c for c in activity_cols if c in p.columns]
        if existing:
            p["total_activity"] = p[existing].sum(axis=1)
            # 各工序占比（反映项目所处阶段）
            for c in existing:
                p[f"{c}_ratio"] = p[c] / (p["total_activity"] + 1)
            # 土建占比高 → 早期；设备安装占比高 → 中期；装修占比高 → 后期
            if "cat_土建" in existing and "cat_装修" in existing and "cat_设备安装" in existing:
                p["stage_early_score"] = p["cat_土建"] / (p["total_activity"] + 1)
                p["stage_mid_score"] = p["cat_设备安装"] / (p["total_activity"] + 1)
                p["stage_late_score"] = p["cat_装修"] / (p["total_activity"] + 1)
                # 阶段转移信号：早期得分下降 + 后期得分上升 = 进入收尾
                p["stage_transition"] = (
                    (p["stage_late_score"].shift(1) - p["stage_late_score"].shift(3))
                    - (p["stage_early_score"].shift(1) - p["stage_early_score"].shift(3))
                )

        # 构造配对: 第i行是本周特征, 第i+1行的target是下周标签
        for i in range(len(p) - 1):
            this_week = p.iloc[i]
            next_week = p.iloc[i + 1]

            pair = {"project_code": proj, "week_num": int(this_week["week_num"])}

            # 本周特征 + 子项区域列
            for c in BASE_FEATURES:
                if c in p.columns:
                    pair[c] = this_week[c]
            for c in sub_cols:
                if c in p.columns:
                    pair[c] = this_week[c]

            # lag / 衍生特征（以特定后缀结尾）
            _lag_suffixes = ("_lag1", "_lag2", "_lag3", "_ma3", "_ma5",
                             "_trend", "_rate", "_ratio", "_score", "_transition")
            for col in p.columns:
                if col.endswith(_lag_suffixes):
                    pair[col] = this_week[col]

            # 下周标签（用中文名）
            for cn_name, en_col in TARGETS.items():
                if en_col in p.columns:
                    pair[cn_name] = next_week[en_col]

            all_pairs.append(pair)

    result = pd.DataFrame(all_pairs)
    # 区分特征列和标签列
    feature_cols = [c for c in result.columns
                    if c not in list(TARGETS.keys()) + ["project_code", "week_num"]]
    label_cols = [k for k in TARGETS.keys() if k in result.columns]

    print(f"  构造配对: {len(result)}条 ({df['project_code'].nunique()}项目)")
    print(f"  特征列: {len(feature_cols)}个")
    print(f"  目标列: {len(label_cols)}个 → {label_cols}")
    return result, feature_cols, label_cols


# ============================================================
# 2. 训练（每个目标独立训练一个 XGBoost）
# ============================================================

def train_one_target(X, y, groups, target_name):
    """单个目标的 XGBoost 训练 + 2折CV（使用分组参数）。"""
    param_group = TARGET_PARAM_GROUP.get(target_name, "personnel")
    params = TARGET_PARAMS[param_group]
    params["random_state"] = RANDOM_STATE
    params["n_jobs"] = -1
    params["verbosity"] = 0

    model = xgb.XGBRegressor(**params)

    gkf = GroupKFold(n_splits=2)
    scores = []
    for fold, (tr, te) in enumerate(gkf.split(X, y, groups)):
        X_tr, X_te = X.iloc[tr], X.iloc[te]
        y_tr, y_te = y.iloc[tr], y.iloc[te]
        m = xgb.XGBRegressor(**params)
        m.fit(X_tr, y_tr)
        pred = m.predict(X_te)
        mae = mean_absolute_error(y_te, pred)
        scores.append(mae)

    # 全量训练
    final = xgb.XGBRegressor(**params)
    final.fit(X, y)

    return {
        "target": target_name,
        "cv_mae": np.mean(scores),
        "cv_mae_folds": scores,
        "model": final,
        "importance": final.feature_importances_,
        "baseline_mae": mean_absolute_error(y, [y.mean()] * len(y)),
        "param_group": param_group,
    }


def train_all(pairs, feature_cols, label_cols):
    """为每个目标列训练独立的 XGBoost（恒定设备跳过）。"""
    X = pairs[feature_cols].fillna(0)
    groups = pairs["project_code"]

    results = []
    for cn_name in label_cols:
        # 恒定设备直接用规则，不训练
        if cn_name in CONSTANT_EQUIPMENT:
            print(f"  {cn_name:<16} [恒定设备-规则] 沿用上周值")
            continue

        y = pairs[cn_name]
        mask = y.notna()
        if mask.sum() < 10:
            print(f"  [SKIP] {cn_name}: 有效样本不足 ({mask.sum()})")
            continue

        r = train_one_target(X[mask], y[mask], groups[mask], cn_name)
        results.append(r)

        grp = r["param_group"]
        print(f"  {cn_name:<16} CV MAE={r['cv_mae']:.2f}  "
              f"基线MAE={r['baseline_mae']:.2f}  "
              f"改善={1-r['cv_mae']/r['baseline_mae']:.1%}  [{grp}]")

    return results


# ============================================================
# 3. 保存
# ============================================================

def save_models(results, feature_cols, model_dir=MODEL_DIR):
    """保存每个目标的模型和元数据。"""
    os.makedirs(model_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    for r in results:
        name = r["target"]
        path = os.path.join(model_dir, f"{name}_{ts}.pkl")
        joblib.dump(r["model"], path)

    # 保存特征列表
    feat_path = os.path.join(model_dir, "feature_columns.txt")
    with open(feat_path, "w", encoding="utf-8") as f:
        f.write("\n".join(feature_cols))

    # 保存汇总报告
    report_path = os.path.join(model_dir, f"report_{ts}.csv")
    rows = []
    for r in results:
        rows.append({
            "目标": r["target"],
            "CV_MAE": round(r["cv_mae"], 2),
            "基线MAE": round(r["baseline_mae"], 2),
            "改善": f"{1-r['cv_mae']/r['baseline_mae']:.1%}",
        })
    pd.DataFrame(rows).to_csv(report_path, index=False, encoding="utf-8-sig")

    print(f"\n模型保存到: {model_dir}/")
    print(f"  特征列表: {feat_path}")
    print(f"  评估报告: {report_path}")
    return model_dir


# ============================================================
# 4. 主入口
# ============================================================

def main():
    print("=" * 60)
    print("下周预测模型训练 (多目标 XGBoost)")
    print("=" * 60)

    # 加载
    print("\n[1] 加载日报周级数据...")
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    df["week_start"] = pd.to_datetime(df["week_start"])
    print(f"  {len(df)}周, {df['project_code'].nunique()}个项目")

    # 动态检测子项区域列
    all_features, sub_cols = _detect_features(df)
    print(f"  特征列: {len(all_features)}个 (含{len(sub_cols)}个子项区域)")

    # 配对
    print("\n[2] 构造训练配对 (本周→下周)...")
    pairs, feature_cols, label_cols = build_training_pairs(df)

    # 训练
    print(f"\n[3] 训练 (Leave-One-Project-Out, 2折)...")
    results = train_all(pairs, feature_cols, label_cols)

    # 特征重要性
    print(f"\n[4] 特征重要性 (以日均施工人员为例)...")
    workers_result = [r for r in results if r["target"] == "日均施工人员"]
    if workers_result:
        r = workers_result[0]
        imp = r["importance"]
        idx = np.argsort(imp)[::-1]
        for i in range(min(10, len(feature_cols))):
            print(f"  {i+1}. {feature_cols[idx[i]]}: {imp[idx[i]]:.3f}")

    # 保存
    print(f"\n[5] 保存模型...")
    save_models(results, feature_cols)

    # 汇总
    print(f"\n{'='*60}")
    print(f"训练完成! {len(results)}/{len(label_cols)} 个目标模型")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
