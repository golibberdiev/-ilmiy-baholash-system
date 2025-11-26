# FastAPI ilovamiz uchun engil Python imiji
FROM python:3.12-slim

# Konteyner ichida ishchi papka
WORKDIR /app

# 1. Faqat dependenciesni o'rnatamiz
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 2. Ilovaning qolgan fayllarini ko'chiramiz
COPY . .

# Railway uchun port
ENV PORT=8000
EXPOSE 8000

# 3. FastAPI ni uvicorn orqali ishga tushiramiz
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
