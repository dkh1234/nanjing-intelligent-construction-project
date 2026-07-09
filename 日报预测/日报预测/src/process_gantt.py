"""
甘特图处理模块
输入: data/gantt/ 下5个xlsx文件
输出: data/processed/unified_tasks.csv (清洗后任务表)
      data/processed/weekly_gantt.csv  (周级训练集, 含真实标签)
"""
import os
import numpy as np
import pandas as pd
from datetime import timedelta

from utils import generate_weeks, validate_weekly_df

# 列名映射（按位置，兼容两种列结构差异）
_COLUMNS = [
    "level",            # 0  层级
    "code",             # 1  WBS代码
    "task_name",        # 2  作业名称
    "type",             # 3  类型: wbs / 作业
    "planned_dur",      # 4  原定工期(天)
    "_drop1",           # 5  计划开始(不需要)
    "_drop2",           # 6  计划结束(不需要)
    "actual_start",     # 7  实际开始
    "actual_end",       # 8  实际结束
    "weight_pct",       # 9  权重%
    "completion_pct",   # 10 完成百分比
    "total_float",      # 11 总浮时
]

# 项目文件名→code
PROJECT_MAP = {
    "山东泉兴水泥有限公司4000td水泥熟料生产线项目下达.xlsx": "N812",
    "梅州皇马水泥有限公司5000td水泥熟料生产线（三线）下达.xlsx": "N686A",
    "江西玉山南方水泥有限公司8000td水泥熟料建设项目下达.xlsx": "N791",
    "池州中建材新材料有限公司年产4000万吨矿产品开采及加工项目下达.xlsx": "N836",
    "肇庆润信新材料有限公司大排矿年产3000万吨建筑花岗岩骨料项目下达.xlsx": "N825",
}


# ============================================================
# 1. 加载与清洗
# ============================================================

def load_gantt_files(data_dir):
    """读取全部甘特图，统一列名，合并为一张任务表。"""
    all_dfs = []
    for filename, code in PROJECT_MAP.items():
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            print(f"  [WARN] 文件不存在: {path}")
            continue

        df = pd.read_excel(path, engine="openpyxl")
        df.columns = _COLUMNS[: len(df.columns)]

        # 只保留叶子任务
        df = df[df["type"] == "作业"].copy()

        # 删除不需要的列
        df = df.drop(columns=["_drop1", "_drop2"], errors="ignore")

        # 类型转换
        df["planned_dur"] = pd.to_numeric(df["planned_dur"], errors="coerce")
        df["weight_pct"] = pd.to_numeric(df["weight_pct"], errors="coerce")
        df["completion_pct"] = pd.to_numeric(df["completion_pct"], errors="coerce")
        df["total_float"] = pd.to_numeric(df["total_float"], errors="coerce")
        df["actual_start"] = pd.to_datetime(df["actual_start"], errors="coerce")
        df["actual_end"] = pd.to_datetime(df["actual_end"], errors="coerce")
        df["project_code"] = code

        # 保留必要列
        keep = [
            "level", "code", "task_name", "planned_dur",
            "actual_start", "actual_end", "weight_pct",
            "completion_pct", "total_float", "project_code",
        ]
        df = df[[c for c in keep if c in df.columns]]

        all_dfs.append(df)
        print(f"  {code}: {len(df)}个叶子任务")

    merged = pd.concat(all_dfs, ignore_index=True)
    print(f"  合并: {len(merged)}个任务, {merged['project_code'].nunique()}个项目")
    return merged


def clean_dates(df):
    """修复异常日期。"""
    # N825: actual_start 有 2001-01-17 等脏数据
    bad_mask = (df["actual_start"] < pd.Timestamp("2015-01-01")) | df["actual_start"].isna()
    if bad_mask.sum() > 0:
        print(f"  异常 actual_start: {bad_mask.sum()}条")

        # 用 actual_end - planned_dur 回填
        can_fix = bad_mask & df["actual_end"].notna()
        df.loc[can_fix, "actual_start"] = (
            df.loc[can_fix, "actual_end"]
            - pd.to_timedelta(df.loc[can_fix, "planned_dur"].fillna(7), unit="D")
        )
        print(f"    已用 end-dur 修复: {can_fix.sum()}条")

        # 仍异常的用该项目最早有效日期
        still = (df["actual_start"] < pd.Timestamp("2015-01-01")) | df["actual_start"].isna()
        for proj in df.loc[still, "project_code"].unique():
            valid_min = df.loc[
                (df["project_code"] == proj) & ~still, "actual_start"
            ].min()
            if pd.notna(valid_min):
                fix = still & (df["project_code"] == proj)
                df.loc[fix, "actual_start"] = valid_min
                print(f"    {proj}: {fix.sum()}条用项目最早日{valid_min.date()}填充")

    # 缺失 actual_end → actual_start + planned_dur 估算
    missing = df["actual_end"].isna()
    if missing.sum() > 0:
        df.loc[missing, "actual_end"] = (
            df.loc[missing, "actual_start"]
            + pd.to_timedelta(df.loc[missing, "planned_dur"].fillna(7), unit="D")
        )
        print(f"  缺失 actual_end: {missing.sum()}条, 已用 start+dur 估算")

    return df


def normalize_weights(df):
    """每个项目内权重归一化到0-1。"""
    for proj in df["project_code"].unique():
        mask = df["project_code"] == proj
        total = df.loc[mask, "weight_pct"].sum()
        df.loc[mask, "weight_norm"] = (
            df.loc[mask, "weight_pct"] / total if total > 0 else 1.0 / mask.sum()
        )
    return df


# ============================================================
# 2. 展开为周级
# ============================================================

def expand_to_weekly(df):
    """将任务表展开为 项目-周 级别的标签数据。"""
    all_weekly = []

    # 计算实际工期
    df["actual_dur"] = (df["actual_end"] - df["actual_start"]).dt.days + 1
    df.loc[df["actual_dur"] <= 0, "actual_dur"] = 1

    for proj in df["project_code"].unique():
        p = df[df["project_code"] == proj]
        min_d, max_d = p["actual_start"].min(), p["actual_end"].max()
        weeks = generate_weeks(min_d, max_d)
        if len(weeks) == 0:
            continue

        # 已完成任务（完成率≥99%）视为有确定完工日期
        done = p[p["completion_pct"] >= 99].copy()

        records = []
        for w in weeks:
            w_end = w + timedelta(days=6)

            # 本周完成的任务权重
            mask_done = (
                (done["actual_end"] >= w) & (done["actual_end"] <= w_end)
            )
            weekly_progress = done.loc[mask_done, "weight_norm"].sum()

            # 累计完成
            cumulative = done.loc[
                done["actual_end"] <= w_end, "weight_norm"
            ].sum()

            # 活跃任务
            active = (
                (p["actual_start"] <= w_end) & (p["actual_end"] >= w)
            ).sum()

            # 新开工
            new_starts = (
                (p["actual_start"] >= w) & (p["actual_start"] <= w_end)
            ).sum()

            # 已延期未完工
            overdue = (
                (p["actual_end"] < w) & (p["completion_pct"] < 50)
            ).sum()

            records.append({
                "project_code": proj,
                "week_start": w.date(),
                "week_end": w_end.date(),
                "week_num": len(records) + 1,
                "weekly_progress": round(weekly_progress, 6),
                "cumulative_progress": round(cumulative, 6),
                "active_tasks": active,
                "new_starts": new_starts,
                "overdue_tasks": overdue,
            })

        wdf = pd.DataFrame(records)

        # 裁剪首尾空周
        max_cum = wdf["cumulative_progress"].max()
        wdf = wdf[
            ~(
                ((wdf["cumulative_progress"] == 0) & (wdf["active_tasks"] == 0))
                | ((wdf["cumulative_progress"] == max_cum) & (wdf["active_tasks"] == 0))
            )
        ].reset_index(drop=True)

        # 重编号
        wdf["week_num"] = range(1, len(wdf) + 1)

        # ---- 裁剪过长的零进度前导段 ----
        # 超过24周无实质进度 → 只保留最后4周零段作为预热
        first_real = wdf[wdf["cumulative_progress"] > max_cum * 0.01]
        first_activity = wdf[wdf["weekly_progress"] > 0.0001]
        if len(first_real) > 0:
            cutoff = first_real.index[0]
            if len(first_activity) > 0:
                cutoff = min(cutoff, first_activity.index[0])
            if cutoff > 24:
                keep_from = max(0, cutoff - 4)
                wdf = wdf.iloc[keep_from:].reset_index(drop=True)
                wdf["week_num"] = range(1, len(wdf) + 1)
                print(f"    裁剪{keep_from}周零段 → 剩余{len(wdf)}周")

        # 加月度特征
        wdf["month"] = pd.to_datetime(wdf["week_start"]).dt.month

        all_weekly.append(wdf)
        print(f"  {proj}: {len(done)}个完成任务 → {len(wdf)}周 ({min_d.date()}~{max_d.date()})")

    return pd.concat(all_weekly, ignore_index=True)


# ============================================================
# 3. 周级衍生特征
# ============================================================

def add_weekly_features(weekly_df, task_df):
    """基于任务表为每周补充结构特征。"""
    wdf = weekly_df.copy()

    features = []
    for _, row in wdf.iterrows():
        proj = row["project_code"]
        ws = pd.Timestamp(row["week_start"])
        we = pd.Timestamp(row["week_end"])
        p = task_df[task_df["project_code"] == proj]

        active = p[(p["actual_start"] <= we) & (p["actual_end"] >= ws)]
        done_before = p[(p["actual_end"] <= we) & (p["completion_pct"] >= 99)]

        # 平均任务工期
        avg_dur = active["planned_dur"].mean() if len(active) > 0 else 0

        # 剩余工作量 = 活跃任务计划工期之和
        remaining = active["planned_dur"].sum()

        # 已完成任务的实际/计划工期比
        if len(done_before) > 0 and done_before["planned_dur"].mean() > 0:
            delay_ratio = done_before["actual_dur"].mean() / done_before["planned_dur"].mean()
        else:
            delay_ratio = 1.0

        # 本周完工数
        completed_this = (
            (p["actual_end"] >= ws) & (p["actual_end"] <= we)
        ).sum()

        features.append({
            "avg_task_dur": avg_dur,
            "total_remaining_work": remaining,
            "delay_ratio_to_date": round(delay_ratio, 3),
            "completed_this_week": completed_this,
        })

    return pd.concat([wdf.reset_index(drop=True), pd.DataFrame(features)], axis=1)


# ============================================================
# 4. 主入口
# ============================================================

def process(input_dir, output_dir):
    """
    完整处理流程: 读取甘特图 → 清洗 → 归一化 → 周级展开。
    返回: (unified_tasks_df, weekly_gantt_df)
    """
    print("=" * 60)
    print("甘特图→周级数据处理")
    print("=" * 60)

    # Step 1: 加载合并
    print("\n[1] 加载甘特图...")
    tasks = load_gantt_files(input_dir)

    # Step 2: 清洗
    print("\n[2] 清洗数据...")
    tasks = clean_dates(tasks)

    # Step 3: 权重归一化
    print("\n[3] 权重归一化...")
    tasks = normalize_weights(tasks)

    # 保存任务表
    os.makedirs(output_dir, exist_ok=True)
    task_path = os.path.join(output_dir, "unified_tasks.csv")
    tasks.to_csv(task_path, index=False, encoding="utf-8-sig")
    print(f"  任务表: {task_path}")

    # Step 4: 周级展开
    print("\n[4] 展开为周级数据...")
    weekly = expand_to_weekly(tasks)

    # Step 5: 衍生特征
    print("\n[5] 添加周级特征...")
    weekly = add_weekly_features(weekly, tasks)

    # 保存
    weekly_path = os.path.join(output_dir, "weekly_gantt.csv")
    weekly.to_csv(weekly_path, index=False, encoding="utf-8-sig")
    print(f"  周级表: {weekly_path}")

    # 校验
    print("\n[校验]")
    validate_weekly_df(weekly, "weekly_gantt")

    # 汇总
    print(f"\n{'='*60}")
    for proj, grp in weekly.groupby("project_code"):
        print(f"  {proj}: {len(grp)}周 进度{grp['cumulative_progress'].min():.1%}→{grp['cumulative_progress'].max():.1%}  周均{grp['weekly_progress'].mean():.4f}")
    print(f"  标签均值={weekly['weekly_progress'].mean():.4f}  零进度周={((weekly['weekly_progress']==0).sum()/len(weekly)):.1%}")
    print(f"{'='*60}")

    return tasks, weekly


if __name__ == "__main__":
    process(
        input_dir=r"D:\日报预测\data\gantt",
        output_dir=r"D:\日报预测\data\processed",
    )
