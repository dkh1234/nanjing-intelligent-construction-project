"""
路径动作挖掘：从 path_activity_items.csv 学习每个路径的高频动作和转移关系。

输出:
  models/sequences/path_action_profile.json  — 每个路径的高频动作、典型数量
  models/sequences/path_action_transitions.json — 动作转移概率
"""
import os, sys, re, json
from collections import defaultdict, Counter
import pandas as pd
import numpy as np
from datetime import datetime


# 优先核心动作（长且具体的优先）
CORE_VERBS = [
    # 长动作短语（最具体）
    "模板安装", "模板拆除", "模板加固",
    "钢筋绑扎", "钢筋加工", "钢筋安装",
    "混凝土浇筑", "混凝土养护",
    "脚手架搭设", "脚手架拆除",
    "预埋件安装", "预埋件焊接",
    "钢结构安装", "钢结构焊接",
    "非标制作", "非标安装",
    "设备安装", "设备调试",
    "电缆敷设", "电缆接线",
    "桥架安装", "桥架盖板",
    "管道安装", "管道焊接", "管道试压",
    "风管安装", "风管制安",
    "网架安装", "网架拼装",
    "檩条安装", "屋面板安装",
    "墙体砌筑", "墙体抹灰",
    "基坑开挖", "基槽开挖", "基础回填",
    "垫层浇筑", "垫层施工",
    "承台浇筑", "承台施工",
    "桩基施工", "桩位复测",
    "土方开挖", "土方回填",
    "挡土墙", "墙背回填", "墙身浇筑", "墙身模板",
    "滑模施工", "滑模安装", "滑模拆除",
    "级配碎石", "水稳层", "沥青铺设", "路缘石",
    "排水沟", "排洪沟", "护坡",
    "柱钢筋", "梁钢筋", "板钢筋", "墙钢筋",
    "框架柱", "构造柱",
    "抹灰", "防水施工", "保温施工",
    "焊接", "螺栓紧固", "找正就位",
    "非标制安", "组对焊接", "吊装就位",
    # 中等长度（2-3字核心动词）
    "开挖", "回填", "浇筑", "灌注", "绑扎", "安装", "砌筑", "搭设",
    "铺设", "焊接", "组对", "吊装", "钻进", "拆除",
    "养护", "拆模", "支模", "翻模", "爬模",
]

# 需要过滤的低信息量动作
FILTER_ACTIONS = {"降尘", "打扫", "保洁", "杂工", "打磨", "清理", "除锈", "刷漆",
                  "完成", "开始", "进行", "实施", "继续", "推进", "施工"}


def _extract_core_action(text):
    """提取核心施工动作"""
    found = []
    for verb in CORE_VERBS:
        if verb in text and verb not in FILTER_ACTIONS:
            idx = text.index(verb)
            start = max(0, idx - 2)
            end = min(len(text), idx + len(verb) + 2)
            found.append((verb, len(verb)))

    if found:
        found.sort(key=lambda x: -x[1])  # 最长匹配优先
        return found[0][0]

    # 回退：更宽泛的关键词匹配
    for verb in ["安装", "浇筑", "绑扎", "砌筑", "搭设", "焊接", "吊装", "回填", "开挖"]:
        if verb in text:
            return verb

    return None  # 如果没匹配到有效动作，返回 None


def _split_actions(text):
    """从文本中提取所有可能的动作短语（用分号或逗号分隔的子句）"""
    actions = []
    parts = re.split(r'[；;。，,\s]{1,2}', text)
    for part in parts:
        part = part.strip()
        if len(part) >= 4:
            core = _extract_core_action(part)
            if core and core not in FILTER_ACTIONS:
                actions.append(core)
    if not actions:
        core = _extract_core_action(text)
        if core and core not in FILTER_ACTIONS:
            actions.append(core)
    return actions


def _deduplicate_actions(actions):
    """去重并保留顺序"""
    seen = set()
    result = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            result.append(a)
    return result


def build_action_profile(df):
    """
    为每个路径建立动作画像：
    - 所有出现过的动作短语及频率
    - 按工种类别的动作分布
    - 典型数量范围
    """
    profile = {}

    for path in df["path"].unique():
        if path == "未分类" or pd.isna(path):
            continue
        pdf = df[df["path"] == path]

        # 收集所有动作短语
        all_actions = []
        for text in pdf["text"]:
            actions = _split_actions(text)
            all_actions.extend(actions)

        action_counts = Counter(all_actions)

        # 按工种类别分组
        by_work_cat = defaultdict(list)
        for _, row in pdf.iterrows():
            for text_part in re.split(r'[；;。，,\s]{1,2}', row["text"]):
                text_part = text_part.strip()
                if len(text_part) >= 4:
                    core = _extract_core_action(text_part)
                    if core:
                        by_work_cat[row.get("primary_work", "其他")].append(core)

        # 数量统计
        qty_vals = pdf["quantity_value"].dropna()
        qty_stats = {}
        if len(qty_vals) > 0:
            qty_stats = {
                "mean": round(float(qty_vals.mean()), 1),
                "median": round(float(qty_vals.median()), 1),
                "p25": round(float(qty_vals.quantile(0.25)), 1),
                "p75": round(float(qty_vals.quantile(0.75)), 1),
                "max": round(float(qty_vals.max()), 1),
            }

        # 条目数统计
        items_per_day = pdf.groupby("date").size()

        profile[path] = {
            "total_items": len(pdf),
            "active_days": pdf["date"].nunique(),
            "top_actions": [(a, c) for a, c in action_counts.most_common(30)],
            "actions_by_work": {
                cat: Counter(acts).most_common(15)
                for cat, acts in by_work_cat.items()
            },
            "quantity_stats": qty_stats,
            "avg_items_per_day": round(float(items_per_day.mean()), 1) if len(items_per_day) > 0 else 0,
        }

    return profile


def build_action_transitions(df):
    """
    为每个路径构建动作转移矩阵。
    在同一路径内，按日期排序的条目序列中，
    统计动作A后面出现动作B的概率。
    """
    transitions = {}

    for path in df["path"].unique():
        if path == "未分类" or pd.isna(path):
            continue
        pdf = df[df["path"] == path].sort_values(["date", "item_order"])

        # 收集该路径的动作序列
        action_seq = []
        for _, row in pdf.iterrows():
            actions = _split_actions(row["text"])
            action_seq.extend(actions)

        action_seq = _deduplicate_actions(action_seq)

        if len(action_seq) < 2:
            continue

        # 构建转移计数
        trans_count = defaultdict(Counter)
        for i in range(len(action_seq) - 1):
            trans_count[action_seq[i]][action_seq[i+1]] += 1

        # 转为概率
        trans_prob = {}
        for a, next_counts in trans_count.items():
            total = sum(next_counts.values())
            trans_prob[a] = {
                b: round(c / total, 3)
                for b, c in next_counts.most_common(10)
            }

        # 起始动作（每天的第一条）
        first_actions = []
        for date in sorted(pdf["date"].unique()):
            day_items = pdf[pdf["date"] == date].sort_values("item_order")
            if len(day_items) > 0:
                acts = _split_actions(day_items.iloc[0]["text"])
                if acts:
                    first_actions.append(acts[0])
        first_counter = Counter(first_actions)

        transitions[path] = {
            "transitions": trans_prob,
            "common_first_actions": first_counter.most_common(10),
            "total_actions": len(action_seq),
        }

    return transitions


def build_recent_context(df):
    """
    为每个路径找出"最近在做什么"的模式。
    用于预测下一步最可能的具体动作。
    """
    context = {}

    for path in df["path"].unique():
        if path == "未分类" or pd.isna(path):
            continue
        pdf = df[df["path"] == path].sort_values(["date", "item_order"])

        # 收集所有 action sequence
        action_seq = []
        date_seq = []
        for _, row in pdf.iterrows():
            acts = _split_actions(row["text"])
            for a in acts:
                action_seq.append(a)
                date_seq.append(row["date"])

        action_seq = _deduplicate_actions(action_seq)

        # 最近N个动作（从最新数据取）
        recent_n = min(20, len(action_seq))
        recent_actions = action_seq[-recent_n:] if recent_n > 0 else []

        context[path] = {
            "recent_actions": recent_actions[-10:],  # 最近10个
            "all_actions": action_seq[-50:],  # 最近50个
            "active_dates": sorted(pdf["date"].unique())[-10:],
        }

    return context


def save_artifacts(profile, transitions, recent_context, model_dir="models/sequences"):
    """保存所有工件"""
    os.makedirs(model_dir, exist_ok=True)

    # 路径动作画像
    with open(os.path.join(model_dir, "path_action_profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    # 动作转移关系
    with open(os.path.join(model_dir, "path_action_transitions.json"), "w", encoding="utf-8") as f:
        json.dump(transitions, f, ensure_ascii=False, indent=2)

    # 最近上下文
    with open(os.path.join(model_dir, "path_recent_context.json"), "w", encoding="utf-8") as f:
        json.dump(recent_context, f, ensure_ascii=False, indent=2)

    meta = {
        "trained_date": datetime.now().isoformat(),
        "paths": len(profile),
        "files": ["path_action_profile.json", "path_action_transitions.json", "path_recent_context.json"],
    }
    with open(os.path.join(model_dir, "action_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"动作序列工件已保存到 {model_dir}/")
    print(f"  路径数: {len(profile)}")
    for p in sorted(profile.keys()):
        top3 = [a for a, c in profile[p]["top_actions"][:5]]
        print(f"  {p}: top actions = {top3}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="路径动作挖掘")
    parser.add_argument("--input", default=None, help="path_activity_items.csv 路径")
    parser.add_argument("--model-dir", default=None, help="模型输出目录")
    args = parser.parse_args()

    base_dir = os.path.join(os.path.dirname(__file__), "..")
    if args.input:
        input_path = args.input
    else:
        input_path = os.path.join(base_dir, "data", "processed", "path_activity_items.csv")

    if args.model_dir:
        model_dir = args.model_dir
    else:
        model_dir = os.path.join(base_dir, "models", "sequences")
    model_dir = os.path.abspath(model_dir)

    print("=" * 60)
    print("  路径动作挖掘")
    print("=" * 60)

    df = pd.read_csv(input_path, encoding="utf-8-sig")
    print(f"\n数据: {len(df)} 条, {df['path'].nunique()} 个路径")

    # 构建画像
    print("\n[1/3] 构建动作画像...")
    profile = build_action_profile(df)

    # 构建转移关系
    print("[2/3] 构建动作转移...")
    transitions = build_action_transitions(df)

    # 最近上下文
    print("[3/3] 提取最近上下文...")
    recent = build_recent_context(df)

    # 保存
    save_artifacts(profile, transitions, recent, model_dir)
    print("\n完成！")


if __name__ == "__main__":
    main()
