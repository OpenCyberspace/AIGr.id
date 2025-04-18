# Use a minimal Python base image
FROM python:3.10-buster

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip3 install --upgrade pip && pip3 install -e .

CMD ["python3"]
