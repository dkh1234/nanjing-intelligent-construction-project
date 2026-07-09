"""
合同信息提取模块

从施工合同文本中提取关键结构化字段。
- extract_contract_fields(text) → 规则提取所有字段
- 字段: 项目名称、合同编号、发包人、承包人、开工日期、竣工日期、
        合同工期、合同金额、工程地点、工程范围
"""
import re
from datetime import datetime, timedelta


# ============================================================
# 正则模式库
# ============================================================

# 日期模式
_DATE_RE = re.compile(r"(\d{4})\s*[-/年]\s*(\d{1,2})\s*[-/月]\s*(\d{1,2})\s*[日]?")

# 金额模式: 支持 1,234.56万元 / 5000万元 / 123.45亿 / 1000000元
_AMOUNT_RE = re.compile(
    r"(\d[\d,.]*)\s*(万|亿)?\s*元"
)

# ---- 所有字段关键词（用于截断上下文边界） ----
_ALL_KEYWORDS = [
    "工程名称", "项目名称",
    "合同编号", "编号", "合同号",
    "发包人", "甲方", "业主", "建设单位", "招标人",
    "承包人", "乙方", "承包商", "施工单位", "中标人",
    "统一社会信用代码", "法定代表人", "联系电话", "开户行", "账号", "项目经理",
    "计划开工日期", "开工日期", "计划开工", "施工开始",
    "计划竣工日期", "竣工日期", "计划竣工", "竣工时间", "完工日期",
    "合同工期", "工期", "总工期", "计划工期", "施工总工期",
    "签约合同价", "合同价款", "合同总价", "中标价", "合同金额", "工程造价", "价款",
    "工程地点", "建设地点", "项目地点", "工程地址", "项目地址", "建设地址",
    "工程范围", "承包范围", "工程内容", "建设内容", "施工范围", "工作内容",
    "建设规模", "建设内容", "项目概况", "工程规模", "生产规模", "设计规模", "项目规模",
    "质量要求", "质量标准", "质量目标", "质量等级",
    "签订日期", "签约日期", "合同签订日期",
    "监理人", "监理单位", "监理工程师",
    "缺陷责任期", "质量保修期", "保修期",
]


def _truncate_at_boundary(text, current_keyword=""):
    """在遇到下一个字段关键词处截断文本，防止字段值越界。"""
    if not text or not isinstance(text, str):
        return text
    # 短值不截断（合同编号、日期、金额等）
    if len(text) < 30:
        return text
    best_pos = len(text)
    for kw in _ALL_KEYWORDS:
        if kw == current_keyword:
            continue
        pos = text.find(kw)
        if pos != -1 and pos < best_pos:
            best_pos = pos
    # 截断并去除尾部非完整句
    if best_pos < len(text):
        text = text[:best_pos]
    return text.rstrip("0123456789. 、-").strip()


# ---- 字段提取器: (字段名, 关键词列表, 提取正则, 上下文窗口) ----

FIELD_PATTERNS = {
    "project_name": {
        "keywords": ["工程名称", "项目名称"],
        "context_before": 0,
        "context_after": 100,
        "clean": lambda v: _clean_field(v),
    },
    "contract_no": {
        "keywords": ["合同编号", "编号", "合同号"],
        "context_before": 0,
        "context_after": 60,
        "pattern": re.compile(
            r"[A-Za-z0-9]{1,8}\s*[\(\（][A-Za-z0-9\s\-\[\]【】（）\(\)]{2,40}"
        ),
        "clean": lambda v: v.strip().lstrip("：:："),
    },
    "party_a": {
        "keywords": ["发包人", "甲方", "业主", "建设单位", "招标人"],
        "context_before": 0,
        "context_after": 500,
        "clean": lambda v: _clean_party(v),
    },
    "party_a_detail": {
        "keywords": ["发包人", "甲方", "业主", "建设单位", "招标人"],
        "context_before": 0,
        "context_after": 800,
        "clean": lambda v: _extract_kv_pairs(v),
    },
    "party_b": {
        "keywords": ["承包人", "乙方", "承包商", "施工单位", "中标人"],
        "context_before": 0,
        "context_after": 500,
        "clean": lambda v: _clean_party(v),
    },
    "party_b_detail": {
        "keywords": ["承包人", "乙方", "承包商", "施工单位", "中标人"],
        "context_before": 0,
        "context_after": 800,
        "clean": lambda v: _extract_kv_pairs(v),
    },
    "start_date": {
        "keywords": ["计划开工日期", "开工日期", "计划开工", "施工开始",
                     "开工时间", "开始施工", "进场日期", "动工日期",
                     "开工", "启动日期"],
        "context_before": 0,
        "context_after": 40,
        "pattern": _DATE_RE,
        "clean": lambda v: _format_date(v),
    },
    "end_date": {
        "keywords": ["计划竣工日期", "竣工日期", "计划竣工", "竣工时间", "完工日期",
                     "完成日期", "交工日期", "结束日期", "验收日期",
                     "竣工", "完工", "交付日期"],
        "context_before": 0,
        "context_after": 40,
        "pattern": _DATE_RE,
        "clean": lambda v: _format_date(v),
    },
    "duration": {
        "keywords": ["合同工期", "工期", "总工期", "计划工期", "施工总工期"],
        "context_before": 0,
        "context_after": 40,
        "pattern": re.compile(r"(\d+)\s*(天|日历天|日|个月|月)"),
        "clean": lambda v: _parse_duration(v),
    },
    "contract_amount": {
        "keywords": ["签约合同价", "合同价款", "合同总价",
                     "中标价", "合同金额", "工程造价", "工程总造价", "价款"],
        "context_before": 0,
        "context_after": 60,
        "pattern": _AMOUNT_RE,
        "clean": lambda v: _parse_amount(v),
    },
    "construction_scale": {
        "keywords": ["建设规模", "工程规模", "建设内容", "生产规模",
                     "设计规模", "项目规模"],
        "context_before": 0,
        "context_after": 200,
        "clean": lambda v: _clean_field(v),
    },
    "quality_standard": {
        "keywords": ["质量要求", "质量标准", "质量目标", "质量等级"],
        "context_before": 0,
        "context_after": 100,
        "clean": lambda v: _clean_field(v),
    },
    "signing_date": {
        "keywords": ["签订日期", "签约日期", "合同签订日期", "订立日期",
                     "签署日期", "签订时间", "签约时间", "订约日期"],
        "context_before": 0,
        "context_after": 30,
        "pattern": _DATE_RE,
        "clean": lambda v: _format_date(v),
    },
    "feed_date": {
        "keywords": ["计划投料时间", "计划投料日期", "投料时间", "投料日期"],
        "context_before": 0,
        "context_after": 30,
        "pattern": _DATE_RE,
        "clean": lambda v: _format_date(v),
    },
    "supervisor": {
        "keywords": ["监理人", "监理单位", "监理工程师"],
        "context_before": 0,
        "context_after": 80,
        "clean": lambda v: _clean_field(v),
    },
    "defect_period": {
        "keywords": ["缺陷责任期", "质量保修期", "保修期"],
        "context_before": 0,
        "context_after": 40,
        "pattern": re.compile(r"(\d+)\s*(天|日历天|日|个月|月|年)"),
        "clean": lambda v: _parse_duration(v),
    },
    "project_location": {
        "keywords": ["工程地点", "建设地点", "项目地点", "工程地址",
                     "项目地址", "建设地址"],
        "context_before": 0,
        "context_after": 100,
        "clean": lambda v: _clean_field(v),
    },
    "project_scope": {
        "keywords": ["工程范围", "承包范围", "工程内容", "建设内容",
                     "施工范围", "工作内容"],
        "context_before": 0,
        "context_after": 500,
        "clean": lambda v: _clean_field(v),
    },
}


def _extract_kv_pairs(text):
    """从文本块中提取所有'标签：值'对，返回 dict。支持空格/换行分隔的字段。"""
    if not text:
        return {}
    pairs = {}

    # 所有已知子字段标签（按长度降序，先匹配长标签避免短标签误匹配））
    _LABELS = [
        "统一社会信用代码", "现场执行经理", "法定代表人", "法人代表",
        "联系电话", "联系方式", "通讯地址", "注册地址", "单位地址",
        "开户银行", "银行账号", "银行帐号", "项目经理", "项目负责人",
        "邮政编码", "开户行", "建造师", "电话", "传真", "地址",
        "账号", "账户", "邮编", "法人",
    ]
    # 按长度降序排列
    _LABELS.sort(key=len, reverse=True)

    # 在文本中查找所有标签位置
    positions = []
    for label in _LABELS:
        # 匹配 "标签：" 或 "标签:"
        for m in re.finditer(re.escape(label) + r"\s*[：:]", text):
            positions.append((m.start(), label))

    # 按位置排序
    positions.sort()

    # 提取每个标签后面的值（到下一个标签或文本末尾）
    for i, (pos, label) in enumerate(positions):
        # 跳过标签本身
        val_start = pos + len(label)
        # 跳过冒号
        while val_start < len(text) and text[val_start] in "：: \t":
            val_start += 1
        # 值结束位置 = 下一个标签的起始位置，或文本末尾
        if i + 1 < len(positions):
            val_end = positions[i + 1][0]
        else:
            val_end = len(text)
        val = text[val_start:val_end].strip().rstrip("，。,\t ")
        if val and len(val) > 1 and label not in pairs:
            pairs[label] = val

    return pairs if pairs else None


def _clean_field(value):
    """清除提取字段中的冒号、括号前缀等格式字符。"""
    value = value.strip()
    # 去掉各种前缀符号
    value = re.sub(r"^[）\)：:\s]+", "", value)
    value = re.sub(r"^（[^）]*）[：:\s]*", "", value)
    value = re.sub(r"^\([^)]*\)[：:\s]*", "", value)
    value = re.split(r"[\n\r；;，。]", value)[0]
    value = value.strip()
    # 如果清洗后只剩括号/符号，返回空
    if re.match(r"^[）\)（\(：:\s]+$", value):
        return ""
    return value


def _clean_party(value):
    """清除当事人名称中无关的格式字符。"""
    value = value.strip()
    value = re.sub(r"^[）\)：:\s]+", "", value)
    value = re.sub(r"^（[^）]*）[：:\s]*", "", value)
    value = re.sub(r"^\([^)]*\)[：:\s]*", "", value)
    value = re.split(r"[\n\r；;，。]", value)[0]
    value = value.strip()
    # 如果清洗后只剩括号/符号/冒号，返回空触发多行回退
    if not value or re.match(r"^[）\)（\(：:\s]+$", value):
        return ""
    return value


def _format_date(match_str):
    """将日期匹配结果格式化为 YYYY-MM-DD。"""
    m = _DATE_RE.search(match_str)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def _parse_duration(match_str):
    """解析工期文本，统一返回天数。"""
    m = re.search(r"(\d+)\s*(天|日历天|日|个月|月)", match_str)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if unit in ("个月", "月"):
            return num * 30  # 近似转换
        return num
    return None


def _parse_amount(match_str):
    """解析金额文本，统一返回元（数值）。"""
    m = _AMOUNT_RE.search(match_str)
    if m:
        num_str = m.group(1).replace(",", "")
        try:
            num = float(num_str)
        except ValueError:
            return None
        unit = m.group(2)
        if unit == "亿":
            num *= 100000000
        elif unit == "万":
            num *= 10000
        return round(num, 2)
    return None


# ============================================================
# 核心提取函数
# ============================================================

def extract_contract_fields(text):
    """
    从施工合同纯文本中提取结构化字段。

    参数:
        text: 合同文件提取的纯文本内容

    返回:
        dict: {
            "项目名称": {"value": "...", "source": "rule"},
            "合同编号": {"value": "...", "source": "rule"},
            "发包人":   {"value": "...", "source": "rule"},
            "承包人":   {"value": "...", "source": "rule"},
            "开工日期": {"value": "YYYY-MM-DD", "source": "rule"},
            "竣工日期": {"value": "YYYY-MM-DD", "source": "rule"},
            "合同工期": {"value": 365, "source": "rule"},
            "合同金额": {"value": 12345678.90, "source": "rule"},
            "工程地点": {"value": "...", "source": "rule"},
            "工程范围": {"value": "...", "source": "rule"},
        }
    """
    if not text or not isinstance(text, str):
        return {"error": "输入文本为空"}

    result = {}
    # 清理文本，保留更多上下文
    text_clean = text.replace("\r\n", "\n").replace("\r", "\n")

    for field_key, config in FIELD_PATTERNS.items():
        value = _extract_field(text_clean, config)
        if value is not None:
            result[field_key] = {"value": value, "source": "rule"}
        else:
            result[field_key] = {"value": None, "source": "rule"}

    # ---- 日期智能兜底 ----
    # Step A: 扫描全文所有日期，按上下文分类
    all_dates = []
    for m in _DATE_RE.finditer(text_clean):
        d = _format_date(m.group(0))
        if d:
            ctx_start = max(0, m.start() - 30)
            ctx_end = min(len(text_clean), m.end() + 30)
            ctx = text_clean[ctx_start:ctx_end]
            all_dates.append((d, ctx, m.start()))

    for d, ctx, pos in all_dates:
        # 开工
        if not result.get("start_date", {}).get("value"):
            if re.search(r"开工|开始施工|进场|动工|启动|开始日期|开工时间", ctx):
                result["start_date"] = {"value": d, "source": "inferred"}
                continue
        # 竣工
        if not result.get("end_date", {}).get("value"):
            if re.search(r"竣工|完工|交工|验收|交付|完成日期|竣工时间", ctx):
                result["end_date"] = {"value": d, "source": "inferred"}
                continue
        # 签订
        if not result.get("signing_date", {}).get("value"):
            if re.search(r"签订|签署|订立|签约", ctx):
                result["signing_date"] = {"value": d, "source": "inferred"}
                continue
        # 投料（兜底）
        if not result.get("feed_date", {}).get("value"):
            if re.search(r"投料", ctx):
                result["feed_date"] = {"value": d, "source": "inferred"}
                continue

    # Step B: 仍然缺失 start/end，直接用工期 + 投料时间推算
    start = result.get("start_date", {}).get("value")
    end = result.get("end_date", {}).get("value")
    feed = result.get("feed_date", {}).get("value")
    duration = result.get("duration", {}).get("value")

    # 有投料 + 工期 → 竣工=投料，开工=投料-工期
    if feed and duration and (not start or not end):
        try:
            feed_dt = datetime.strptime(feed, "%Y-%m-%d")
            if not end:
                result["end_date"] = {"value": feed_dt.strftime("%Y-%m-%d"), "source": "inferred"}
                end = feed_dt.strftime("%Y-%m-%d")
            if not start:
                inferred = feed_dt - timedelta(days=duration)
                result["start_date"] = {"value": inferred.strftime("%Y-%m-%d"), "source": "inferred"}
                start = inferred.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    # 有工期 + 1个日期 → 推算另一个
    if duration:
        try:
            if start and not end:
                s = datetime.strptime(start, "%Y-%m-%d")
                result["end_date"] = {"value": (s + timedelta(days=duration)).strftime("%Y-%m-%d"), "source": "inferred"}
            elif end and not start:
                e = datetime.strptime(end, "%Y-%m-%d")
                result["start_date"] = {"value": (e - timedelta(days=duration)).strftime("%Y-%m-%d"), "source": "inferred"}
        except (ValueError, TypeError):
            pass

    # Step C: 工期未直接匹配，尝试从全文找 "XX个月" 或 "XX天"
    if not duration:
        dur_matches = list(re.finditer(r"(\d+)\s*(个月|月|日历天|天|日)", text_clean))
        for dm in dur_matches:
            num = int(dm.group(1))
            unit = dm.group(2)
            days = num * 30 if unit in ("个月", "月") else num
            if 30 <= days <= 3000:  # 合理范围
                result["duration"] = {"value": days, "source": "inferred"}
                duration = days
                # 再次尝试推算
                if feed and not start:
                    try:
                        fd = datetime.strptime(feed, "%Y-%m-%d")
                        result["start_date"] = {"value": (fd - timedelta(days=days)).strftime("%Y-%m-%d"), "source": "inferred"}
                        result["end_date"] = {"value": feed, "source": "inferred"}
                    except:
                        pass
                break

    # 工期自动计算（竣工 - 开工）
    if (not duration and start and end):
        try:
            s = datetime.strptime(start, "%Y-%m-%d")
            e = datetime.strptime(end, "%Y-%m-%d")
            computed = (e - s).days
            if 30 <= computed <= 3000:
                result["duration"] = {"value": computed, "source": "computed"}
        except ValueError:
            pass

    return result


def _extract_field(text, config):
    """
    对单个字段执行关键词定位 + 上下文提取 + 模式匹配。

    策略:
    1. 在所有关键词中，找到第一个在文本中出现的位置
    2. 截取该位置附近的上下文窗口
    3. 如果有 pattern，在上下文窗口中匹配
    4. 否则返回清理后的上下文
    """
    # 1. 定位关键词
    best_pos = None
    best_kw = None
    for kw in config["keywords"]:
        pos = text.find(kw)
        if pos != -1 and (best_pos is None or pos < best_pos):
            best_pos = pos
            best_kw = kw

    if best_pos is None:
        return None

    # 2. 截取上下文窗口（从关键词末尾开始）
    start = best_pos + len(best_kw) + config.get("context_before", 0)
    end = start + config.get("context_after", 80)
    context = text[start:end]

    # 3. 尝试模式匹配（取离关键词最近的匹配））
    pattern = config.get("pattern")
    if pattern:
        matches = list(pattern.finditer(context))
        if matches:
            # 取第一个匹配（离关键词最近）
            m = matches[0]
            raw = m.group(0) if m.lastindex is None else context[m.start():m.end()]
            value = config["clean"](raw)
            value = _truncate_at_boundary(value)
            if value:
                return value
        # 如果没有匹配到模式，尝试取第一行有意义的内容
        first_line = context.strip().split("\n")[0].strip()
        if first_line and len(first_line) > 1:
            value = config["clean"](first_line)
            value = _truncate_at_boundary(value)
            if value:
                return value
        return None

    # 4. 无模式时返回清理后的上下文
    lines = [l.strip() for l in context.strip().split("\n") if l.strip()]
    if not lines:
        return None

    # 尝试取第一行
    cleaned = config["clean"](lines[0])
    # 如果第一行太短（只是标签），尝试合并第二行
    if (not cleaned or len(cleaned) < 3) and len(lines) >= 2:
        combined = lines[0].strip().rstrip("：:") + lines[1].strip()
        cleaned = config["clean"](combined)
    # 如果还是太短，直接用第二行
    if (not cleaned or len(cleaned) < 3) and len(lines) >= 2:
        cleaned = config["clean"](lines[1])

    if cleaned:
        cleaned = _truncate_at_boundary(cleaned)
    if cleaned and len(cleaned) >= 1:
        return cleaned
    return None


# ============================================================
# 导出字段名（中文，供前端展示）
# ============================================================

FIELD_LABELS = {
    "project_name": "项目名称",
    "contract_no": "合同编号",
    "party_a": "发包人（甲方）",
    "party_a_detail": "发包人详细信息",
    "party_b": "承包人（乙方）",
    "party_b_detail": "承包人详细信息",
    "start_date": "开工日期",
    "end_date": "竣工日期",
    "duration": "合同工期（天）",
    "contract_amount": "合同金额（元）",
    "construction_scale": "建设规模",
    "quality_standard": "质量要求",
    "signing_date": "合同签订日期",
    "feed_date": "计划投料时间",
    "supervisor": "监理人",
    "defect_period": "缺陷责任期（天）",
    "project_location": "工程地点",
    "project_scope": "工程范围",
}


def format_result(raw_result):
    """将提取结果转为中文 key 并添加标签信息。"""
    if "error" in raw_result:
        return raw_result

    formatted = {}
    for en_key, cn_label in FIELD_LABELS.items():
        field_data = raw_result.get(en_key, {"value": None, "source": "rule"})
        formatted[en_key] = {
            "value": field_data["value"],
            "source": field_data.get("source", "rule"),
            "label": cn_label,
        }
    return formatted
