FROM python:3.11-buster

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8765
EXPOSE 7777
CMD ["python", "main.py"]