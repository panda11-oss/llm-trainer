FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    requests \
    python-dotenv \
    apscheduler \
    chromadb

COPY src ./src

CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8001"]