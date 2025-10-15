FROM python:3.14-slim

WORKDIR /app

RUN mkdir -p /app/downloads

COPY requirements.txt .

# Install packages
RUN apt-get update && \
    apt-get install -y python3-pip

# Install dependencies
RUN pip install --upgrade pip && \
    pip install uv && \
    uv pip install -r requirements.txt --system

# Source files
COPY src/silae/*.py /app/

ENV DOWNLOAD_DIR=/app/downloads

CMD ["sh", "-c", "python main.py -d $DOWNLOAD_DIR -i"]
