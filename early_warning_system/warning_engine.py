"""
预警核心逻辑 —— 三大预警维度的计算引擎
"""

from __future__ import annotations

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List, Dict, Tuple

from .models import (
    ProjectPlan,
    WeeklyReport,
    PlanMilestone,
    CriticalPathProcess,
    AlertLevel,
    MilestoneAlert,
    CriticalPathAlert,
    ProgressCurveAlert,
    WarningReport,
    MilestoneReportItem,
)


# ============================================================================
# 名称模糊匹配
# ============================================================================

def _normalize(name: str) -> str:
    """去掉数字序号前缀、空格、标点，仅保留中文/字母/数字用于匹配"""
    import re
    name = re.sub(r"^\d+[\.\、\s]+", "", name)
    name = name.replace(" ", "").replace("　", "")
    return name


def _match_keywords(report_key: str, plan_name: str) -> bool:
    """
    判断周报中的 key 是否与策划书中的名称匹配。
    规则：report_key 是 plan_name 的子串（去空格后），
    或 plan_name 关键词在 report_key 中，
    或两者有 ≥4 个连续相同字符（且占较短字符串的 ≥60%）。
    """
    rk = report_key.replace(" ", "").replace("　", "")
    pn = _normalize(plan_name)
    if rk in pn:
        return True
    if pn in rk:
        return True
    shorter = min(len(rk), len(pn))
    min_match = max(5, int(shorter * 0.6))  # 至少5个连续字符且 ≥ 短串的60%
    for i in range(len(rk) - min_match + 1):
        if rk[i:i + min_match] in pn:
            return True
    return False


# 工序级关键词：若 report key 包含这些词，说明是具体工序状态而非整车间状态
_PROCESS_KEYWORDS = ["桩基", "土建", "设备基础", "设备安装", "调试", "联动", "点火", "图纸"]


def _match_report_to_milestone(
    report_key: str,
    milestone: PlanMilestone,
) -> bool:
    """周报 key 是否与该里程碑匹配"""
    return _match_keywords(report_key, milestone.name)


def _match_report_to_workshop(
    report_key: str,
    workshop_name: str,
) -> bool:
    """周报 key 是否与该车间名称匹配"""
    return _match_keywords(report_key, workshop_name)


def _match_report_to_process(
    report_key: str,
    process: CriticalPathProcess,
) -> bool:
    """周报 key 是否与该工序名称匹配"""
    return _match_keywords(report_key, process.process_name)


# ============================================================================
# 辅助函数
# ============================================================================

def _calc_delay(target_date: date, actual_date: date) -> int:
    """计算延迟天数：正数表示延迟，负数表示提前"""
    return (actual_date - target_date).days


def _is_pre_project_milestone(milestone: PlanMilestone, plan: ProjectPlan) -> bool:
    """
    判断里程碑是否为项目开工前的节点。
    如 "完成全套施工图图纸设计"（目标日期在开工日之前）、
    "项目实体开工日"（就是开工日当天）。
    """
    start = plan.base_info.start_date
    return milestone.target_date <= start


def _classify_delay(delay_days: int, threshold_yellow: int = 7, threshold_red: int = 30) -> AlertLevel:
    """根据延迟天数返回预警等级（适用于工序）"""
    if delay_days < threshold_yellow:
        return AlertLevel.GREEN
    elif delay_days < threshold_red:
        return AlertLevel.YELLOW
    else:
        return AlertLevel.RED


# ============================================================================
# 1. 里程碑节点预警
# ============================================================================

def evaluate_milestones(
    plan: ProjectPlan,
    report: WeeklyReport,
    report_date: date,
) -> List[MilestoneAlert]:
    """
    里程碑节点预警规则：
      - 目标日期未到 + 已完成     → 绿色（提前完成）
      - 目标日期已过 + 延迟<30天   → 黄色
      - 目标日期已过 + 延迟≥30天   → 红色
      - 目标日期已过 + 进行中     → 按延迟天数判断

    特殊处理：
      - 开工前里程碑（如 图纸设计、开工日）：若项目已启动，
        且周报中无明确状态，则自动视为"按期完成"
    """
    alerts: List[MilestoneAlert] = []

    for milestone in plan.milestones:
        # 查找周报中对应的状态
        matched_report: Optional[MilestoneReportItem] = None
        for rk, rv in report.milestone_statuses.items():
            if _match_report_to_milestone(rk, milestone):
                matched_report = rv
                break

        target = milestone.target_date

        if matched_report is None:
            # 周报中无此里程碑的明确状态
            if _is_pre_project_milestone(milestone, plan):
                # 开工前节点：项目已启动，视为按期完成
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=AlertLevel.GREEN,
                    delay_days=0,
                    reason="项目开工前节点，视为按期完成",
                ))
            elif report_date > target:
                delay = _calc_delay(target, report_date)
                level = AlertLevel.RED if delay >= 30 else AlertLevel.YELLOW
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=level,
                    delay_days=delay,
                    reason=f"缺少状态数据；目标日期已过{delay}天，判定为{'红色' if level == AlertLevel.RED else '黄色'}预警",
                ))
            else:
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=AlertLevel.GREEN,
                    delay_days=0,
                    reason="目标日期未到，暂无状态数据",
                ))
            continue

        # ---- 有周报状态 ----
        if matched_report.status == "completed":
            actual = matched_report.actual_date
            if actual is None:
                # 已标记完成但无实际日期
                if report_date <= target:
                    alerts.append(MilestoneAlert(
                        milestone_name=milestone.name,
                        target_date=target,
                        alert_level=AlertLevel.GREEN,
                        delay_days=0,
                        reason="已完成，且未超过目标日期",
                    ))
                else:
                    delay = _calc_delay(target, report_date)
                    level = AlertLevel.RED if delay >= 30 else AlertLevel.YELLOW
                    alerts.append(MilestoneAlert(
                        milestone_name=milestone.name,
                        target_date=target,
                        alert_level=level,
                        delay_days=delay,
                        reason=f"已标记完成但缺少实际日期，报告日已超目标日期{delay}天",
                    ))
            elif actual <= target:
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=AlertLevel.GREEN,
                    delay_days=0,
                    reason=f"已于{actual}提前/按期完成",
                ))
            else:
                delay = _calc_delay(target, actual)
                level = AlertLevel.RED if delay >= 30 else AlertLevel.YELLOW
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=level,
                    delay_days=delay,
                    reason=f"于{actual}完成，延迟{delay}天",
                ))

        elif matched_report.status == "in_progress":
            if report_date <= target:
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=AlertLevel.GREEN,
                    delay_days=0,
                    reason="进行中，尚未到目标日期",
                ))
            else:
                delay = _calc_delay(target, report_date)
                level = AlertLevel.RED if delay >= 30 else AlertLevel.YELLOW
                extra = ""
                if matched_report.issues:
                    extra = f"；异常：{matched_report.issues}"
                if matched_report.actual_progress is not None and matched_report.total:
                    pct = matched_report.actual_progress / matched_report.total * 100
                    extra += f"（进度 {matched_report.actual_progress}/{matched_report.total} = {pct:.1f}%）"
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=level,
                    delay_days=delay,
                    reason=f"进行中但已超目标日期{delay}天{extra}",
                ))

        else:
            # not_started or unknown
            if report_date > target:
                delay = _calc_delay(target, report_date)
                level = AlertLevel.RED if delay >= 30 else AlertLevel.YELLOW
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=level,
                    delay_days=delay,
                    reason=f"尚未开始，目标日期已过{delay}天",
                ))
            else:
                alerts.append(MilestoneAlert(
                    milestone_name=milestone.name,
                    target_date=target,
                    alert_level=AlertLevel.GREEN,
                    delay_days=0,
                    reason="尚未开始，目标日期未到",
                ))

    return alerts


# ============================================================================
# 2. 进度曲线预警（月度跟踪）
# ============================================================================

def _build_monthly_plan_curve(
    plan: ProjectPlan,
    start_date: date,
    total_months: int,
) -> List[Tuple[str, float]]:
    """
    根据里程碑目标日期构建计划进度曲线。
    返回 [(月份标签, 累计计划完成百分比), ...]
    每个里程碑等权重贡献进度。
    """
    milestones = plan.milestones
    n = len(milestones)
    if n == 0:
        return []

    weight_per_milestone = 100.0 / n
    curve: List[Tuple[str, float]] = []

    for m in range(1, total_months + 1):
        month_label = (start_date + relativedelta(months=m - 1)).strftime("%Y-%m")
        # 月末日期：该月最后一天
        if m == 1:
            month_end = (start_date + relativedelta(months=1)) - timedelta(days=1)
        else:
            month_end = start_date + relativedelta(months=m) - timedelta(days=1)
        done_count = sum(1 for ms in milestones if ms.target_date <= month_end)
        cumulative_pct = round(done_count * weight_per_milestone, 2)
        curve.append((month_label, cumulative_pct))

    return curve


def _calc_actual_progress(
    plan: ProjectPlan,
    report: WeeklyReport,
) -> float:
    """
    计算实际累计进度百分比。
    基于已完成里程碑 + 进行中里程碑的部分进度。
    开工前里程碑若项目已启动，视为自动完成。
    """
    milestones = plan.milestones
    n = len(milestones)
    if n == 0:
        return 100.0

    weight_per_milestone = 100.0 / n
    actual_pct = 0.0

    for milestone in milestones:
        matched: Optional[MilestoneReportItem] = None
        for rk, rv in report.milestone_statuses.items():
            if _match_report_to_milestone(rk, milestone):
                matched = rv
                break

        if matched is None:
            # 无信息：开工前节点自动视为完成
            if _is_pre_project_milestone(milestone, plan):
                actual_pct += weight_per_milestone
            # 其他无信息节点不给分
            continue

        if matched.status == "completed":
            actual_pct += weight_per_milestone
        elif matched.status == "in_progress":
            if matched.actual_progress is not None and matched.total:
                partial = matched.actual_progress / matched.total
                actual_pct += weight_per_milestone * partial
            else:
                actual_pct += weight_per_milestone * 0.5

    return round(actual_pct, 2)


def evaluate_progress_curve(
    plan: ProjectPlan,
    report: WeeklyReport,
    report_date: date,
) -> List[ProgressCurveAlert]:
    """
    进度曲线预警规则（月度跟踪）：
      - 实际 ≥ 计划        → 绿色
      - 实际低于计划 0~10%  → 黄色
      - 实际低于计划 >10%   → 红色

    返回截至 report_date 所在月份及之前所有月份的预警。
    """
    start = plan.base_info.start_date
    total_months = plan.total_months

    planned_curve = _build_monthly_plan_curve(plan, start, total_months)
    actual_pct = _calc_actual_progress(plan, report)

    # 确定当前月份索引
    current_month_idx = 0
    for i, (label, _) in enumerate(planned_curve):
        year, month = label.split("-")
        month_end = date(int(year), int(month), 1) + relativedelta(months=1) - timedelta(days=1)
        if report_date <= month_end:
            current_month_idx = i
            break
    else:
        current_month_idx = len(planned_curve) - 1

    alerts: List[ProgressCurveAlert] = []

    for i, (label, planned_pct) in enumerate(planned_curve):
        if i > current_month_idx:
            break

        deviation = actual_pct - planned_pct

        if deviation >= 0:
            level = AlertLevel.GREEN
            reason = f"实际进度 {actual_pct:.1f}% ≥ 计划进度 {planned_pct:.1f}%，偏差 +{deviation:.1f}%"
        elif deviation >= -10:
            level = AlertLevel.YELLOW
            reason = f"实际进度 {actual_pct:.1f}% < 计划进度 {planned_pct:.1f}%，偏差 {deviation:.1f}%（0~10%内）"
        else:
            level = AlertLevel.RED
            reason = f"实际进度 {actual_pct:.1f}% 远低于计划进度 {planned_pct:.1f}%，偏差 {deviation:.1f}%（>10%）"

        alerts.append(ProgressCurveAlert(
            month_label=label,
            planned_pct=planned_pct,
            actual_pct=actual_pct,
            deviation_pct=round(deviation, 2),
            alert_level=level,
            reason=reason,
        ))

    return alerts


# ============================================================================
# 3. 关键路径工序偏差预警
# ============================================================================

def evaluate_critical_path(
    plan: ProjectPlan,
    report: WeeklyReport,
    report_date: date,
) -> List[CriticalPathAlert]:
    """
    关键路径工序偏差预警规则：
      - 偏差 < 7天       → 绿色
      - 7天 ≤ 偏差 < 30天 → 黄色
      - 偏差 ≥ 30天      → 红色

    匹配策略（按优先级）：
      1. 优先按工序名称精确匹配（周报 key ↔ 工序名称）
      2. 其次按车间名称匹配桩基工序（critical_path_current 数据）
      3. 对于整车间已完成的（如 机电修车间），所有工序均视为完成，
         但仅最后一个工序使用车间完成日期，之前工序使用各自的计划日期评估
    """
    alerts: List[CriticalPathAlert] = []

    for workshop_name, processes in plan.critical_paths.items():
        # 1) 匹配周报 critical_path_current（桩基进度数据）
        cp_info = None
        for rk, rv in report.critical_path_current.items():
            if _match_report_to_workshop(rk, workshop_name):
                cp_info = rv
                break

        # 2) 匹配周报 milestone_statuses（整体车间状态，如"机电修车间"→completed）
        #    注意：需区分"整车间完成"与"仅桩基完成"。
        #    若 report key 含工序关键词（如"桩基"），则为工序级状态，不视为整车间状态。
        workshop_ms: Optional[MilestoneReportItem] = None
        for rk, rv in report.milestone_statuses.items():
            if _match_report_to_workshop(rk, workshop_name):
                # 若 key 含工序级关键词，说明是具体工序（如"烧成窑尾桩基"），非整车间
                is_process_level = any(kw in rk for kw in _PROCESS_KEYWORDS)
                if not is_process_level:
                    workshop_ms = rv
                    break

        # 3) 判断整车间是否已全部完成
        workshop_all_done = (
            workshop_ms is not None
            and workshop_ms.status == "completed"
            and workshop_ms.actual_date is not None
        )
        workshop_done_date = workshop_ms.actual_date if workshop_all_done else None

        # 4) 逐个工序评估
        for idx, proc in enumerate(processes):
            target = proc.target_date
            is_last = (idx == len(processes) - 1)

            # ---- 尝试按工序名称精确匹配 ----
            proc_ms: Optional[MilestoneReportItem] = None
            for rk, rv in report.milestone_statuses.items():
                if _match_report_to_process(rk, proc):
                    proc_ms = rv
                    break

            actual_date: Optional[date] = None

            # 情况 A：工序在周报中有精确状态
            if proc_ms is not None:
                if proc_ms.status == "completed" and proc_ms.actual_date:
                    actual_date = proc_ms.actual_date
                elif proc_ms.status == "in_progress":
                    # 进行中 → 无实际完成日期，后续按"未完成"处理
                    pass

            # 情况 B：无精确匹配，但桩基数据表明桩基工序已完成
            if actual_date is None and cp_info is not None and cp_info.piling_done:
                if "桩基" in proc.process_name:
                    # 尝试从 milestone_statuses 中获取桩基实际完成日期
                    # 匹配策略：找到匹配该车间的 critical_path_current 的 key，
                    # 然后在 milestone_statuses 中找包含该 key 且含"桩基"的条目
                    pile_date: Optional[date] = None
                    # 找出匹配本车间的 cp key（如 "烧成窑尾"）
                    cp_key: Optional[str] = None
                    for crk in report.critical_path_current:
                        if _match_report_to_workshop(crk, workshop_name):
                            cp_key = crk
                            break
                    for rk, rv in report.milestone_statuses.items():
                        if "桩基" in rk and rv.status == "completed" and rv.actual_date:
                            # 匹配方式：cp_key 是 rk 的子串（如 "烧成窑尾" in "烧成窑尾桩基"）
                            if cp_key and cp_key in rk:
                                pile_date = rv.actual_date
                                break
                            # 备选：直接尝试模糊匹配 rk 与车间名
                            if pile_date is None and _match_report_to_workshop(rk, workshop_name):
                                pile_date = rv.actual_date
                    actual_date = pile_date if pile_date else report_date

            # 情况 C：整车间已完成
            if actual_date is None and workshop_all_done:
                if is_last:
                    # 最后一道工序用车间完成日期
                    actual_date = workshop_done_date
                else:
                    # 非最后工序：车间整完成说明它也已做完
                    # 用 target_date 当天表示按期（因为中间工序的延迟已反映在最后一工序上）
                    actual_date = target

            # ---- 生成预警 ----
            if actual_date is not None:
                delay = _calc_delay(target, actual_date)
                level = _classify_delay(delay)
                if delay < 0:
                    detail = f"提前{-delay}天完成"
                elif delay == 0:
                    detail = "按期完成"
                elif delay < 7:
                    detail = f"按期完成（偏差{delay}天）"
                elif delay < 30:
                    detail = f"延迟{delay}天完成"
                else:
                    detail = f"严重延迟{delay}天完成"

                alerts.append(CriticalPathAlert(
                    workshop=workshop_name,
                    process_name=proc.process_name,
                    target_date=target,
                    actual_date=actual_date,
                    alert_level=level,
                    delay_days=delay,
                    reason=detail,
                ))
            else:
                # 无实际完成日期
                if report_date <= target:
                    alerts.append(CriticalPathAlert(
                        workshop=workshop_name,
                        process_name=proc.process_name,
                        target_date=target,
                        alert_level=AlertLevel.GREEN,
                        delay_days=0,
                        reason="目标日期未到，正常推进中",
                    ))
                else:
                    delay = _calc_delay(target, report_date)
                    level = _classify_delay(delay)

                    extra = ""
                    if proc_ms and proc_ms.issues:
                        extra = f"；异常：{proc_ms.issues}"
                    if cp_info and not cp_info.piling_done and "桩基" in proc.process_name:
                        extra += f"（已完成{cp_info.key_pile_completed}根，剩余{cp_info.remaining}根）"

                    alerts.append(CriticalPathAlert(
                        workshop=workshop_name,
                        process_name=proc.process_name,
                        target_date=target,
                        alert_level=level,
                        delay_days=delay,
                        reason=f"已超目标日期{delay}天，尚未完成{extra}",
                    ))

    return alerts


# ============================================================================
# 综合判断
# ============================================================================

def determine_overall_status(
    milestone_alerts: List[MilestoneAlert],
    progress_alerts: List[ProgressCurveAlert],
    critical_alerts: List[CriticalPathAlert],
) -> Tuple[AlertLevel, str]:
    """
    综合预警等级：
      - 任一维度红色 → 总体红色
      - 任一维度黄色（且无红色）→ 总体黄色
      - 全部绿色 → 总体绿色
    """
    reasons: List[str] = []
    has_red = False
    has_yellow = False

    # 检查里程碑
    red_ms = [a for a in milestone_alerts if a.alert_level == AlertLevel.RED]
    yellow_ms = [a for a in milestone_alerts if a.alert_level == AlertLevel.YELLOW]
    if red_ms:
        has_red = True
        reasons.append(f"里程碑维度：{len(red_ms)}个节点红色预警（{', '.join(a.milestone_name for a in red_ms)}）")
    if yellow_ms:
        has_yellow = True
        reasons.append(f"里程碑维度：{len(yellow_ms)}个节点黄色预警")

    # 检查进度曲线
    red_pc = [a for a in progress_alerts if a.alert_level == AlertLevel.RED]
    yellow_pc = [a for a in progress_alerts if a.alert_level == AlertLevel.YELLOW]
    if red_pc:
        has_red = True
        reasons.append(f"进度曲线维度：{len(red_pc)}个月红色预警（偏差>10%）")
    if yellow_pc:
        has_yellow = True
        reasons.append(f"进度曲线维度：{len(yellow_pc)}个月黄色预警（偏差0~10%）")

    # 检查关键路径
    red_cp = [a for a in critical_alerts if a.alert_level == AlertLevel.RED]
    yellow_cp = [a for a in critical_alerts if a.alert_level == AlertLevel.YELLOW]
    if red_cp:
        has_red = True
        names = ', '.join(f'{a.workshop}/{a.process_name}' for a in red_cp)
        reasons.append(f"关键路径维度：{len(red_cp)}个工序红色预警（{names}）")
    if yellow_cp:
        has_yellow = True
        reasons.append(f"关键路径维度：{len(yellow_cp)}个工序黄色预警")

    if has_red:
        level = AlertLevel.RED
    elif has_yellow:
        level = AlertLevel.YELLOW
    else:
        level = AlertLevel.GREEN
        reasons.append("所有维度均正常，项目整体推进顺利")

    return level, "；".join(reasons) if reasons else "所有维度均正常"


# ============================================================================
# 建议措施生成
# ============================================================================

def generate_recommendations(overall_level: AlertLevel) -> List[str]:
    """根据综合预警等级生成建议措施"""
    if overall_level == AlertLevel.GREEN:
        return [
            "继续按计划执行，保持当前进度节奏",
            "定期（每周）跟踪里程碑节点状态",
            "做好资源储备，防范潜在风险",
        ]
    elif overall_level == AlertLevel.YELLOW:
        return [
            "建议增加有限资源投入（如增开班组、延长作业时间）",
            "加强日常监控频率，每日跟踪偏差工序进展",
            "对存在偏差的工序进行重点分析和专项调度",
            "评估后续工序的压缩空间，制定备选方案",
            "提前预警相关供应商和分包商，协调资源保障",
        ]
    else:  # RED
        return [
            "建议大幅增加资源投入，必要时增开工作面",
            "调整关键工序施工方案，优化施工逻辑",
            "启动工期调整流程，重新评估竣工节点",
            "上报项目管理委员会审批工期变更",
            "组织专家论证会，评估加速措施可行性",
            "与业主/监理方沟通，协商工期调整",
            "全面排查制约因素（设备、材料、人员、天气等）",
            "制定赶工计划并落实责任人，实行日调度制度",
        ]
