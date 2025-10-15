FROM python:3.11-alpine

WORKDIR /app

RUN pip install pyzmq

COPY client.py .

CMD ["python", "client.py"]