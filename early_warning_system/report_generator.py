"""
报告生成器 —— 将预警引擎输出格式化为 JSON 报告
"""

from __future__ import annotations

import json
from datetime import date
from typing import List

from .models import (
    WarningReport,
    MilestoneAlert,
    CriticalPathAlert,
    ProgressCurveAlert,
    AlertLevel,
)
from .warning_engine import (
    evaluate_milestones,
    evaluate_progress_curve,
    evaluate_critical_path,
    determine_overall_status,
    generate_recommendations,
)
from .models import ProjectPlan, WeeklyReport


class WarningReportGenerator:
    """预警报告生成器 —— 编排整个评估流程并生成最终报告"""

    def __init__(self, plan: ProjectPlan, report: WeeklyReport):
        self.plan = plan
        self.report = report

    def generate(self) -> WarningReport:
        """执行全量评估并生成预警报告"""
        report_date = self._resolve_report_date()

        # 三大维度评估
        milestones_alert = evaluate_milestones(self.plan, self.report, report_date)
        progress_curve_alert = evaluate_progress_curve(self.plan, self.report, report_date)
        critical_path_alert = evaluate_critical_path(self.plan, self.report, report_date)

        # 综合判断
        overall_status, overall_reason = determine_overall_status(
            milestones_alert, progress_curve_alert, critical_path_alert
        )

        # 建议措施
        recommendations = generate_recommendations(overall_status)

        return WarningReport(
            project_name=self.plan.base_info.project_name,
            report_date=report_date,
            milestones_alert=milestones_alert,
            critical_path_alert=critical_path_alert,
            progress_curve_alert=progress_curve_alert,
            overall_status=overall_status,
            overall_reason=overall_reason,
            recommendations=recommendations,
            key_issues=self.report.key_issues,
        )

    def _resolve_report_date(self) -> date:
        """解析报告日期"""
        if self.report.report_date:
            return self.report.report_date
        # fallback: 取 milestones 中最晚的 actual_date
        latest = None
        for item in self.report.milestone_statuses.values():
            if item.actual_date:
                if latest is None or item.actual_date > latest:
                    latest = item.actual_date
        return latest or date.today()


def report_to_json(report: WarningReport, indent: int = 2, ensure_ascii: bool = False) -> str:
    """将报告序列化为 JSON 字符串"""
    return json.dumps(report.model_dump(), indent=indent, ensure_ascii=ensure_ascii, default=str)


def report_to_dict(report: WarningReport) -> dict:
    """将报告转为 Python dict（方便后续处理）"""
    return report.model_dump()


def print_report(report: WarningReport):
    """在控制台美观打印报告"""
    BOLD = "\033[1m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    def color_for(level: AlertLevel) -> str:
        if level == AlertLevel.RED:
            return RED
        elif level == AlertLevel.YELLOW:
            return YELLOW
        return GREEN

    print(f"{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  工程项目工期预警报告{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"  项目名称: {report.project_name}")
    print(f"  报告日期: {report.report_date}")
    print(f"  综合预警: {color_for(report.overall_status)}{report.overall_status.value}{RESET}")
    print()

    # --- 里程碑预警 ---
    print(f"{BOLD}── 里程碑节点预警{RESET}")
    for a in report.milestones_alert:
        icon = "●" if a.alert_level != AlertLevel.GREEN else "○"
        color = color_for(a.alert_level)
        print(f"  {color}{icon} [{a.alert_level.value}] {a.milestone_name}{RESET}")
        print(f"      目标: {a.target_date} | 延迟: {a.delay_days}天 | {a.reason}")
    print()

    # --- 进度曲线预警 ---
    print(f"{BOLD}── 月度进度曲线预警{RESET}")
    for a in report.progress_curve_alert:
        color = color_for(a.alert_level)
        print(f"  {color}[{a.alert_level.value}] {a.month_label} | 实际 {a.actual_pct:.1f}% vs 计划 {a.planned_pct:.1f}% | 偏差 {a.deviation_pct:+.1f}%{RESET}")
        print(f"      {a.reason}")
    print()

    # --- 关键路径预警 ---
    print(f"{BOLD}── 关键路径工序偏差预警{RESET}")
    for a in report.critical_path_alert:
        icon = "●" if a.alert_level != AlertLevel.GREEN else "○"
        color = color_for(a.alert_level)
        actual_str = str(a.actual_date) if a.actual_date else "未完成"
        print(f"  {color}{icon} [{a.alert_level.value}] {a.workshop} → {a.process_name}{RESET}")
        print(f"      目标: {a.target_date} | 实际: {actual_str} | 延迟: {a.delay_days}天 | {a.reason}")
    print()

    # --- 关键问题 ---
    if report.key_issues:
        print(f"{BOLD}── 现场关键问题{RESET}")
        for i, issue in enumerate(report.key_issues, 1):
            print(f"  {i}. {issue}")
        print()

    # --- 综合判断 ---
    print(f"{BOLD}── 综合判断{RESET}")
    print(f"  {report.overall_reason}")
    print()

    # --- 建议措施 ---
    print(f"{BOLD}── 建议措施{RESET}")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {i}. {rec}")
    print(f"{BOLD}{'='*70}{RESET}")
