FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV APP_HOST=0.0.0.0
EXPOSE 10000
CMD gunicorn wsgi:app --bind 0.0.0.0:${PORT:-10000} --workers 2 --timeout 120
