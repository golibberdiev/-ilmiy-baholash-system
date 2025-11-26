# main.py
from typing import Dict
from datetime import datetime
from io import BytesIO

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

import openpyxl

from db import SessionLocal, engine, Base
from models import (
    EvaluationRequest,
    EvaluationResult,
    Evaluation,  # SQLAlchemy ORM modeli
)
from core import evaluate as evaluate_core  # asosiy hisoblash funksiyasi


# -----------------------------
# FastAPI ilovasini yaratish
# -----------------------------
app = FastAPI(
    title="Tashkilotda ilmiy faoliyat samaradorligini baholash",
    version="1.0.0",
)

# static papkani ulash (index.html, admin.html, logo va boshqalar shu yerda)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Bazadagi jadvallarni yaratish (agar bo‘lmasa)
Base.metadata.create_all(bind=engine)


# -----------------------------
# DB sessiya dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -----------------------------
# Foydalanuvchi interfeysi – /
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    """
    Asosiy (user) sahifa – static/index.html ni beradi.
    """
    try:
        # Asosiy variant – UTF-8
        with open("static/index.html", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # Agar tasodifan cp1251 yoki boshqa kodirovkada saqlangan bo‘lsa
        with open("static/index.html", encoding="cp1251", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="static/index.html topilmadi. Iltimos, fayl joylashuvini va nomini tekshiring.",
        )


# -----------------------------
# Admin panel – /admin
# -----------------------------
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """
    Admin paneli uchun alohida sahifa – static/admin.html.
    """
    try:
        with open("static/admin.html", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open("static/admin.html", encoding="cp1251", errors="ignore") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="static/admin.html topilmadi. Iltimos, fayl joylashuvini va nomini tekshiring.",
        )


# -----------------------------
# Hisoblash endpointi – /evaluate
# -----------------------------
@app.post("/evaluate", response_model=EvaluationResult)
def evaluate_endpoint(
    req: EvaluationRequest,
    db: Session = Depends(get_db),
):
    """
    Frontenddan kelgan ma'lumotlarni qabul qiladi,
    algoritm bo‘yicha hisoblaydi va natijani DB ga yozib qo‘yadi.
    """
    # 1) Asosiy hisob-kitob (core.py ichidagi evaluate_core)
    result: EvaluationResult = evaluate_core(req)

    # 2) Blok indekslarini bazaga saqlash uchun lug‘at ko‘rinishiga keltiramiz
    block_values: Dict[str, float] = {}
    for block in result.blocks:
        # block.block – "R", "P", "O", "I"
        # block.value – indeks qiymati
        block_values[block.block] = block.value

    # 3) ORM obyektini yaratib bazaga yozamiz
    db_obj = Evaluation(
        tashkilot=result.tashkilot,
        yil=result.yil,
        total_index=result.total_index,
        block_values=block_values,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    # 4) Frontendga pydantic model – EvaluationResult qaytadi
    return result


# -----------------------------
# Tarixiy natijalar – /evaluations
# -----------------------------
@app.get("/evaluations")
def list_evaluations(db: Session = Depends(get_db)):
    """
    Barcha saqlangan baholashlarni qaytaradi.
    Admin panel va foydalanuvchi interfeysidagi tahlil uchun ishlatiladi.
    """
    return (
        db.query(Evaluation)
        .order_by(Evaluation.yil, Evaluation.id)
        .all()
    )


# -----------------------------
# Jadvalni Excelga eksport – /export/excel
# -----------------------------
@app.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):
    """
    Barcha baholash natijalarini Excel (.xlsx) fayl ko‘rinishida eksport qiladi.
    Admin paneldagi jadvalga mos ustunlar:
    #, Tashkilot, Yil, Umumiy indeks, R, P, O, I
    """
    evaluations = (
        db.query(Evaluation)
        .order_by(Evaluation.yil, Evaluation.id)
        .all()
    )

    # Excel ishchi kitobi va varaq
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Baholashlar"

    # Sarlavha qatori
    headers = ["#", "Tashkilot", "Yil", "Umumiy indeks", "R", "P", "O", "I"]
    ws.append(headers)

    # Ma'lumotlarni yozish
    for idx, row in enumerate(evaluations, start=1):
        bv = row.block_values or {}
        ws.append([
            idx,
            row.tashkilot or "",
            row.yil or "",
            float(row.total_index) if row.total_index is not None else None,
            float(bv.get("R", 0)) if bv.get("R") is not None else None,
            float(bv.get("P", 0)) if bv.get("P") is not None else None,
            float(bv.get("O", 0)) if bv.get("O") is not None else None,
            float(bv.get("I", 0)) if bv.get("I") is not None else None,
        ])

    # Faylni xotirada saqlaymiz
    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"ilmiy_baholash_{datetime.now():%Y%m%d_%H%M%S}.xlsx"

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )
