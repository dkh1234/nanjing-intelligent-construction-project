"""
主入口 —— 支持用户上传策划书与周报 JSON，或使用内置示例数据运行
"""

from __future__ import annotations

import argparse
import json
import sys
import os
from datetime import date
from pathlib import Path
from typing import Optional, Tuple

# 确保 early_warning_system 包可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from early_warning_system.models import (
    ProjectPlan,
    ProjectBaseInfo,
    PlanMilestone,
    CriticalPathProcess,
    WeeklyReport,
    MilestoneReportItem,
    CriticalPathCurrentItem,
)
from early_warning_system.report_generator import (
    WarningReportGenerator,
    report_to_json,
    print_report,
)


# ============================================================================
# 内置示例数据（当用户未提供文件时使用）
# ============================================================================

SAMPLE_PLAN_RAW = {
    "一、项目基础概况": {
        "项目名称": "陇南祁连山水泥厂新建熟料生产线项目",
        "现场实体开工日": "2025-03-11",
        "计划总工期": "16个月",
        "计划整体竣工点火节点": "2026-07-04"
    },
    "二、项目整体里程碑节点清单": [
        {"节点名称": "完成全套施工图图纸设计", "目标日期": "2025-02-28"},
        {"节点名称": "项目实体开工日", "目标日期": "2025-03-11"},
        {"节点名称": "烧成窑尾桩基全部施工完成", "目标日期": "2025-04-29"},
        {"节点名称": "生料库桩基全部施工完成", "目标日期": "2025-04-26"},
        {"节点名称": "中控室桩基全部施工完成", "目标日期": "2025-05-11"},
        {"节点名称": "熟料库桩基全部施工完成", "目标日期": "2025-10-20"},
        {"节点名称": "全场所有桩基工程全部完工", "目标日期": "2025-10-20"},
        {"节点名称": "全厂区工艺车间土建主体及装饰施工完成", "目标日期": "2026-02-28"},
        {"节点名称": "全部主机、辅机设备到场交付完成", "目标日期": "2026-03-15"},
        {"节点名称": "熟料线全套机电设备安装工作完成", "目标日期": "2026-05-20"},
        {"节点名称": "全线单机调试+联动调试全部完成", "目标日期": "2026-07-03"},
        {"节点名称": "生产线首次点火投产", "目标日期": "2026-07-04"}
    ],
    "三、分车间关键路径工序及目标日期": {
        "1.机电修车间+综合材料库": [
            {"工序名称": "图纸交付完成", "目标日期": "2025-02-28"},
            {"工序名称": "隔墙抹灰、地面垫层浇筑施工", "目标日期": "2025-03-25"},
            {"工序名称": "外墙砌筑、构造柱浇筑完成", "目标日期": "2025-03-20"},
            {"工序名称": "内墙腻子、乳胶漆、门窗安装完工", "目标日期": "2025-03-30"},
            {"工序名称": "车间全部土建装饰收尾交付", "目标日期": "2025-04-15"}
        ],
        "2.烧成窑尾区域": [
            {"工序名称": "62根桩基施工", "目标日期": "2025-04-29"},
            {"工序名称": "窑尾基础承台、主体土建施工", "目标日期": "2025-11-30"},
            {"工序名称": "窑尾设备基础交付安装", "目标日期": "2025-12-15"}
        ],
        "3.生料均化库区域": [
            {"工序名称": "32根生料库桩基全部浇筑完成", "目标日期": "2025-04-26"},
            {"工序名称": "库体滑模、仓体土建施工", "目标日期": "2025-12-20"},
            {"工序名称": "库内设备基础完工交付", "目标日期": "2026-01-10"}
        ],
        "4.中控室区域": [
            {"工序名称": "34根中控室桩基全部完工", "目标日期": "2025-05-11"},
            {"工序名称": "中控室主体框架施工", "目标日期": "2025-11-10"},
            {"工序名称": "中控系统基础完工", "目标日期": "2025-12-01"}
        ],
        "5.熟料库区域": [
            {"工序名称": "143根熟料库桩基全部施工完成", "目标日期": "2025-10-20"},
            {"工序名称": "熟料库仓体土建施工", "目标日期": "2026-02-20"},
            {"工序名称": "熟料输送设备基础完工交付", "目标日期": "2026-02-28"}
        ]
    }
}

SAMPLE_REPORT_RAW = {
    "project_name": "陇南祁连山水泥厂项目",
    "report_period": "2025-03-11 ~ 2025-05-11",
    "key_milestones_status": {
        "烧成窑尾桩基": {"status": "completed", "actual_date": "2025-04-29"},
        "生料库桩基": {"status": "completed", "actual_date": "2025-04-26"},
        "中控室桩基": {"status": "completed", "actual_date": "2025-05-11"},
        "熟料库桩基": {"status": "in_progress", "actual_progress": 12, "total": 143, "issues": "漂石层制约，日均1~2根，进度缓慢"},
        "机电修车间": {"status": "completed", "actual_date": "2025-04-15"}
    },
    "critical_path_current": {
        "烧成窑尾": {"key_pile_completed": 62, "piling_done": True, "土建开始": True},
        "熟料库": {"key_pile_completed": 12, "piling_done": False, "remaining": 131},
        "生料库": {"key_pile_completed": 32, "piling_done": True},
        "中控室": {"key_pile_completed": 34, "piling_done": True}
    },
    "key_issues": [
        "熟料库区域地下大量漂石，桩基施工效率仅1~2根/天",
        "旋挖钻机多次故障需维修",
        "钻头掉入桩孔2次",
        "3#旋挖钻机履带宽度3.5米大于进场道路宽度3.4米，设备进场受阻"
    ]
}


# ============================================================================
# JSON 文件读取
# ============================================================================

def _read_json_file(filepath: str) -> dict:
    """
    从指定路径读取 JSON 文件，返回 Python dict。
    若文件不存在/编码错误/JSON 格式错误，打印友好提示并退出。
    """
    path = Path(filepath)
    if not path.exists():
        print(f"[ERROR] 文件不存在: {filepath}")
        sys.exit(1)
    if not path.is_file():
        print(f"[ERROR] 路径不是文件: {filepath}")
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except UnicodeDecodeError:
        # 回退到 GBK 编码（Windows 常见）
        try:
            with open(path, "r", encoding="gbk") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERROR] 文件编码读取失败: {e}")
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 格式错误: {e}")
        sys.exit(1)

    if not isinstance(data, dict):
        print(f"[ERROR] JSON 顶层必须是对象（dict），当前为: {type(data).__name__}")
        sys.exit(1)

    return data


# ============================================================================
# 数据加载与校验
# ============================================================================

def _parse_date(s: str) -> date:
    """解析 ISO 格式日期字符串（如 2025-04-29）"""
    return date.fromisoformat(s)


def _validate_plan_structure(raw: dict) -> Tuple[bool, str]:
    """校验策划书 JSON 顶层结构是否合法"""
    required_keys = ["一、项目基础概况", "二、项目整体里程碑节点清单", "三、分车间关键路径工序及目标日期"]
    missing = [k for k in required_keys if k not in raw]
    if missing:
        return False, f"缺少必要字段: {', '.join(missing)}"

    base = raw["一、项目基础概况"]
    base_required = ["项目名称", "现场实体开工日", "计划总工期", "计划整体竣工点火节点"]
    missing_base = [k for k in base_required if k not in base]
    if missing_base:
        return False, f"项目基础概况缺少字段: {', '.join(missing_base)}"

    milestones = raw["二、项目整体里程碑节点清单"]
    if not isinstance(milestones, list) or len(milestones) == 0:
        return False, "里程碑节点清单必须是非空数组"

    for i, m in enumerate(milestones):
        if not isinstance(m, dict):
            return False, f"里程碑[{i}] 必须是对象"
        if "节点名称" not in m or "目标日期" not in m:
            return False, f"里程碑[{i}] 缺少「节点名称」或「目标日期」"

    paths = raw["三、分车间关键路径工序及目标日期"]
    if not isinstance(paths, dict) or len(paths) == 0:
        return False, "关键路径工序必须是非空对象"

    for ws, procs in paths.items():
        if not isinstance(procs, list):
            return False, f"车间「{ws}」的工序必须是数组"
        for j, p in enumerate(procs):
            if not isinstance(p, dict):
                return False, f"车间「{ws}」工序[{j}] 必须是对象"
            if "工序名称" not in p or "目标日期" not in p:
                return False, f"车间「{ws}」工序[{j}] 缺少「工序名称」或「目标日期」"

    return True, ""


def _validate_report_structure(raw: dict) -> Tuple[bool, str]:
    """校验周报 JSON 顶层结构是否合法"""
    required = ["project_name", "report_period", "key_milestones_status", "critical_path_current"]
    missing = [k for k in required if k not in raw]
    if missing:
        return False, f"缺少必要字段: {', '.join(missing)}"

    ms = raw["key_milestones_status"]
    if not isinstance(ms, dict):
        return False, "key_milestones_status 必须是对象"

    for key, val in ms.items():
        if not isinstance(val, dict):
            return False, f"里程碑状态「{key}」必须是对象"
        if "status" not in val:
            return False, f"里程碑状态「{key}」缺少 status 字段"

    cp = raw["critical_path_current"]
    if not isinstance(cp, dict):
        return False, "critical_path_current 必须是对象"

    return True, ""


def load_plan(filepath: Optional[str] = None) -> ProjectPlan:
    """
    加载策划书。
    若提供 filepath 则从文件读取；否则使用内置示例数据。
    """
    if filepath is None:
        print("  [INFO] 未指定策划书文件，使用内置示例数据")
        raw = SAMPLE_PLAN_RAW
    else:
        print(f"  [INFO] 读取策划书: {filepath}")
        raw = _read_json_file(filepath)

    valid, msg = _validate_plan_structure(raw)
    if not valid:
        print(f"[ERROR] 策划书结构校验失败: {msg}")
        sys.exit(1)
    print("  [OK] 策划书结构校验通过")

    base = raw["一、项目基础概况"]
    base_info = ProjectBaseInfo.model_validate(base)

    milestones = [PlanMilestone.model_validate(m) for m in raw["二、项目整体里程碑节点清单"]]

    critical_paths = {}
    for workshop, processes in raw["三、分车间关键路径工序及目标日期"].items():
        critical_paths[workshop] = [CriticalPathProcess.model_validate(p) for p in processes]

    return ProjectPlan(
        base_info=base_info,
        milestones=milestones,
        critical_paths=critical_paths,
    )


def load_report(filepath: Optional[str] = None) -> WeeklyReport:
    """
    加载周报。
    若提供 filepath 则从文件读取；否则使用内置示例数据。
    """
    if filepath is None:
        print("  [INFO] 未指定周报文件，使用内置示例数据")
        raw = SAMPLE_REPORT_RAW
    else:
        print(f"  [INFO] 读取周报: {filepath}")
        raw = _read_json_file(filepath)

    valid, msg = _validate_report_structure(raw)
    if not valid:
        print(f"[ERROR] 周报结构校验失败: {msg}")
        sys.exit(1)
    print("  [OK] 周报结构校验通过")

    milestone_statuses = {}
    for key, val in raw["key_milestones_status"].items():
        actual_date = _parse_date(val["actual_date"]) if val.get("actual_date") else None
        milestone_statuses[key] = MilestoneReportItem(
            status=val["status"],
            actual_date=actual_date,
            actual_progress=val.get("actual_progress"),
            total=val.get("total"),
            issues=val.get("issues"),
        )

    critical_path_current = {}
    for key, val in raw["critical_path_current"].items():
        critical_path_current[key] = CriticalPathCurrentItem(**val)

    return WeeklyReport(
        project_name=raw["project_name"],
        report_period=raw["report_period"],
        milestone_statuses=milestone_statuses,
        critical_path_current=critical_path_current,
        key_issues=raw.get("key_issues", []),
    )


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="工程项目工期预警系统 — 根据策划书与周报生成预警报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python -m early_warning_system.main
      （使用内置示例数据运行）

  python -m early_warning_system.main -p plan.json -r report.json
      （指定策划书与周报文件）

  python -m early_warning_system.main -p plan.json -r report.json -o output.json
      （指定输出文件路径）

文件格式说明:
  策划书 JSON 需包含以下顶层字段：
    "一、项目基础概况"      项目名、开工日、总工期、竣工节点
    "二、项目整体里程碑节点清单"   [{节点名称, 目标日期}, ...]
    "三、分车间关键路径工序及目标日期"  {车间名: [{工序名称, 目标日期}, ...]}

  周报 JSON 需包含以下顶层字段：
    project_name           项目名称
    report_period          报告周期（如 "2025-03-11 ~ 2025-05-11"）
    key_milestones_status  各里程碑实际状态
    critical_path_current  各车间关键路径当前进展
    key_issues（可选）      现场关键问题列表
        """
    )
    parser.add_argument(
        "-p", "--plan",
        type=str,
        default=None,
        help="策划书 JSON 文件路径（不指定则使用内置示例）"
    )
    parser.add_argument(
        "-r", "--report",
        type=str,
        default=None,
        help="周报 JSON 文件路径（不指定则使用内置示例）"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="预警报告 JSON 输出路径（默认: warning_report_output.json）"
    )
    parser.add_argument(
        "--no-print",
        action="store_true",
        help="不打印详细报告到控制台"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  工程项目工期预警系统")
    print("=" * 70)

    # ── 1. 加载数据 ──
    print("\n[1/3] 加载数据...")
    plan = load_plan(args.plan)
    report = load_report(args.report)

    print(f"  [OK] 策划书: {plan.base_info.project_name}")
    print(f"    里程碑节点: {plan.total_milestones}个")
    print(f"    关键路径车间: {len(plan.critical_paths)}个")
    print(f"    关键路径工序总数: {len(plan.all_critical_processes)}个")
    print(f"  [OK] 周报: {report.project_name}")
    print(f"    报告周期: {report.report_period}")
    print(f"    报告日期: {report.report_date}")
    print(f"    关键问题: {len(report.key_issues)}条")

    # ── 2. 生成预警报告 ──
    print("\n[2/3] 执行预警分析...")
    generator = WarningReportGenerator(plan, report)
    warning = generator.generate()

    # ── 3. 输出 ──
    print("\n[3/3] 生成报告...")

    json_output = report_to_json(warning)

    output_path = args.output or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "warning_report_output.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_output)
    print(f"  [OK] JSON 报告已保存至: {output_path}")

    if not args.no_print:
        print("\n")
        print_report(warning)

    return warning


if __name__ == "__main__":
    main()
