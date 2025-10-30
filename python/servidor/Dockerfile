FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pyzmq msgpack

COPY servidor.py .

CMD ["python", "-u", "servidor.py"]