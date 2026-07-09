"""
从天级日报原文中提取具体施工条目。

每个条目包含：
  project_code, date, week_num, path, work_category,
  item_order, text, action_phrases, quantity_type, quantity_value,
  cumulative_value, total_value, remaining_value

输出: data/processed/path_activity_items.csv
"""
import os, re, sys, json
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from utils import parse_date, week_boundaries


# ---- 路径识别关键词（与 process_daily.py 的 SUB_PROJECTS 对齐） ----
PATH_KEYWORDS = {
    "烧成窑尾": ["窑尾", "C2", "C3", "C4", "C5", "C6", "分解炉", "烟室", "预热器"],
    "烧成窑头": ["窑头", "篦冷机", "窑头罩", "斜拉链"],
    "烧成窑中": ["窑中", "回转窑", "三次风管", "窑墩"],
    "原料粉磨": ["原料磨", "原料粉磨", "辊压机", "废气处理", "袋收尘", "大风管非标", "窑尾袋收尘"],
    "水泥粉磨": ["水泥磨", "水泥粉磨", "选粉机", "旋风筒", "出料罩", "电动葫芦", "砂浆墩"],
    "水泥储存": ["水泥库", "水泥仓", "太极锥", "水泥储存"],
    "煤粉制备": ["煤磨", "煤粉", "煤立磨", "煤粉仓", "原煤卸车", "原煤堆场"],
    "辅料堆场": ["辅料", "堆棚", "堆场", "预均化", "取料机", "石灰石"],
    "原料配料": ["原料配料", "配料站.*原料", "原料.*配料"],
    "水泥配料": ["水泥配料", "配料站.*水泥"],
    "包装装车": ["包装", "装车", "水泥汽车散装"],
    "中控电气": ["中控", "电气", "照明", "开槽埋管", "中控楼"],
    "熟料库": ["熟料库", "熟料转运", "熟料储存"],
    "脱硫石膏": ["脱硫", "石膏", "混合材"],
    "压缩空气": ["压缩空气", "空压"],
    "循环水系统": ["循环水", "泵房", "水泵", "水处理"],
    "转运站": ["转运站"],
    "SCR脱硝": ["SCR", "脱硝"],
    "水泥汽车散装": ["汽车散装", "水泥散装"],
    "厂区道路": ["道路", "挡墙", "挡土墙", "排洪沟", "进场路", "临时便道", "路基", "路面"],
    "桩基工程": ["桩基", "打桩", "灌注桩", "旋挖", "桩位"],
    "机修车间": ["机修", "机电修"],
    "中控楼": ["中控楼", "控制楼", "综合楼"],
    "生料库": ["生料库", "生料均化", "均化库", "生料仓"],
    "综合办公楼": ["办公楼", "办公区", "综合楼"],
}

# ---- 工种类别关键词 ----
WORK_CATEGORIES = {
    "土建": ["开挖", "回填", "浇筑", "混凝土", "砼", "钢筋", "模板", "抹灰", "砌筑",
             "基槽", "基坑", "桩基", "桩头", "承台", "地面", "道路", "碾压",
             "拆除", "清理", "脚手架", "搭设", "绑扎", "打桩", "夯实", "垫层",
             "砌砖", "圈梁", "构造柱", "框架柱", "框架", "屋面", "女儿墙",
             "散装", "转运站", "输送地坑", "循环水池", "泵房", "挡土墙", "墙背"],
    "钢结构": ["钢结构", "钢构", "钢梁", "钢柱", "预埋件", "焊接", "牛腿", "框柱",
              "非标制作", "组对", "钢平台", "栏杆", "楼梯", "钢绞线", "门架",
              "屋面板", "彩板", "支撑", "支架", "网架", "檩条", "吊装"],
    "设备安装": ["安装", "设备", "管道", "风管", "电缆", "桥架", "配电", "机械",
               "非标件", "阀门", "选粉机", "收尘", "风机", "膨胀节",
               "取料机", "提升机", "包装机", "装车机", "除尘器",
               "轨道", "斗提", "螺旋", "输送", "料仓", "料斗",
               "冷却", "润滑", "液压"],
    "装修": ["装饰", "装修", "涂料", "防水", "保温", "门窗",
            "硅钙板", "气凝胶", "贴砖", "吊顶", "抹面",
            "涂刷", "油漆", "地坪", "瓷砖"],
}

# ---- 数量提取模式 ----
QUANTITY_PATTERNS = [
    (r'(?:完成|浇筑|安装|绑扎|砌筑|开挖|回填|铺设|施工|打桩|钻进|浇注|灌注)[^\d]{0,10}(\d+(?:\.\d+)?)\s*(?:根|米|m|方|m³|吨|t|个|台|套|处|道|条|段|跨|层|榀)', 'quantity'),
    (r'(\d+(?:\.\d+)?)\s*(?:根|米|m|方|m³|吨|t|个|台|套)', 'quantity'),
    (r'累计(?:完成)?\s*(\d+(?:\.\d+)?)\s*(?:根|米|m|方|m³|吨|t)', 'cumulative'),
    (r'总计\s*(\d+(?:\.\d+)?)\s*(?:根|米|m|方|m³|吨|t)', 'total'),
    (r'剩余\s*(\d+(?:\.\d+)?)\s*(?:根|米|m|方|m³|吨|t)', 'remaining'),
    (r'(?:完成|已完成)(\d+(?:\.\d+)?)\s*%', 'percent'),
    (r'(\d+(?:\.\d+)?)\s*%', 'percent'),
]

# ---- 施工动作短语模式 ----
ACTION_PATTERNS = [
    r'[一-鿿]{2,4}(?:开挖|回填|浇筑|绑扎|安装|砌筑|搭设|铺设|焊接|吊装|钻进|灌注|拆除|清理|打磨|喷涂|涂刷)',
    r'(?:基坑|基槽|垫层|承台|地梁|框架|筒体|墙体|楼板|屋面板|柱|梁|板|墙)(?:开挖|回填|浇筑|绑扎|安装|砌筑|施工)',
    r'(?:模板|钢筋|混凝土|砼|脚手架|预埋件|螺栓|管道|电缆|桥架|风管)(?:安装|绑扎|搭设|拆除|浇筑|制作|加工|焊接)',
    r'(?:非标|钢构|网架|檩条|彩板|栏杆|楼梯|平台)(?:制作|安装|焊接|组对|吊装)',
    r'(?:设备|机械|风机|泵|阀门|收尘器|提升机)(?:安装|调试|就位|找正)',
    r'(?:抹灰|防水|保温|涂料|油漆|地坪|贴砖|吊顶)(?:施工|作业|完成)',
]


def _classify_path(text):
    """识别文本所属路径/子区域"""
    hits = []
    for path, keywords in PATH_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                hits.append((path, len(kw)))  # 最长匹配优先
    if not hits:
        return "未分类"
    hits.sort(key=lambda x: -x[1])
    return hits[0][0]


def _classify_work(text):
    """识别工种类别"""
    hits = []
    for cat, keywords in WORK_CATEGORIES.items():
        if any(kw in text for kw in keywords):
            hits.append(cat)
    return hits if hits else ["其他"]


def _extract_quantities(text):
    """提取数量信息"""
    result = {"quantity": None, "cumulative": None, "total": None, "remaining": None, "percent": None, "unit": None}
    for pattern, qtype in QUANTITY_PATTERNS:
        m = re.search(pattern, text)
        if m:
            val = float(m.group(1))
            # 找单位
            unit_match = re.search(r'(根|米|m|方|m³|吨|t|个|台|套|处|道|条|段|跨|层|榀|%)', text[m.end()-5:m.end()+5])
            unit = unit_match.group(1) if unit_match else None
            result[qtype] = val
            if unit and not result["unit"]:
                result["unit"] = unit
    return result


def _extract_action_phrases(text):
    """从文本中提取施工动作短语（优先核心动词）"""
    phrases = []
    for pattern in ACTION_PATTERNS:
        for m in re.finditer(pattern, text):
            phrase = m.group(0)
            if len(phrase) >= 3 and phrase not in phrases:
                # 过滤低信息量动作
                if phrase not in {"降尘", "打扫", "保洁", "打磨", "清理", "除锈", "刷漆", "杂工", "完成", "进行"}:
                    phrases.append(phrase)
    return phrases[:5] if phrases else []


def _split_construction_section(text):
    """从日报文本中提取施工情况部分的各个条目"""
    # 找施工情况段落
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # 尝试匹配 "三、施工情况：" 或 "施工情况："
    match = re.search(
        r'(?:三[、\.．]\s*)?施工情况[：:]\s*\n?(.*?)(?=\n\s*(?:[四4五5][、\.．]|备注|$))',
        normalized, flags=re.S
    )
    if not match:
        return []
    body = match.group(1).strip()

    items = []
    # 按编号分割: "1.", "1、", "1)", "（1）", "1 ", etc.
    # 先按行分，再按行内编号分
    lines = body.split("\n")
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        # 跳过非条目行（如标题、空行）
        if re.match(r'^(?:[一二三四五六七八九十]|[土钢设装修]|[中水泥烧])', line) and '：' not in line and ':' not in line:
            continue

        # 在同一行内按编号分割
        parts = re.split(r'(?=(?:^|\s|，|。|；)(?:\d+[\.\、）)]\s*|（\d+）))', line)
        for part in parts:
            part = part.strip().rstrip("；;，,。.")
            if not part or len(part) < 5:
                continue
            # 去掉前导编号
            cleaned = re.sub(r'^(?:\d+[\.\、）)]\s*|（\d+）)\s*', '', part).strip()
            if len(cleaned) >= 5:
                items.append(cleaned)

    return items


def process_project(project_dir, project_code):
    """处理一个项目下所有日报，返回条目列表"""
    items = []
    if not os.path.isdir(project_dir):
        return items

    files = sorted([f for f in os.listdir(project_dir) if f.endswith('.txt')])

    for fname in files:
        fpath = os.path.join(project_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            text = f.read()

        # 解析日期
        date_str = parse_date(text[:200])
        if not date_str:
            # 从文件名推断
            base = fname.replace('.txt', '')
            try:
                date_str = base
                datetime.strptime(date_str[:10], '%Y-%m-%d')
            except:
                continue

        try:
            date_obj = pd.to_datetime(date_str)
        except:
            continue

        # 计算周数
        week_num = date_obj.isocalendar()[1]

        # 提取施工条目
        entry_texts = _split_construction_section(text)

        for i, entry_text in enumerate(entry_texts):
            path = _classify_path(entry_text)
            work_cats = _classify_work(entry_text)
            quantities = _extract_quantities(entry_text)
            action_phrases = _extract_action_phrases(entry_text)

            items.append({
                "project_code": project_code,
                "date": str(date_obj.date()),
                "week_num": week_num,
                "path": path,
                "work_category": "|".join(work_cats) if work_cats else "其他",
                "primary_work": work_cats[0] if work_cats else "其他",
                "item_order": i + 1,
                "text": entry_text[:200],  # 截断长文本
                "action_phrases": "|".join(action_phrases[:5]),
                "quantity_type": "根数" if quantities.get("unit") in ("根",) else (quantities.get("unit") or ""),
                "quantity_value": quantities["quantity"],
                "cumulative_value": quantities["cumulative"],
                "total_value": quantities["total"],
                "remaining_value": quantities["remaining"],
                "percent_complete": quantities["percent"],
            })

    return items


def main():
    import argparse
    parser = argparse.ArgumentParser(description="提取施工条目")
    parser.add_argument("--data-dir", default="data/daily", help="日报数据目录")
    parser.add_argument("--output", default=None, help="输出 CSV 路径")
    args = parser.parse_args()

    base_dir = os.path.join(os.path.dirname(__file__), "..")
    daily_dir = os.path.join(base_dir, args.data_dir)
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(base_dir, "data", "processed", "path_activity_items.csv")

    all_items = []
    for proj in sorted(os.listdir(daily_dir)):
        proj_dir = os.path.join(daily_dir, proj)
        if os.path.isdir(proj_dir):
            print(f"处理 {proj}...")
            items = process_project(proj_dir, proj)
            print(f"  提取 {len(items)} 条施工条目")
            all_items.extend(items)

    df = pd.DataFrame(all_items)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\n总计: {len(df)} 条")
    print(f"保存到: {output_path}")
    print(f"路径分布:")
    for p, c in df["path"].value_counts().head(15).items():
        print(f"  {p}: {c}")


if __name__ == "__main__":
    main()
