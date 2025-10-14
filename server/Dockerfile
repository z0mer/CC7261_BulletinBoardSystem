FROM python:3.11-alpine

WORKDIR /app

RUN pip install pyzmq

COPY server.py .

CMD ["python", "server.py"]