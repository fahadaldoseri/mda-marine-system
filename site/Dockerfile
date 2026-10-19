# حاوية خدمة ويب هوك بوت تلغرام — مركز الوعي بالمجال البحري (MDA)
# تُقدّم مسار /api/telegram/webhook و /healthz فقط؛ والموقع الثابت يُقدَّم من مخرجات البناء.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000

WORKDIR /app
RUN pip install --no-cache-dir "pymysql==1.1.1"

COPY server/app.py /app/app.py

EXPOSE 3000
CMD ["python3", "/app/app.py"]