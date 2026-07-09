"""
为日报项目生成伪进度标签，基于施工活动签名追踪。
与 track_activities.py 共享核心逻辑。
"""
import os
import re
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import timedelta

RAW_DIR = r"D:\日报预测\data\daily"
OUTPUT_DIR = r"D:\日报预测\data\processed"

LOC_SUFFIX = "(?:车间|库|房|区域|道路|堆棚|场|站|楼|坑|沟|塔|窑|仓|廊|棚|坪|池|槽|井|所|室)"
ACTION_KW = "(?:安装|施工|浇筑|开挖|回填|拆除|绑扎|焊接|铺设|碾压|涂刷|搭设|砌筑|抹灰|养护|验收|清理|破除|吊装|调试|修理|更换|加固|支护|防水|保温|装修|喷浆|钻孔|切割|运输|吊运|组装|校正|测量|放线|检测|试验|灌注|打入|沉桩|打桩|爆破|夯实)"


def extract_location_action(text):
    sigs = []
    loc_pattern = re.compile(r"([一-龥]{2,10}?)" + LOC_SUFFIX)
    locations = loc_pattern.findall(text)
    if not locations:
        loc_pattern2 = re.compile(r"([一-龥]{2,8})" + LOC_SUFFIX)
        locations = loc_pattern2.findall(text)
    actions = re.findall(ACTION_KW, text)
    for loc in locations[:3]:
        for act in actions[:2]:
            sigs.append(f"{loc}-{act}")
    if not sigs:
        phrases = re.findall(r"[一-龥]{3,15}", text)
        for phrase in phrases[:2]:
            sigs.append(phrase)
    return list(set(sigs))


def build_pseudo_labels(proj_dir, proj_code):
    """追踪活动签名，为每周生成伪进度标签。"""
    files = sorted([f for f in os.listdir(proj_dir) if f.endswith(".txt")])

    sig_first = {}
    sig_last = {}

    for fname in files:
        date_str = fname.replace(".txt", "")
        try:
            date = pd.to_datetime(date_str).date()
        except:
            continue

        path = os.path.join(proj_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except:
            continue

        items = re.findall(r"(?:\d+[\.\、）)]|（\d+）|[a-z][\.\)])([^\n]+)", text)
        all_sigs = []
        for item in items:
            all_sigs.extend(extract_location_action(item))
        all_sigs = list(set(all_sigs))

        for sig in all_sigs:
            if sig not in sig_first:
                sig_first[sig] = date
            sig_last[sig] = date

    total_sigs = len(sig_first)
    if total_sigs < 20:
        print(f"  [WARN] {proj_code}: 仅{total_sigs}个签名, 跳过")
        return None

    # 加载已有的周级特征
    daily_path = os.path.join(OUTPUT_DIR, "weekly_daily.csv")
    daily = pd.read_csv(daily_path, encoding="utf-8-sig")
    daily["week_start"] = pd.to_datetime(daily["week_start"])
    proj_weekly = daily[daily["project_code"] == proj_code].copy()

    # 为每周计算伪进度
    pseudo_progress = []
    pseudo_cumulative = []
    for _, row in proj_weekly.iterrows():
        ws = pd.to_datetime(row["week_start"]).date()
        we = pd.to_datetime(row["week_end"]).date()

        new_count = sum(1 for sig, first in sig_first.items() if ws <= first <= we)
        cum_count = sum(1 for sig, first in sig_first.items() if first <= we)

        pseudo_progress.append(new_count / total_sigs)
        pseudo_cumulative.append(cum_count / total_sigs)

    proj_weekly["weekly_progress"] = pseudo_progress
    proj_weekly["cumulative_progress"] = pseudo_cumulative

    print(f"  {proj_code}: {total_sigs}个签名, "
          f"周均伪进度={proj_weekly['weekly_progress'].mean():.4f}, "
          f"零进度率={(proj_weekly['weekly_progress']==0).mean():.1%}")

    return proj_weekly


def add_pseudo_labels():
    print("=" * 60)
    print("日报伪标签生成")
    print("=" * 60)

    updated_dfs = []
    for proj_code in ["P001", "P003"]:
        proj_dir = os.path.join(RAW_DIR, proj_code)
        if not os.path.isdir(proj_dir):
            print(f"  [SKIP] {proj_code}: 目录不存在")
            continue
        labeled = build_pseudo_labels(proj_dir, proj_code)
        if labeled is not None:
            updated_dfs.append(labeled)

    if not updated_dfs:
        print("无数据输出")
        return None

    result = pd.concat(updated_dfs, ignore_index=True)
    out_path = os.path.join(OUTPUT_DIR, "weekly_daily_labeled.csv")
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n输出: {out_path} ({len(result)}周)")
    return result


if __name__ == "__main__":
    add_pseudo_labels()
