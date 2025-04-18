FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY service /service 
WORKDIR /service 

RUN pip3 install -r requirements.txt 
RUN pip3 install uvicorn==0.11.8
ENV TEST=No
ENTRYPOINT ["python3", "main.py"]