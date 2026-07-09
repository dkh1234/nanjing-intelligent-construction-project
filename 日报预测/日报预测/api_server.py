"""
日报预测 API 服务

启动: python api_server.py
接口: POST /api/daily/upload-and-predict
"""
import os
import sys
import re
import json
import tempfile
import shutil
from datetime import timedelta
from io import BytesIO

import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 确保 src 在 path 中
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
sys.path.insert(0, SRC_DIR)

from process_daily import parse_one_report, aggregate_to_weekly
from predict_api import predict_from_dataframe

from datetime import datetime
from fastapi import Depends, HTTPException, status
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from auth_middleware import get_current_user, require_admin
from database import get_db
from models import (
    UserLogin, UserCreate, UserUpdate, UserOut,
    TokenResponse, RefreshRequest,
    ChangePasswordRequest, ResetPasswordRequest,
)

app = FastAPI(title="日报预测API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 认证路由 ==========

@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: UserLogin):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (body.username,)
        ).fetchone()
        if row is None or not verify_password(body.password, row["password"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        user = dict(row)
        access_token = create_access_token(user["id"], user["role"])
        refresh_token = create_refresh_token(user["id"], user["token_version"])

        conn.execute(
            "UPDATE users SET last_login = datetime('now', 'localtime') WHERE id = ?",
            (user["id"],)
        )
        conn.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": UserOut(**user).model_dump(),
        }
    finally:
        conn.close()


@app.post("/api/auth/refresh")
def refresh_token(body: RefreshRequest):
    payload = decode_token(body.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user_id = int(payload["sub"])
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="账号已被禁用或删除")
        if row["token_version"] != payload.get("ver"):
            raise HTTPException(status_code=401, detail="密码已重置，请重新登录")

        new_access = create_access_token(user_id, row["role"])
        return {"access_token": new_access}
    finally:
        conn.close()


@app.get("/api/auth/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    return UserOut(**user).model_dump()


@app.post("/api/auth/change-password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    if not verify_password(body.old_password, user["password"]):
        raise HTTPException(status_code=400, detail="原密码错误")

    new_hash = hash_password(body.new_password)
    new_version = user["token_version"] + 1

    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password = ?, token_version = ? WHERE id = ?",
            (new_hash, new_version, user["id"]),
        )
        conn.commit()
        return {"message": "密码修改成功，请重新登录"}
    finally:
        conn.close()


# ============================================================
# 1. 文本提取
# ============================================================

def extract_text(file_bytes: bytes, filename: str) -> str:
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
            raise RuntimeError("请安装 python-docx")

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
            raise RuntimeError("请安装 pdfplumber")

    if ext in (".xlsx", ".xls"):
        try:
            dfs = pd.read_excel(BytesIO(file_bytes), sheet_name=None)
            text = ""
            for sheet, df in dfs.items():
                text += df.to_string(index=False) + "\n"
            return text
        except Exception:
            raise RuntimeError("Excel 解析失败")

    raise RuntimeError(f"不支持的文件格式: {ext}")


# ============================================================
# 2. 按日拆分
# ============================================================

def split_by_date(text: str) -> list:
    """
    按日期标记拆分为逐日报告。
    日期间隔：跨天数 > 0 则视为新一天。
    支持格式: 2025-04-12, 2025-4-7, 2025年4月12日
    """
    date_pat = re.compile(
        r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日]?"
    )
    matches = list(date_pat.finditer(text))

    if len(matches) < 2:
        return [text.strip()] if text.strip() else []

    segments = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        day_text = text[start:end].strip()
        if day_text:
            segments.append(day_text)

    return segments


# ============================================================
# 3. 核心流程
# ============================================================

def process_uploaded_file(file_bytes: bytes, filename: str, project_code: str):
    """完整处理链路：文本→解析→聚合→预测用DataFrame，同时返回最后一天原始文本"""
    # 提取文本
    text = extract_text(file_bytes, filename)

    # 按日拆分
    daily_texts = split_by_date(text)
    if not daily_texts:
        raise RuntimeError("未能从文件中识别出日报内容")

    # 保留最后一天的原始文本
    last_day_text = daily_texts[-1].strip() if daily_texts else ""

    # 逐日解析
    records = []
    for day_text in daily_texts:
        rec = parse_one_report(day_text, filename)
        if rec["date"] is not None:
            records.append(rec)

    if not records:
        raise RuntimeError("未能从日报中提取到日期信息")

    daily_df = pd.DataFrame(records)
    daily_df = daily_df.dropna(subset=["date"]).sort_values("date")

    # 聚合为周级
    weekly_df = aggregate_to_weekly(daily_df, project_code)
    if len(weekly_df) < 4:
        raise RuntimeError(f"仅提取到 {len(weekly_df)} 周数据，至少需要4周")

    return weekly_df, last_day_text


# ============================================================
# 4. API 端点
# ============================================================

@app.post("/api/daily/upload-and-predict")
async def upload_and_predict(
    file: UploadFile = File(...),
    predict_weeks: int = Form(1),
    current_user: dict = Depends(get_current_user),
):
    """上传日报文件，解析并预测"""
    try:
        # 读取文件
        file_bytes = await file.read()
        project_code = "UPLOAD"

        # 处理
        weekly_df, last_day_text = process_uploaded_file(file_bytes, file.filename, project_code)

        # 预测（传入最后一天原文用于生成日报文本）
        prediction = predict_from_dataframe(weekly_df, predict_weeks, last_day_text)

        # 组装解析结果
        weeks_data = weekly_df.to_dict(orient="records")
        # 转换日期类型
        for w in weeks_data:
            for k, v in w.items():
                if hasattr(v, "isoformat"):
                    w[k] = str(v)
                elif isinstance(v, (np.integer,)):
                    w[k] = int(v)
                elif isinstance(v, (np.floating,)):
                    w[k] = float(v)
                elif pd.isna(v):
                    w[k] = 0

        return {
            "parsed": {
                "weeks": weeks_data,
                "week_count": len(weekly_df)
            },
            "prediction": prediction
        }

    except RuntimeError as e:
        return {
            "parsed": None,
            "prediction": None,
            "error": str(e)
        }
    except Exception as e:
        return {
            "parsed": None,
            "prediction": None,
            "error": f"处理异常: {str(e)}"
        }


@app.get("/api/daily/health")
def health():
    return {"status": "ok"}


# ============================================================
# 5. 管理员路由
# ============================================================

from admin_routes import router as admin_router
app.include_router(admin_router)

# ============================================================
# 5.5 工期预警路由
# ============================================================

from duration_warning_api import router as warning_router
app.include_router(warning_router)

# ============================================================
# 6. 启动
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("  日报预测 API 服务")
    print(f"  http://127.0.0.1:8000")
    print(f"  http://127.0.0.1:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
