FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir requests selectolax lxml

COPY monitor.py /app/monitor.py

CMD ["python", "monitor.py"]
