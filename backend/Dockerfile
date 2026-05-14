FROM python:3.11-slim

LABEL version="1.24"
LABEL description="动力电池拆卸知识图谱推理系统"

WORKDIR /app

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .. .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
