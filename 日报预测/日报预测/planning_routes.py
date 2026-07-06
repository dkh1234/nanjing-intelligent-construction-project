"""
策划书解析 API 路由

POST /api/planning/upload-and-parse  — 上传策划书(.docx)，解析并返回结构化数据
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from auth_middleware import get_current_user
from planning_parser import parse_planning_document

router = APIRouter(prefix="/api/planning", tags=["planning"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/upload-and-parse")
async def upload_and_parse(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传策划书文档并解析

    Args:
        file: .docx 格式的策划书文件，最大 20MB
        current_user: 当前登录用户（自动注入）

    Returns:
        {
            "project": {...},
            "milestones": [...],
            "critical_paths": [...],
            "monthly_tasks": [...]
        }
    """
    # 文件格式校验
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("docx", "doc"):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: .{ext}，请上传 .docx 或 .doc 文件"
        )

    # 读取文件
    file_bytes = await file.read()

    # 文件大小校验
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（最大 20MB）"
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="文件为空，请上传有效的策划书文档"
        )

    # 解析
    try:
        result = parse_planning_document(file_bytes, filename)
        return {
            **result,
            "filename": filename,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析异常: {str(e)}")
