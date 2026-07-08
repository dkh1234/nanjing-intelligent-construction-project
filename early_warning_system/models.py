"""
数据模型定义 —— 使用 Pydantic v2 进行数据校验与序列化
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional, List, Dict

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 枚举定义
# ============================================================================

class AlertLevel(str, Enum):
    """预警等级"""
    GREEN = "绿色"
    YELLOW = "黄色"
    RED = "红色"


class MilestoneStatus(str, Enum):
    """里程碑实际状态"""
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"


# ============================================================================
# 项目策划书模型
# ============================================================================

class ProjectBaseInfo(BaseModel):
    """项目基础概况"""
    project_name: str = Field(alias="项目名称")
    start_date: date = Field(alias="现场实体开工日")
    total_duration: str = Field(alias="计划总工期")
    planned_completion_date: date = Field(alias="计划整体竣工点火节点")


class PlanMilestone(BaseModel):
    """策划书中的里程碑节点"""
    name: str = Field(alias="节点名称")
    target_date: date = Field(alias="目标日期")


class CriticalPathProcess(BaseModel):
    """关键路径工序"""
    process_name: str = Field(alias="工序名称")
    target_date: date = Field(alias="目标日期")


class ProjectPlan(BaseModel):
    """项目策划书（完整）"""
    base_info: ProjectBaseInfo
    milestones: List[PlanMilestone]
    # key: 车间名称, value: 该车间的关键路径工序列表
    critical_paths: Dict[str, List[CriticalPathProcess]]

    @property
    def total_months(self) -> int:
        """根据计划总工期字符串推算月数"""
        dur = self.base_info.total_duration
        # 支持 "16个月" / "16" 两种写法
        digits = "".join(ch for ch in dur if ch.isdigit())
        return int(digits) if digits else 12

    @property
    def total_milestones(self) -> int:
        return len(self.milestones)

    @property
    def all_critical_processes(self) -> List[tuple]:
        """返回 (车间名, CriticalPathProcess) 的扁平列表"""
        result = []
        for workshop, processes in self.critical_paths.items():
            for proc in processes:
                result.append((workshop, proc))
        return result


# ============================================================================
# 项目周报模型
# ============================================================================

class MilestoneReportItem(BaseModel):
    """周报中单个里程碑的实际状态"""
    status: str  # "completed" / "in_progress" / "not_started"
    actual_date: Optional[date] = None
    actual_progress: Optional[int] = None  # 已完成数量
    total: Optional[int] = None            # 总数量
    issues: Optional[str] = None           # 异常描述


class CriticalPathCurrentItem(BaseModel):
    """周报中某个车间关键路径的当前状态（允许额外字段如 土建开始）"""
    key_pile_completed: int = 0
    piling_done: bool = False
    remaining: int = 0

    model_config = ConfigDict(extra="allow")  # 允许并保留额外字段（如 土建开始）


class WeeklyReport(BaseModel):
    """项目周报（完整）"""
    project_name: str
    report_period: str
    report_date: Optional[date] = None  # 报告截止日期（若未提供则从 report_period 解析）
    milestone_statuses: Dict[str, MilestoneReportItem]
    critical_path_current: Dict[str, CriticalPathCurrentItem]
    key_issues: List[str] = Field(default_factory=list)

    def model_post_init(self, __context):
        """若 report_date 未提供，尝试从 report_period 的结束日期解析"""
        if self.report_date is None:
            # report_period 如 "2025-03-11 ~ 2025-05-11"
            parts = self.report_period.split("~")
            if len(parts) == 2:
                try:
                    self.report_date = date.fromisoformat(parts[1].strip())
                except ValueError:
                    pass


# ============================================================================
# 预警结果模型
# ============================================================================

class MilestoneAlert(BaseModel):
    """单个里程碑的预警结果"""
    milestone_name: str
    target_date: date
    alert_level: AlertLevel
    delay_days: int = 0
    reason: str = ""


class CriticalPathAlert(BaseModel):
    """单个关键路径工序的预警结果"""
    workshop: str
    process_name: str
    target_date: date
    actual_date: Optional[date] = None
    alert_level: AlertLevel
    delay_days: int = 0
    reason: str = ""


class ProgressCurveAlert(BaseModel):
    """进度曲线预警结果"""
    month_label: str           # 如 "2025-03"
    planned_pct: float         # 计划累计完成百分比
    actual_pct: float          # 实际累计完成百分比
    deviation_pct: float       # 偏差（实际-计划）
    alert_level: AlertLevel
    reason: str = ""


class WarningReport(BaseModel):
    """最终预警报告"""
    project_name: str
    report_date: date
    milestones_alert: List[MilestoneAlert]
    critical_path_alert: List[CriticalPathAlert]
    progress_curve_alert: List[ProgressCurveAlert]
    overall_status: AlertLevel
    overall_reason: str
    recommendations: List[str]
    key_issues: List[str] = Field(default_factory=list)
