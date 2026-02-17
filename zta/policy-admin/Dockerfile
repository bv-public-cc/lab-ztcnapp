FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends     openssh-client git ca-certificates     && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir kubernetes pyyaml ansible-core boto3

RUN useradd -m -u 10001 app
USER app
WORKDIR /app
COPY src/ /app/
ENV HOME=/home/app
CMD ["python", "-u", "dispatcher.py"]
