"""
路径级预测模块（v2 — 基于具体施工动作）

根据历史日报中每个路径的真实施工动作序列，
预测当前活跃路径下一步最可能的具体施工内容。

输入：周级DataFrame（来自 process_daily）+ path_activity_items.csv
输出：每个活跃路径的 report_line，包含具体施工动作描述
"""
import os, sys, re, json
from collections import defaultdict, Counter
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))

CAT_LABELS = ["土建", "钢结构", "设备安装", "装修"]
SUB_SKIP = {"sub_count", "sub_diversity", "sub_entropy", "cum_sub_areas", "new_sub_areas"}


def _get_model_dir():
    return os.path.join(os.path.dirname(__file__), "..", "models", "sequences")


def _get_data_dir():
    return os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def _load_artifacts():
    """加载动作画像和转移关系"""
    model_dir = _get_model_dir()
    profile = {}
    transitions = {}
    recent_ctx = {}
    work_profile = {}

    # 动作画像
    pp = os.path.join(model_dir, "path_action_profile.json")
    if os.path.exists(pp):
        with open(pp, "r", encoding="utf-8") as f:
            profile = json.load(f)

    # 转移关系
    tp = os.path.join(model_dir, "path_action_transitions.json")
    if os.path.exists(tp):
        with open(tp, "r", encoding="utf-8") as f:
            transitions = json.load(f)

    # 最近上下文
    rp = os.path.join(model_dir, "path_recent_context.json")
    if os.path.exists(rp):
        with open(rp, "r", encoding="utf-8") as f:
            recent_ctx = json.load(f)

    # 工种画像
    wp = os.path.join(model_dir, "sub_work_profile.json")
    if os.path.exists(wp):
        with open(wp, "r", encoding="utf-8") as f:
            work_profile = json.load(f)

    return profile, transitions, recent_ctx, work_profile


def _load_items_df():
    """加载施工条目CSV"""
    path = os.path.join(_get_data_dir(), "path_activity_items.csv")
    if os.path.exists(path):
        return pd.read_csv(path, encoding="utf-8-sig")
    return None


def _get_active_sub_areas(weekly_df):
    """提取当前活跃的子区域"""
    sub_cols = [c for c in weekly_df.columns
                if c.startswith("sub_") and c not in SUB_SKIP]
    last_row = weekly_df.iloc[-1]
    active = {}
    for col in sub_cols:
        name = col.replace("sub_", "")
        val = float(last_row.get(col, 0))
        if val > 0:
            # 计算 age
            series = weekly_df[col].values
            first_idx = next((i for i, v in enumerate(series) if v > 0), 0)
            age = len(series) - 1 - first_idx
            active[name] = {"intensity": val, "age_weeks": age}
    return active


def _get_recent_actions_for_path(items_df, path, project_code=None, n_weeks=3):
    """获取某个路径最近N周的施工动作"""
    if items_df is None:
        return []

    df = items_df[items_df["path"] == path].copy()
    if project_code:
        pdf = df[df["project_code"] == project_code]
        if len(pdf) > 0:
            df = pdf

    if len(df) == 0:
        return []

    df = df.sort_values(["date", "item_order"])
    # 取最近的动作
    recent = df.tail(n_weeks * 5)  # 大约最近3周，每天1-2条

    actions = []
    for _, row in recent.iterrows():
        text = str(row["text"])
        phrases = str(row.get("action_phrases", "")).split("|")
        for p in phrases:
            p = p.strip()
            if p and len(p) >= 2 and p not in actions:
                # 过滤低信息量动作
                if p not in {"降尘", "保洁", "打磨", "清理", "除锈", "刷漆", "打扫", "杂工"}:
                    actions.append(p)
        # 如果 action_phrases 为空，从 text 中提取核心动作
        if not phrases or phrases == [""]:
            short = re.findall(r'[一-鿿]{2,6}(?:安装|绑扎|浇筑|砌筑|搭设|开挖|回填|焊接|吊装|施工|制作|铺设|拆除|防水|保温)', text)
            for s in short:
                if s not in actions and s not in {"降尘", "保洁", "打磨", "清理", "除锈", "刷漆", "打扫", "杂工", "完成", "进行", "开始", "继续"}:
                    actions.append(s)

    return actions[-15:] if len(actions) > 15 else actions


def _predict_next_actions(path, profile, transitions, recent_actions, work_profile):
    """
    预测该路径下一步最可能的动作。
    综合：转移关系 > 路径专属高频 > 工种阶段动作 > 最近未出现的 > 全部高频
    用 IDF 思想：路径间通用的动作降权，路径专属的动作提权。
    """
    pp = profile.get(path, {})
    top_actions = pp.get("top_actions", [])  # [(action, count), ...]
    trans_data = transitions.get(path, {}).get("transitions", {})

    # 统计每个动作出现在多少个路径中（IDF 思想）
    path_count = defaultdict(int)
    for pname, pdata in profile.items():
        for a, _ in pdata.get("top_actions", []):
            path_count[a] += 1
    total_paths = max(len(profile), 1)

    predicted = []

    # 策略1: 转移预测（高分）
    for ra in reversed(recent_actions[-5:]):
        if ra not in trans_data:
            continue
        for next_a, prob in trans_data[ra].items():
            if next_a in [p[0] for p in predicted]:
                continue
            # 加分：最近没出现过
            bonus = 0.2 if next_a not in recent_actions[-3:] else 0
            # 加分：路径专属度高（出现路径数少）
            rarity = 1.0 - (path_count.get(next_a, total_paths) / total_paths)
            score = prob + bonus + rarity * 0.3
            predicted.append((next_a, min(score, 1.0), f"转移:{ra}→{next_a}"))

    # 策略2: 路径高频 + 最近没出现过
    for a, count in top_actions[:20]:
        if a in [p[0] for p in predicted]:
            continue
        if a in recent_actions[-5:]:
            continue  # 最近做过了，预测价值低
        rarity = 1.0 - (path_count.get(a, total_paths) / total_paths)
        score = 0.3 + rarity * 0.4 + min(count / 200, 0.3)
        predicted.append((a, min(score, 1.0), f"高频:{path}"))

    # 策略3: 基于工种阶段推断（从 work_profile 取当前阶段主导工种的动作）
    wp = work_profile.get(path, {})
    age_profile = wp.get("age_profile", {})
    # 用 top_actions 的前几个作为兜底
    if len(predicted) < 3:
        for a, count in top_actions[:10]:
            if a not in [p[0] for p in predicted]:
                predicted.append((a, 0.2, f"兜底:{path}"))

    # 去重排序
    seen = set()
    result = []
    for a, prob, reason in sorted(predicted, key=lambda x: -x[1]):
        if a not in seen and len(a) >= 2:
            seen.add(a)
            result.append({"action": a, "confidence": round(prob, 3), "source": reason})
        if len(result) >= 5:
            break

    return result


def _generate_report_line(path, recent_actions, next_actions, profile):
    """生成自然语言的路径预测描述"""
    pp = profile.get(path, {})

    NOISE = {"降尘", "打磨", "保洁", "清理", "除锈", "刷漆", "打扫", "杂工",
             "完成", "进行", "开始", "继续", "施工"}

    # 预测的下一步动作（排噪声）
    next_names = [a["action"] for a in next_actions[:5]
                  if a["action"] not in NOISE]

    # 判断是新开还是延续：看最近动作和预测动作的重叠度
    recent_set = set(recent_actions[-5:]) if recent_actions else set()
    new_actions = [a for a in next_names if a not in recent_set]
    continuing = [a for a in next_names if a in recent_set]

    # 根据预测是否为新动作选择措辞
    if new_actions and len(new_actions) >= 2:
        tmpl = "{path}：下一阶段将推进{actions}，约{n}项作业。"
    elif new_actions:
        mixed = new_actions + continuing[:2]
        tmpl = "{path}：预计转入{actions}，约{n}项作业。"
        next_names = mixed
    elif continuing and len(continuing) >= 2:
        tmpl = "{path}：继续推进{actions}，约{n}项作业。"
        next_names = continuing
    elif next_names:
        tmpl = "{path}：预计安排{actions}，约{n}项作业。"
    else:
        # 回退到 top_actions
        fallback = [a for a, c in pp.get("top_actions", [])[:3]]
        if fallback:
            return f"{path}：按计划推进，预计{','.join(fallback)}。"
        return f"{path}：按计划推进。"

    avg_items = pp.get("avg_items_per_day", 2)
    n = max(2, round(avg_items))

    return tmpl.format(
        path=path,
        actions="、".join(next_names[:3]),
        n=n,
    )


def predict_sequences(weekly_df, model_dir=None):
    """
    给定周级数据，预测当前活跃路径的具体施工内容。
    """
    profile, transitions, recent_ctx, work_profile = _load_artifacts()
    items_df = _load_items_df()

    if not profile:
        return {
            "project_phase": "unknown",
            "active_paths": [],
            "warning": "动作画像不存在，请先运行 extract_items.py + mine_actions.py",
        }

    active_subs = _get_active_sub_areas(weekly_df)
    project_code = weekly_df.iloc[-1].get("project_code", "UPLOAD")

    # 判断项目阶段
    last_row = weekly_df.iloc[-1]
    cat_install = float(last_row.get("cat_设备安装", 0))
    cat_total = sum(float(last_row.get(f"cat_{l}", 0)) for l in CAT_LABELS)
    install_ratio = cat_install / max(cat_total, 1)
    if install_ratio < 0.25:
        phase = "early"
    elif install_ratio > 0.5:
        phase = "late"
    else:
        phase = "mid"

    results = []
    for path_name, info in sorted(active_subs.items(), key=lambda x: -x[1]["intensity"]):
        pp = profile.get(path_name)
        if not pp:
            continue

        # 获取该路径最近的真实动作
        recent_actions = _get_recent_actions_for_path(items_df, path_name, project_code)

        # 预测下一步动作
        next_actions = _predict_next_actions(path_name, profile, transitions, recent_actions, work_profile)

        # 生成报告行
        report_line = _generate_report_line(path_name, recent_actions, next_actions, profile)

        # 置信度
        confidence = round(
            (next_actions[0]["confidence"] if next_actions else 0.3)
            * min(1.0, len(recent_actions) / 5),
            2
        )

        results.append({
            "name": path_name,
            "current_intensity": info["intensity"],
            "age_weeks": info["age_weeks"],
            "recent_actions": recent_actions[-8:],
            "next_actions": next_actions,
            "predicted_quantity": pp.get("quantity_stats", {}),
            "confidence": confidence,
            "report_line": report_line,
        })

    results.sort(key=lambda x: x["current_intensity"], reverse=True)

    return {
        "project_phase": phase,
        "active_paths": results,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="路径级预测")
    parser.add_argument("--project", "-p", default="P001", help="项目代码")
    args = parser.parse_args()

    from mine_sequences import load_weekly_data
    df = load_weekly_data()
    df = df[df["project_code"] == args.project].sort_values("week_num")

    if len(df) == 0:
        print(f"项目 {args.project} 不存在")
        return

    result = predict_sequences(df)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
