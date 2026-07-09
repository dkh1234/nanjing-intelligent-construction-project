"""
日报处理模块
输入: data/daily/P002/*.txt, data/daily/P003/*.txt
输出: data/processed/weekly_daily.csv (周级特征, 无标签)

日报→解析→天级DataFrame→按周聚合→输出执行强度特征
日报不提供进度标签，作为补充特征用于模型预测阶段。
"""
import os
import re
import numpy as np
import pandas as pd
from datetime import timedelta
from collections import Counter

from utils import parse_date, parse_temperature, is_rainy, is_extreme, week_boundaries, validate_weekly_df
from detail_templates import parse_activity_line

# ---- 工序关键词（与甘特图工序分类对齐） ----
WORK_CATEGORIES = {
    "土建":    ["开挖", "回填", "浇筑", "混凝土", "砼", "钢筋", "模板", "抹灰", "砌筑",
                "基槽", "基坑", "桩基", "桩头", "承台", "地面", "道路", "碾压",
                "拆除", "清理", "脚手架", "搭设", "绑扎", "打桩", "夯实", "垫层",
                "砌砖", "圈梁", "构造柱", "框架柱", "框架", "屋面", "女儿墙",
                "散装", "转运站", "输送地坑", "循环水池", "泵房"],
    "钢结构":  ["钢结构", "钢构", "钢梁", "钢柱", "预埋件", "焊接", "牛腿", "框柱",
                "非标制作", "组对", "钢平台", "栏杆", "楼梯", "钢绞线", "门架",
                "屋面板", "彩板", "支撑", "支架"],
    "设备安装": ["安装", "设备", "管道", "风管", "电缆", "桥架", "配电", "机械",
                "非标件", "阀门", "选粉机", "收尘", "风机", "膨胀节",
                "取料机", "提升机", "包装机", "装车机", "除尘器",
                "轨道", "斗提", "螺旋", "输送", "料仓", "料斗",
                "冷却", "润滑", "液压"],
    "装修":    ["装饰", "装修", "涂料", "防水", "保温", "门窗",
                "硅钙板", "气凝胶", "贴砖", "吊顶", "抹面",
                "涂刷", "油漆", "地坪", "瓷砖"],
}

# ---- 子项区域分类（从施工描述中识别具体工程区域） ----
SUB_PROJECTS = {
    "烧成窑尾":    ["窑尾", "C2", "C3", "C4", "C5", "C6", "分解炉", "烟室", "预热器"],
    "烧成窑头":    ["窑头", "篦冷机", "窑头罩", "斜拉链"],
    "烧成窑中":    ["窑中", "回转窑", "三次风管", "窑墩"],
    "原料粉磨":    ["原料磨", "原料粉磨", "辊压机", "废气处理", "袋收尘",
                   "大风管非标", "窑尾袋收尘"],
    "水泥粉磨":    ["水泥磨", "水泥粉磨", "选粉机", "旋风筒", "出料罩",
                   "电动葫芦", "砂浆墩"],
    "水泥储存":    ["水泥库", "水泥仓", "太极锥", "水泥储存"],
    "煤粉制备":    ["煤磨", "煤粉", "煤立磨", "煤粉仓", "原煤卸车", "原煤堆场"],
    "辅料堆场":    ["辅料", "堆棚", "堆场", "预均化", "取料机", "石灰石"],
    "原料配料":    ["原料配料", "配料站"],
    "水泥配料":    ["水泥配料", "配料站.*水泥"],
    "包装装车":    ["包装", "装车", "水泥汽车散装"],
    "中控电气":    ["中控", "电气", "照明", "开槽埋管"],
    "熟料库":      ["熟料库", "熟料转运"],
    "脱硫石膏":    ["脱硫", "石膏", "混合材"],
    "压缩空气":    ["压缩空气", "空压"],
    "循环水系统":  ["循环水", "泵房", "水泵", "水处理"],
    "转运站":      ["转运站"],
    "SCR脱硝":     ["SCR", "脱硝"],
    "水泥汽车散装": ["汽车散装", "水泥散装"],
    "厂区道路":    ["道路", "挡墙", "排洪沟", "进场路", "临时便道"],
}


def _categorize_work(text):
    """根据施工描述文本，判断属于哪类工序。"""
    hits = []
    for cat, keywords in WORK_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            hits.append(cat)
    return hits if hits else ["其他"]


def _classify_sub_project(text):
    """根据施工描述文本，识别所属子项区域。允许多区域匹配。"""
    hits = []
    for sub, keywords in SUB_PROJECTS.items():
        if any(kw in text for kw in keywords):
            hits.append(sub)
    return hits if hits else ["未分类"]


def _extract_construction_items(text):
    """提取施工情况条目，兼容“施工情况：1、...2、...”写在同一行的 Word 模板。"""
    normalized = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u00a0", " ")
    )
    section_match = re.search(
        r"(?:三[、\.．]?\s*)?施工情况[：:]?\s*(.*?)(?=(?:\n\s*(?:[四4五5][、\.．]|备注))|\s*$)",
        normalized,
        flags=re.S,
    )
    body = section_match.group(1).strip() if section_match else normalized

    marker_re = re.compile(r"(?:^|(?<=[\n。；;]))\s*(?:\d+[\.\、）)]|（\d+）)\s*")
    matches = list(marker_re.finditer(body))
    items = []

    if matches:
        for i, marker in enumerate(matches):
            start = marker.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            item = body[start:end].strip(" \n\t；;。")
            if len(item) >= 5:
                items.append(item)
    else:
        for line in body.split("\n"):
            line = line.strip()
            if re.match(r"^(?:\d+[\.\、）)]|（\d+）|[a-z][\.\)])", line):
                cleaned = re.sub(r"^(?:\d+[\.\、）)]|（\d+）|[a-z][\.\)])\s*", "", line).strip()
                if len(cleaned) >= 5:
                    items.append(cleaned)

    return items


# ============================================================
# 1. 单份日报解析
# ============================================================

def parse_one_report(text, filename=""):
    """解析一份日报文本，返回结构化字典。"""
    rec = {
        "date": None, "temp_min": None, "temp_max": None,
        "is_rainy": False, "is_extreme": False,
        "total_workers": 0, "num_subcontractors": 0,
        "num_excavator": 0, "num_crane": 0, "num_loader": 0,
        "num_mobile_crane": 0, "num_crawler_crane": 0,
        "construction_items": 0, "work_categories": [], "sub_projects": [],
        "detail_gen": {}, "source_file": filename,
    }

    if not text or not isinstance(text, str):
        return rec

    lines = text.strip().split("\n")

    # 日期和天气（第一行）
    first_line = lines[0].strip() if lines else ""
    d = parse_date(first_line)
    if d:
        rec["date"] = d
    tmin, tmax = parse_temperature(first_line)
    if tmin is not None:
        rec["temp_min"] = tmin
    if tmax is not None:
        rec["temp_max"] = tmax
    rec["is_rainy"] = is_rainy(first_line)
    rec["is_extreme"] = is_extreme(first_line)

    # 全文本搜索工人和设备
    full = " ".join(lines)

    # 工人: 匹配 "xx人" 模式
    worker_nums = re.findall(r"(\d+)\s*人", full)
    if worker_nums:
        rec["total_workers"] = sum(int(n) for n in worker_nums)
        rec["num_subcontractors"] = len(worker_nums)

    # 机械: 设备名+数量
    equip_patterns = {
        "num_excavator":    [r"挖[掘]?机\s*(\d+)", r"(\d+)\s*台[^，。]*挖"],
        "num_loader":       [r"装载机\s*(\d+)", r"(\d+)\s*台[^，。]*装载"],
        "num_mobile_crane": [r"汽车吊\s*(\d+)", r"(\d+)\s*台[^，。]*汽车吊"],
        "num_crawler_crane":[r"履带吊\s*(\d+)", r"(\d+)\s*台[^，。]*履带"],
        "num_crane":        [r"塔吊\s*(\d+)", r"(\d+)\s*台[^，。]*塔吊"],
    }
    for key, pats in equip_patterns.items():
        for pat in pats:
            m = re.search(pat, full)
            if m:
                rec[key] = int(m.group(1))
                break

    # 施工条目：兼容条目独立成行、以及 Word 中多个编号条目挤在同一行的格式
    all_work_text = _extract_construction_items(text)
    rec["construction_items"] = len(all_work_text)

    # 工序分类 + 具体数量提取
    cats = []
    subs = []
    detail_gen = {}
    for t in all_work_text:
        cats.extend(_categorize_work(t))
        subs.extend(_classify_sub_project(t))
        sub, qty = parse_activity_line(t)
        if qty and "根数" in qty:
            detail_gen[sub] = detail_gen.get(sub, 0) + qty["根数"]
    rec["work_categories"] = cats
    rec["sub_projects"] = subs
    rec["detail_gen"] = detail_gen

    return rec


# ============================================================
# 2. 批量解析项目日报
# ============================================================

def parse_project_daily(project_dir):
    """解析一个项目目录下所有日报TXT。"""
    records = []
    for fname in sorted(os.listdir(project_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(project_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue
        rec = parse_one_report(text, fname)
        records.append(rec)

    df = pd.DataFrame(records)
    df = df.dropna(subset=["date"]).sort_values("date")
    return df


# ============================================================
# 3. 天→周聚合
# ============================================================

def aggregate_to_weekly(daily_df, project_code):
    """将天级日报聚合为周级特征。"""
    df = daily_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # 确定日期范围并生成周
    min_d, max_d = df["date"].min(), df["date"].max()
    w_start, _ = week_boundaries(min_d)
    w_end, _ = week_boundaries(max_d)
    weeks = pd.date_range(w_start, w_end, freq="W-MON")

    records = []
    for w in weeks:
        w_end_dt = w + timedelta(days=6)
        mask = (df["date"] >= w) & (df["date"] <= w_end_dt)
        week_data = df[mask]

        n_days = len(week_data)
        if n_days == 0:
            continue

        # 天气
        rain_days = week_data["is_rainy"].sum()
        extreme_days = week_data["is_extreme"].sum()
        avg_temp = week_data[["temp_min", "temp_max"]].mean().mean()  # 粗略平均

        # 人力
        avg_workers = week_data["total_workers"].mean()
        max_workers = week_data["total_workers"].max()
        sub_count = week_data["num_subcontractors"].mean()

        # 机械
        avg_excavator = week_data["num_excavator"].mean()
        avg_crane = week_data["num_crane"].mean()
        avg_loader = week_data["num_loader"].mean()
        avg_mobile_crane = week_data["num_mobile_crane"].mean()
        total_equip = week_data[
            ["num_excavator", "num_crane", "num_loader",
             "num_mobile_crane", "num_crawler_crane"]
        ].sum(axis=1).mean()

        # 施工活动
        avg_items = week_data["construction_items"].mean()
        total_items = week_data["construction_items"].sum()

        # 工序分布
        all_cats = []
        for cats in week_data["work_categories"]:
            all_cats.extend(cats)
        cat_counts = Counter(all_cats)

        # 子项区域分布
        all_subs = []
        for subs in week_data["sub_projects"]:
            all_subs.extend(subs)
        sub_counts = Counter(all_subs)

        # 具体数量聚合（子区域根数）
        detail_gen_week = {}
        for dg in week_data["detail_gen"]:
            if isinstance(dg, dict):
                for k, v in dg.items():
                    detail_gen_week[k] = detail_gen_week.get(k, 0) + v

        base_record = {
            "project_code": project_code,
            "week_start": w.date(),
            "week_end": w_end_dt.date(),
            "week_num": len(records) + 1,
            "month": w.month,
            "n_days": n_days,
            # 天气
            "rain_days": rain_days,
            "extreme_days": extreme_days,
            "avg_temp": round(avg_temp, 1) if pd.notna(avg_temp) else None,
            # 人力
            "avg_workers": round(avg_workers, 1),
            "max_workers": max_workers,
            "sub_count": round(sub_count, 1),
            # 机械
            "avg_excavator": round(avg_excavator, 2),
            "avg_crane": round(avg_crane, 2),
            "avg_loader": round(avg_loader, 2),
            "avg_mobile_crane": round(avg_mobile_crane, 2),
            "total_equip": round(total_equip, 2),
            # 施工活动
            "avg_items_per_day": round(avg_items, 1),
            "total_items_week": total_items,
            "cat_土建": cat_counts.get("土建", 0),
            "cat_钢结构": cat_counts.get("钢结构", 0),
            "cat_设备安装": cat_counts.get("设备安装", 0),
            "cat_装修": cat_counts.get("装修", 0),
        }
        # 子区域具体数量列
        for sub_name in sorted(SUB_PROJECTS.keys()):
            key = f"detail_{sub_name}_gen"
            base_record[key] = detail_gen_week.get(sub_name, 0)

        # 子项区域列：只保留出现过至少一次的区域
        for sub_name in sorted(SUB_PROJECTS.keys()):
            key = f"sub_{sub_name}"
            base_record[key] = sub_counts.get(sub_name, 0)

        # 活动签名特征：子项多样性 + 新区域出现
        unique_subs = len(sub_counts)
        base_record["sub_diversity"] = unique_subs  # 活跃区域数

        records.append(base_record)

    wdf = pd.DataFrame(records)

    # ---- 后处理：累计特征 ----
    # 子项区域首次出现追踪（排除非子项列的 sub_ 前缀列）
    skip_cols = {"sub_count", "sub_diversity", "sub_entropy", "cum_sub_areas", "new_sub_areas"}
    sub_cols = [c for c in wdf.columns
                if c.startswith("sub_") and c not in skip_cols]
    if sub_cols:
        cum_seen = set()
        new_counts = []
        entropy_vals = []
        for _, row in wdf.iterrows():
            active_now = {c for c in sub_cols if row.get(c, 0) > 0}
            new_this_week = len(active_now - cum_seen)
            cum_seen |= active_now
            new_counts.append(new_this_week)

            # Shannon 熵
            counts = [max(row.get(c, 0), 0) for c in sub_cols]
            total = sum(counts)
            if total > 0:
                probs = [c / total for c in counts if c > 0]
                entropy = -sum(p * np.log(p) for p in probs)
            else:
                entropy = 0.0
            entropy_vals.append(round(entropy, 3))

        wdf["new_sub_areas"] = new_counts
        wdf["sub_entropy"] = entropy_vals
        wdf["cum_sub_areas"] = [len({c for c in sub_cols if wdf.iloc[:i+1][c].sum() > 0})
                                for i in range(len(wdf))]

    # 进度标签（日报没有）
    wdf["weekly_progress"] = None
    wdf["cumulative_progress"] = None

    # 重编号
    wdf["week_num"] = range(1, len(wdf) + 1)
    return wdf


# ============================================================
# 4. 主入口
# ============================================================

def process(input_dir, output_dir, project_codes=None):
    """
    遍历 input_dir 下的项目子目录，解析日报并聚合为周级特征。
    project_codes: dict, 目录名→项目代号, 默认 {"P002":"P002", "P003":"P003"}
    """
    if project_codes is None:
        project_codes = {"P001": "P001", "P003": "P003"}

    print("=" * 60)
    print("日报→周级特征处理")
    print("=" * 60)

    all_weekly = []
    for dirname, code in project_codes.items():
        proj_dir = os.path.join(input_dir, dirname)
        if not os.path.isdir(proj_dir):
            print(f"  [WARN] 目录不存在: {proj_dir}")
            continue

        print(f"\n  处理: {code} ({proj_dir})")

        # 解析所有日报
        daily = parse_project_daily(proj_dir)
        print(f"    解析: {len(daily)}天日报")

        if len(daily) == 0:
            continue

        # 聚合为周级
        weekly = aggregate_to_weekly(daily, code)
        print(f"    聚合: {len(weekly)}周")

        # 基本信息
        print(f"    日期: {daily.date.min().date()} ~ {daily.date.max().date()}")
        print(f"    均温: {weekly.avg_temp.mean():.1f}°C  降雨周比例: {(weekly.rain_days > 0).mean():.1%}")

        all_weekly.append(weekly)

    if not all_weekly:
        print("\n  [ERROR] 未找到日报数据")
        return None

    result = pd.concat(all_weekly, ignore_index=True)

    # 保存
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "weekly_daily.csv")
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n  输出: {out_path}")

    # 汇总
    print(f"\n{'='*60}")
    print(f"  合计: {len(result)}周, {result['project_code'].nunique()}个项目")
    for proj, grp in result.groupby("project_code"):
        print(f"    {proj}: {len(grp)}周")

    return result


if __name__ == "__main__":
    process(
        input_dir=r"D:\日报预测\data\daily",
        output_dir=r"D:\日报预测\data\processed",
    )
