"""
工期预警 API 路由

POST /api/duration-warning
接收项目策划书 + 周报文件（PDF/Word），调用 Dify AI 提取结构化数据，
然后运行 early_warning_system 预警引擎，返回前端兼容格式。
"""
from __future__ import annotations

import json
import os
import re
import sys
from io import BytesIO
from typing import Optional

import requests
from fastapi import APIRouter, UploadFile, File, HTTPException

# ── 将项目根目录加入 sys.path，以便导入 early_warning_system ──
_CUR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_CUR))  # 上溯两级到项目根
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ── Dify 配置 ──
DIFY_BASE_URL = os.environ.get("DIFY_BASE_URL", "http://172.16.204.124/v1")

# 两个 Dify 工作流的 API Key（可在环境变量中覆盖）
DIFY_PLAN_WORKFLOW_KEY = os.environ.get(
    "DIFY_PLAN_WORKFLOW_KEY",
    "Bearer app-RVxS1XNdtouvepKVdK3jpMN5"
)
DIFY_REPORT_WORKFLOW_KEY = os.environ.get(
    "DIFY_REPORT_WORKFLOW_KEY",
    "Bearer app-nU6liUS57LGKHTbwaNG5cESW"
)

router = APIRouter(prefix="/api", tags=["duration-warning"])


# ================================================================
#  文档文本提取（与 api_server.py 中的逻辑一致）
# ================================================================

def _extract_text(file_bytes: bytes, filename: str) -> str:
    """从上传文件中提取纯文本"""
    ext = os.path.splitext(filename)[1].lower()

    if ext in (".txt", ".text"):
        return file_bytes.decode("utf-8", errors="ignore")

    if ext in (".docx", ".doc"):
        try:
            from docx import Document
            doc = Document(BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            raise RuntimeError("请安装 python-docx: pip install python-docx")

    if ext == ".pdf":
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
            return text
        except ImportError:
            raise RuntimeError("请安装 pdfplumber: pip install pdfplumber")

    raise RuntimeError(f"不支持的文件格式: {ext}")


# ================================================================
#  Dify AI 调用
# ================================================================

def _call_dify_workflow(api_key: str, inputs: dict, timeout: int = 120) -> str:
    """
    调用 Dify Workflow API (blocking 模式)，返回 outputs 中的第一个文本值。

    与 Chat API 的区别：
    - 端点: /v1/workflows/run（而非 /v1/chat-messages）
    - 请求体无 query 字段，参数通过 inputs 传入
    - 响应在 data.outputs 中（而非 answer 字段）
    """
    url = f"{DIFY_BASE_URL}/workflows/run"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "inputs": inputs,
        "response_mode": "blocking",
        "user": "admin",
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        # Workflow API 返回格式: {"data": {"outputs": {"text": "...", ...}}}
        outputs = data.get("data", {}).get("outputs", {})
        if outputs:
            # 返回第一个输出字段的值
            return list(outputs.values())[0]
        return ""
    except requests.exceptions.ConnectionError:
        raise RuntimeError("无法连接 Dify AI 服务 (172.16.204.124)，请检查网络和服务状态")
    except requests.exceptions.Timeout:
        raise RuntimeError("Dify AI 服务响应超时，请稍后重试")
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.text[:500]
        except Exception:
            pass
        raise RuntimeError(f"Dify API 返回错误 (HTTP {e.response.status_code}): {detail}")
    except Exception as e:
        raise RuntimeError(f"调用 Dify Workflow 失败: {str(e)}")


def _extract_json_from_answer(answer: str) -> dict:
    """
    从 Dify 返回的 markdown/文本中提取 JSON 对象。
    支持 ```json ... ``` 代码块或裸 JSON。
    """
    # 尝试匹配 ```json ... ``` 代码块
    code_block = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", answer, re.DOTALL)
    if code_block:
        candidate = code_block.group(1).strip()
    else:
        # 尝试匹配首个 { ... } 对象
        brace_match = re.search(r"\{.*\}", answer, re.DOTALL)
        if brace_match:
            candidate = brace_match.group(0).strip()
        else:
            candidate = answer.strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # 尝试修复常见问题：移除尾部逗号
        cleaned = re.sub(r",\s*(\}|\])", r"\1", candidate)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"Dify AI 返回内容无法解析为 JSON，原始内容前500字符:\n{candidate[:500]}"
            )


# ================================================================
#  结构化数据提取
# ================================================================

PLAN_EXTRACTION_PROMPT = """你是一个工程项目文档分析专家。请从以下项目策划书/合同文本中提取关键信息，并**仅输出**一个合法的 JSON 对象（不要包含任何额外说明或 markdown 标记）。

JSON 格式要求：
{
  "一、项目基础概况": {
    "项目名称": "工程项目名称",
    "现场实体开工日": "YYYY-MM-DD",
    "计划总工期": "XX个月",
    "计划整体竣工点火节点": "YYYY-MM-DD"
  },
  "二、项目整体里程碑节点清单": [
    {"节点名称": "里程碑名称", "目标日期": "YYYY-MM-DD"}
  ],
  "三、分车间关键路径工序及目标日期": {
    "车间名称": [
      {"工序名称": "工序名称", "目标日期": "YYYY-MM-DD"}
    ]
  }
}

注意事项：
- 所有日期统一为 YYYY-MM-DD 格式
- 如果文档中未明确给出某个字段，请根据上下文合理推断
- 里程碑节点至少提取3个，关键路径工序至少包含2个车间

文档内容：
"""

REPORT_EXTRACTION_PROMPT = """你是一个工程项目文档分析专家。请从以下项目周报/月报文本中提取关键信息，并**仅输出**一个合法的 JSON 对象（不要包含任何额外说明或 markdown 标记）。

JSON 格式要求：
{
  "project_name": "项目名称",
  "report_period": "YYYY-MM-DD ~ YYYY-MM-DD",
  "key_milestones_status": {
    "里程碑名称": {
      "status": "completed",
      "actual_date": "YYYY-MM-DD"
    }
  },
  "critical_path_current": {
    "车间名称": {
      "key_pile_completed": 已完成数量,
      "piling_done": true,
      "remaining": 剩余数量
    }
  },
  "key_issues": ["问题描述1", "问题描述2"]
}

注意事项：
- status 取值: "completed"(已完成) / "in_progress"(进行中) / "not_started"(未开始)
- 如果文档中未明确给出某个字段，请根据上下文合理推断
- actual_progress 和 total 是可选的数字字段，用于表示已完成/总量（如已完成12根/总计143根）

文档内容：
"""


def _parse_plan_document(text: str) -> dict:
    """使用 Dify 策划书解析 Workflow 将文档转为结构化 JSON"""
    answer = _call_dify_workflow(
        api_key=DIFY_PLAN_WORKFLOW_KEY,
        inputs={"doc_text": text[:8000]}
    )
    return _extract_json_from_answer(answer)


def _parse_report_document(text: str) -> dict:
    """使用 Dify 周报解析 Workflow 将文档转为结构化 JSON"""
    answer = _call_dify_workflow(
        api_key=DIFY_REPORT_WORKFLOW_KEY,
        inputs={"doc_text": text[:8000]}
    )
    return _extract_json_from_answer(answer)


# ================================================================
#  预警引擎调用
# ================================================================

def _run_warning_engine(plan_raw: dict, report_raw: dict) -> dict:
    """调用 early_warning_system 运行预警分析，返回完整报告 dict"""
    from early_warning_system.models import (
        ProjectPlan, ProjectBaseInfo, PlanMilestone, CriticalPathProcess,
        WeeklyReport, MilestoneReportItem, CriticalPathCurrentItem,
    )
    from early_warning_system.report_generator import (
        WarningReportGenerator, report_to_dict,
    )

    # ── 构建 ProjectPlan ──
    base = plan_raw["一、项目基础概况"]
    base_info = ProjectBaseInfo.model_validate(base)

    milestones = [
        PlanMilestone.model_validate(m)
        for m in plan_raw["二、项目整体里程碑节点清单"]
    ]

    critical_paths = {}
    for ws_name, processes in plan_raw["三、分车间关键路径工序及目标日期"].items():
        critical_paths[ws_name] = [
            CriticalPathProcess.model_validate(p) for p in processes
        ]

    plan = ProjectPlan(
        base_info=base_info,
        milestones=milestones,
        critical_paths=critical_paths,
    )

    # ── 构建 WeeklyReport ──
    from datetime import date

    milestone_statuses = {}
    for key, val in report_raw.get("key_milestones_status", {}).items():
        actual_date = None
        if val.get("actual_date"):
            try:
                actual_date = date.fromisoformat(val["actual_date"])
            except (ValueError, TypeError):
                pass
        milestone_statuses[key] = MilestoneReportItem(
            status=val.get("status", "not_started"),
            actual_date=actual_date,
            actual_progress=val.get("actual_progress"),
            total=val.get("total"),
            issues=val.get("issues"),
        )

    critical_path_current = {}
    for key, val in report_raw.get("critical_path_current", {}).items():
        critical_path_current[key] = CriticalPathCurrentItem(**val)

    report = WeeklyReport(
        project_name=report_raw.get("project_name", plan.base_info.project_name),
        report_period=report_raw.get("report_period", ""),
        milestone_statuses=milestone_statuses,
        critical_path_current=critical_path_current,
        key_issues=report_raw.get("key_issues", []),
    )

    # ── 生成预警报告 ──
    generator = WarningReportGenerator(plan, report)
    warning = generator.generate()

    return report_to_dict(warning)


# ================================================================
#  结果格式转换：early_warning_system → 前端格式
# ================================================================

def _transform_to_frontend_format(warning_dict: dict) -> dict:
    """
    将 WarningReport 的完整 dict 转换为前端 DurationWarning.vue 期望的格式：
    {
      risk_level: "green" | "yellow" | "red",
      planned_completion_date: "YYYY-MM-DD",
      predicted_completion_date: "YYYY-MM-DD",
      delay_days: int,
      analysis_summary: str
    }
    """
    overall = warning_dict.get("overall_status", "绿色")

    # 映射中文等级 → 英文字符串
    level_map = {"绿色": "green", "黄色": "yellow", "红色": "red"}
    risk_level = level_map.get(overall, "green")

    # 从里程碑预警中找计划竣工日期（取目标日期最晚的里程碑作为计划竣工节点）
    milestones = warning_dict.get("milestones_alert", [])
    planned_completion_date = ""

    for m in milestones:
        target = m.get("target_date", "")
        if target:
            target_str = str(target)
            if not planned_completion_date or target_str > planned_completion_date:
                planned_completion_date = target_str

    # 综合三个维度计算最大延迟天数（里程碑 + 关键路径 + 进度曲线）
    max_delay = 0

    # 1) 里程碑维度延迟
    for m in milestones:
        delay = m.get("delay_days", 0)
        if delay > max_delay:
            max_delay = delay

    # 2) 关键路径维度延迟（各工序偏差也会推后最终竣工日期）
    cp_alerts = warning_dict.get("critical_path_alert", [])
    for a in cp_alerts:
        delay = a.get("delay_days", 0)
        if delay > max_delay:
            max_delay = delay

    # 3) 进度曲线维度：若偏差 < -10%（红色），按当月计划天数估算延迟
    pc_alerts = warning_dict.get("progress_curve_alert", [])
    for a in pc_alerts:
        if a.get("alert_level") == "红色":
            deviation = abs(a.get("deviation_pct", 0))
            # 偏差超过10%的部分，按每月30天折算延迟
            excess = deviation - 10
            if excess > 0:
                estimated_delay = int(excess / 100 * 30)  # 粗略折算天数
                if estimated_delay > max_delay:
                    max_delay = estimated_delay

    # 预测竣工日期 = 计划日期 + 最大延迟
    predicted_completion_date = planned_completion_date
    if planned_completion_date:
        from datetime import date, timedelta
        try:
            planned_date = date.fromisoformat(planned_completion_date)
            predicted = planned_date + timedelta(days=max_delay)
            predicted_completion_date = predicted.isoformat()
        except (ValueError, TypeError):
            pass

    delay_days = max_delay

    # 组装摘要
    parts = []
    overall_reason = warning_dict.get("overall_reason", "")

    # 里程碑红色/黄色预警
    red_ms = [m for m in milestones if m.get("alert_level") in ("红色",)]
    yellow_ms = [m for m in milestones if m.get("alert_level") in ("黄色",)]
    if red_ms:
        parts.append(f"里程碑维度：{len(red_ms)}个节点红色预警")
    if yellow_ms:
        parts.append(f"里程碑维度：{len(yellow_ms)}个节点黄色预警")

    # 关键路径预警（cp_alerts 已在上述延迟计算中定义）
    red_cp = [a for a in cp_alerts if a.get("alert_level") in ("红色",)]
    yellow_cp = [a for a in cp_alerts if a.get("alert_level") in ("黄色",)]
    if red_cp:
        parts.append(f"关键路径维度：{len(red_cp)}个工序红色预警")
    if yellow_cp:
        parts.append(f"关键路径维度：{len(yellow_cp)}个工序黄色预警")

    # 进度曲线预警（pc_alerts 已在上述延迟计算中定义）
    red_pc = [a for a in pc_alerts if a.get("alert_level") in ("红色",)]
    if red_pc:
        parts.append(f"进度曲线维度：{len(red_pc)}个月偏差>10%")

    # 建议
    recs = warning_dict.get("recommendations", [])
    if recs:
        parts.append(f"建议：{'；'.join(recs[:2])}")

    analysis_summary = "。\n".join(parts) if parts else overall_reason

    return {
        "risk_level": risk_level,
        "planned_completion_date": planned_completion_date,
        "predicted_completion_date": predicted_completion_date,
        "delay_days": delay_days,
        "analysis_summary": analysis_summary,
        # 附加完整报告供高级场景使用
        "full_report": warning_dict,
    }


# ================================================================
#  API 端点
# ================================================================

@router.post("/duration-warning")
async def duration_warning(
    plan_file: UploadFile = File(...),
    report_file: UploadFile = File(...),
):
    """
    接收项目策划书和周报文件，执行工期预警分析。

    支持两种上传方式：
    1. **JSON 文件**（推荐）：直接上传 .json 格式的策划书和周报，无需 AI 解析
    2. **PDF/Word 文件**：调用 Dify AI 提取结构化数据后再分析

    JSON 格式要求见 /api/duration-warning/sample 返回的 full_report 中对应字段。

    返回：
    - risk_level: 风险等级（green / yellow / red）
    - planned_completion_date: 计划完工日期
    - predicted_completion_date: 预测完工日期
    - delay_days: 预计延迟天数（负数表示提前）
    - analysis_summary: 分析摘要
    """
    # 1. 读取文件
    try:
        plan_bytes = await plan_file.read()
        report_bytes = await report_file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="文件读取失败")

    plan_ext = os.path.splitext(plan_file.filename or "")[1].lower()
    report_ext = os.path.splitext(report_file.filename or "")[1].lower()

    # ── 路径 A：JSON 文件直接解析 ──
    if plan_ext == ".json" and report_ext == ".json":
        try:
            plan_raw = json.loads(plan_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=400, detail=f"策划书 JSON 解析失败: {str(e)}")
        try:
            report_raw = json.loads(report_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=400, detail=f"周报 JSON 解析失败: {str(e)}")

        # 基础校验
        if "一、项目基础概况" not in plan_raw:
            raise HTTPException(status_code=400, detail="策划书 JSON 缺少顶层字段「一、项目基础概况」，请参考 /api/duration-warning/sample 中的格式")
        if "key_milestones_status" not in report_raw:
            raise HTTPException(status_code=400, detail="周报 JSON 缺少字段「key_milestones_status」，请参考 /api/duration-warning/sample 中的格式")

        try:
            warning_dict = _run_warning_engine(plan_raw, report_raw)
            return _transform_to_frontend_format(warning_dict)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"预警引擎执行失败: {str(e)}")

    # ── 路径 B：PDF/Word 文件走 Dify AI 解析 ──
    try:
        plan_text = _extract_text(plan_bytes, plan_file.filename or "plan.pdf")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"策划书文本提取失败: {str(e)}。也可直接上传 JSON 文件（.json），绕过 AI 解析。")

    try:
        report_text = _extract_text(report_bytes, report_file.filename or "report.pdf")
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"周报文本提取失败: {str(e)}。也可直接上传 JSON 文件（.json），绕过 AI 解析。")

    if not plan_text.strip():
        raise HTTPException(status_code=400, detail="策划书文件内容为空，请检查文件")
    if not report_text.strip():
        raise HTTPException(status_code=400, detail="周报文件内容为空，请检查文件")

    try:
        plan_raw = _parse_plan_document(plan_text)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"策划书 AI 结构化失败: {str(e)}。可改用 JSON 文件上传，参考 /api/duration-warning/sample 返回格式。")

    try:
        report_raw = _parse_report_document(report_text)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"周报 AI 结构化失败: {str(e)}。可改用 JSON 文件上传，参考 /api/duration-warning/sample 返回格式。")

    try:
        warning_dict = _run_warning_engine(plan_raw, report_raw)
        return _transform_to_frontend_format(warning_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预警引擎执行失败: {str(e)}")


# ================================================================
#  内置默认示例数据（来自 early_warning_system/main.py）
# ================================================================

SAMPLE_PLAN = {
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

SAMPLE_REPORT = {
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


@router.get("/duration-warning/sample")
def duration_warning_sample():
    """
    使用内置默认示例数据运行工期预警分析，无需上传文件。

    示例数据：
    - 项目：陇南祁连山水泥厂新建熟料生产线项目
    - 策划书：12个里程碑节点，5个车间关键路径
    - 周报：2025-03-11 ~ 2025-05-11，熟料库桩基进度滞后
    """
    try:
        warning_dict = _run_warning_engine(SAMPLE_PLAN, SAMPLE_REPORT)
        result = _transform_to_frontend_format(warning_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预警引擎执行失败: {str(e)}")
