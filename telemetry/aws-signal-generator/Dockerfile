FROM python:3.11-slim
RUN pip install --no-cache-dir boto3 kubernetes
WORKDIR /app
COPY src/ /app/
CMD ["python","-u","generate_signals.py"]
