FROM python:3.6.9-buster 

COPY service /service 
WORKDIR /service 

RUN pip3 install -r requirements.txt 
RUN pip3 install uvicorn

ENTRYPOINT ["uvicorn", "main:app", "--host=0.0.0.0"]