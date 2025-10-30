FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pyzmq

COPY broker.py .

CMD ["python", "-u", "broker.py"]

