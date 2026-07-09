"""
施工活动模板解析模块

从施工活动描述文本中提取：
  - 子项/区域分类（sub）
  - 具体数量信息（qty dict，如 {"根数": 5}）

用于 process_daily.py 的日报解析流程。
"""

import re

# ---- 子项区域关键词（与 process_daily.py 的 SUB_PROJECTS 对齐） ----
SUB_PROJECT_KEYWORDS = {
    "烧成窑尾":    ["窑尾", "C2", "C3", "C4", "C5", "C6", "分解炉", "烟室", "预热器", "旋风筒"],
    "烧成窑头":    ["窑头", "篦冷机", "窑头罩", "斜拉链"],
    "烧成窑中":    ["窑中", "回转窑", "三次风管", "窑墩", "墩柱", "墩身"],
    "原料粉磨":    ["原料磨", "原料粉磨", "辊压机", "废气处理", "袋收尘", "大风管非标", "窑尾袋收尘"],
    "水泥粉磨":    ["水泥磨", "水泥粉磨", "选粉机", "旋风筒", "出料罩", "电动葫芦", "砂浆墩", "辊压机提升机"],
    "水泥储存":    ["水泥库", "水泥仓", "太极锥", "水泥储存"],
    "煤粉制备":    ["煤磨", "煤粉", "煤立磨", "煤粉仓", "原煤卸车", "原煤堆场", "原煤"],
    "辅料堆场":    ["辅料", "堆棚", "堆场", "预均化", "取料机", "石灰石"],
    "原料配料":    ["原料配料", "配料站.*原料", "原料.*配料"],
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
    "厂区道路":    ["道路", "挡墙", "排洪沟", "进场路", "临时便道", "挡土墙", "路基", "路面"],
    "桩基工程":    ["桩基", "打桩", "灌注桩", "旋挖", "桩位", "破桩", "桩头"],
    "生料库":      ["生料库", "生料均化", "均化库", "生料仓", "滑模"],
    "机修车间":    ["机修", "机电修"],
    "中控楼":      ["中控楼", "控制楼", "综合楼"],
    "综合办公楼":  ["办公楼", "办公区"],
    "厂前区":      ["厂前区", "倒班楼", "食堂"],
    "石膏堆棚":    ["石膏堆棚"],
    "水泥包装":    ["水泥包装"],
}


def _classify_sub(text):
    """根据施工描述文本，识别所属子项区域。使用最长匹配策略。"""
    hits = []
    for sub, keywords in SUB_PROJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                hits.append((sub, len(kw)))
    if not hits:
        return "未分类"
    # 最长关键词匹配优先
    hits.sort(key=lambda x: -x[1])
    return hits[0][0]


def _extract_quantity(text):
    """
    从施工描述中提取数量信息。
    返回 dict，可能包含: 根数, 米, 方, 吨, 台, 个 等
    """
    qty = {}

    # 桩基/根数模式
    # 优先匹配 "累计完成XX根" → 取第一个数字
    # "累计完成72根，总计79根" → 取72（本期完成量）
    pile_patterns = [
        r'(?:累计(?:完成)?|已完成?|完成|施工|钻进|灌注|打桩|破桩)\s*(\d+(?:\.\d+)?)\s*根',
        r'(\d+(?:\.\d+)?)\s*根(?:\s*(?:桩|灌注桩|管桩|PHC|预应力))',
    ]
    for pat in pile_patterns:
        match = re.search(pat, text)
        if match:
            qty["根数"] = int(match.group(1))
            break

    # 米/长度模式
    meter_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:米|m)', text, re.IGNORECASE)
    if meter_matches:
        qty["米"] = sum(float(n) for n in meter_matches)

    # 方/体积模式
    cube_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:方|m³)', text)
    if cube_matches:
        qty["方"] = sum(float(n) for n in cube_matches)

    # 吨/重量
    ton_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:吨|t)', text, re.IGNORECASE)
    if ton_matches:
        qty["吨"] = sum(float(n) for n in ton_matches)

    # 台/设备数量
    unit_matches = re.findall(r'(\d+)\s*台', text)
    if unit_matches:
        qty["台"] = sum(int(n) for n in unit_matches)

    # 个/通用数量
    ge_matches = re.findall(r'(\d+)\s*个', text)
    if ge_matches:
        qty["个"] = sum(int(n) for n in ge_matches)

    return qty if qty else None


def parse_activity_line(text):
    """
    解析一条施工活动描述，返回 (sub, qty)。

    参数:
        text: str - 施工活动描述，如 "桩基工程：窑头A区累计完成72根，总计79根"
    返回:
        sub: str - 子项区域名称
        qty: dict or None - 数量信息，如 {"根数": 72}，无匹配时返回 None
    """
    if not text or not isinstance(text, str):
        return "未分类", None

    sub = _classify_sub(text)
    qty = _extract_quantity(text)

    return sub, qty
