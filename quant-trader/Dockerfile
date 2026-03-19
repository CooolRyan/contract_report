# quant-trader: 키움 REST 기반 전략 루프 + Spring 연동
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 기본은 실거래 루프 (환경변수로 broker / contract_report 설정)
CMD ["python", "main.py", "trade"]
