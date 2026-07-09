"""
验证日报施工活动是否可追踪 —— 能否从中提取伪进度标签

思路: 日报每条施工条目 = 一个"微型任务"
追踪每个区域的首次出现/最后出现 → 构造伪进度曲线
"""
import os
import re
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import timedelta

RAW_DIR = r"D:\日报\清洗数据\dataClean\data\raw"

# 地点后缀
LOC_SUFFIX = "(?:车间|库|房|区域|道路|堆棚|场|站|楼|坑|沟|塔|窑|仓|廊|棚|坪|池|槽|井|所|室)"

# 动作关键词
ACTION_KW = "(?:安装|施工|浇筑|开挖|回填|拆除|绑扎|焊接|铺设|碾压|涂刷|搭设|砌筑|抹灰|养护|验收|清理|破除|吊装|调试|修理|更换|加固|支护|防水|保温|装修|喷浆|钻孔|切割|运输|吊运|组装|校正|测量|放线|检测|试验|灌注|打入|沉桩|打桩|开挖|爆破|运输|回填|碾压|夯实)"

def extract_location_action(text):
    """从施工描述中提取 地点+动作 简化签名。
    例如 '石膏堆棚北侧道路基槽开挖' → 石膏堆棚-开挖
         '机修车间6.977米牛腿预埋件安装' → 机修车间-安装
    """
    sigs = []
    # 找 "地点后缀" 前面最近的名词短语
    loc_pattern = re.compile(r'([一-龥]{2,10}?)' + LOC_SUFFIX)
    locations = loc_pattern.findall(text)

    if not locations:
        # fallback: 尝试找纯地点词
        loc_pattern2 = re.compile(r'([一-龥]{2,8})' + LOC_SUFFIX)
        locations = loc_pattern2.findall(text)

    # 找动作
    actions = re.findall(ACTION_KW, text)

    for loc in locations[:3]:  # 最多取3个地点
        for act in actions[:2]:  # 最多取2个动作
            sigs.append(f"{loc}-{act}")

    # 如果没有匹配到地点+动作组合, 取最长的名词短语
    if not sigs:
        # 提取所有2-8字的中文短语作为备选
        phrases = re.findall(r'[一-龥]{3,15}', text)
        for phrase in phrases[:2]:
            sigs.append(phrase)

    return list(set(sigs))


def track_project(proj_dir, proj_code):
    """追踪一个项目所有活动签名的起止时间, 构造伪进度。"""
    files = sorted([f for f in os.listdir(proj_dir) if f.endswith(".txt")])

    sig_first = {}   # 签名 → 首次出现日期
    sig_last = {}    # 签名 → 末次出现日期
    daily_sigs = {}  # date → 当天所有签名

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

        # 提取编号施工条目
        items = re.findall(r'(?:\d+[\.\、）)]|（\d+）|[a-z][\.\)])([^\n]+)', text)
        all_sigs = []
        for item in items:
            sigs = extract_location_action(item)
            all_sigs.extend(sigs)

        # 去重（当天内）
        all_sigs = list(set(all_sigs))
        daily_sigs[date] = all_sigs

        for sig in all_sigs:
            if sig not in sig_first:
                sig_first[sig] = date
            sig_last[sig] = date

    total_sigs = len(sig_first)
    if total_sigs < 20:
        print(f"  [WARN] {proj_code}: 仅{total_sigs}个活动签名，可能不足以构造伪进度")
        return None, total_sigs

    # 生成周级伪进度
    all_dates = sorted(daily_sigs.keys())
    start_d = all_dates[0]
    end_d = all_dates[-1]

    weeks_data = []
    current = start_d - timedelta(days=start_d.weekday())  # 对齐到周一
    while current <= end_d:
        w_end = current + timedelta(days=6)

        # 本周新出现的签名
        new_count = sum(1 for sig, first in sig_first.items() if current <= first <= w_end)

        # 截至本周的累计签名
        cum_count = sum(1 for sig, first in sig_first.items() if first <= w_end)

        # 本周活跃签名
        active = sum(1 for sig in sig_first
                     if sig_first[sig] <= w_end and sig_last[sig] >= current)

        weeks_data.append({
            "project_code": proj_code,
            "week_start": current,
            "total_unique": total_sigs,
            "active": active,
            "new_this_week": new_count,
            "cumulative": cum_count,
            "pseudo_progress": cum_count / total_sigs,
            "pseudo_weekly": new_count / total_sigs,
        })

        current += timedelta(days=7)

    wdf = pd.DataFrame(weeks_data)

    # 裁剪首尾空周
    max_cum = wdf["cumulative"].max()
    wdf = wdf[
        ~(((wdf["cumulative"] == 0) & (wdf["active"] == 0))
          | ((wdf["cumulative"] == max_cum) & (wdf["active"] == 0)))
    ]
    wdf = wdf.reset_index(drop=True)
    wdf["week_num"] = range(1, len(wdf) + 1)

    return wdf, total_sigs


# ============================================================
print("=" * 60)
print("日报施工活动可追踪性验证")
print("=" * 60)

results = {}
for proj_dir_name in ["P001", "P003"]:
    proj_dir = os.path.join(RAW_DIR, proj_dir_name)
    if not os.path.isdir(proj_dir):
        print(f"\n{proj_dir_name}: 目录不存在")
        continue

    result = track_project(proj_dir, proj_dir_name)
    if result is None:
        print(f"\n{proj_dir_name}: 签名不足，放弃")
        continue

    wdf, total_sigs = result
    results[proj_dir_name] = (wdf, total_sigs)

    print(f"\n--- {proj_dir_name} ---")
    print(f"  提取活动签名: {total_sigs}个")
    print(f"  有效周数: {len(wdf)}")
    print(f"  周均活跃签名: {wdf['active'].mean():.1f}")
    print(f"  周均新签名: {wdf['new_this_week'].mean():.1f}")
    print(f"  伪累计进度: {wdf['pseudo_progress'].min():.1%} -> {wdf['pseudo_progress'].max():.1%}")

    zero_rate = (wdf['pseudo_weekly'] == 0).mean()
    print(f"  零伪进度周: {(wdf['pseudo_weekly']==0).sum()}/{len(wdf)} ({zero_rate:.1%})")
    print(f"  (甘特图零进度周参考: ~27%)")

    print(f"  前5周伪进度: {wdf['pseudo_weekly'].head(5).round(4).tolist()}")
    print(f"  后5周伪进度: {wdf['pseudo_weekly'].tail(5).round(4).tolist()}")
    print(f"  进度std: {wdf['pseudo_weekly'].std():.4f}")

    # S曲线特征
    c = wdf["pseudo_progress"]
    for pct_val in [0.25, 0.50, 0.75]:
        if c.max() >= pct_val:
            wk = wdf[c >= pct_val]["week_num"].min()
            print(f"  达{pct_val:.0%}签名: 第{wk}周 ({wk/len(wdf):.1%}位置)")

# ---- 对比甘特图 ----
if results:
    print("\n--- 与甘特图对比 ---")
    gantt = pd.read_csv(r"D:\日报预测\data\processed\weekly_gantt.csv", encoding="utf-8-sig")
    print(f"  甘特图 周均进度: {gantt['weekly_progress'].mean():.4f}  std: {gantt['weekly_progress'].std():.4f}")
    print(f"  甘特图 零进度率: {(gantt['weekly_progress']==0).mean():.1%}")
    for name, (wdf, total) in results.items():
        print(f"  {name} 伪进度均值: {wdf['pseudo_weekly'].mean():.4f}  std: {wdf['pseudo_weekly'].std():.4f}")

    print(f"\n  注意: 伪进度是基于'新出现活动签名数/总签名数'")
    print(f"        甘特图标签是基于'完成任务权重之和'")
    print(f"        两者量纲不同, 但形态应相似（都是S曲线）")

print("\n" + "=" * 60)
print("关键判断:")
print("1. 签名数 >= 50 → 可尝试路线A（伪标签联合训练）")
print("2. 签名数 20-50 → 考虑路线A但需降低伪标签权重")
print("3. 签名数 < 20 → 走路线B（日报特征嫁接）")
print("4. 零伪进度率是否接近甘特图的 ~27%？（太接近0或100%都说明信号差）")
print("=" * 60)
