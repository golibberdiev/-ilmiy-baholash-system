# Ilmiy faoliyat samaradorligini baholash tizimi

Ushbu loyiha FastAPI asosida ishlab chiqilgan:
- Foydalanuvchi interfeysi (`/`)
- Admin panel (`/admin`)
- Ilmiy faoliyatni R, P, O, I bloklari bo‘yicha baholash
- Hisob-kitob natijalarini SQLite bazaga yozish
- Admin jadvalini Excel (`.xlsx`) formatida eksport qilish

## Texnologiyalar

- Python 3.11
- FastAPI
- Uvicorn
- SQLAlchemy + SQLite
- openpyxl
- Bootstrap 5 + Chart.js (frontend)

---

## Lokal ishga tushirish

```bash
# Virtual muhit (ixtiyoriy, tavsiya etiladi)
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Serverni ishga tushirish
uvicorn main:app --reload
