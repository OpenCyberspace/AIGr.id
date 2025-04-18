# Use an official Python runtime as a parent image
FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 4000
CMD ["python", "main.py"]
