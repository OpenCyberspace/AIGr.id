FROM python:3.6.9-buster 


#install helm inside the container
RUN wget https://get.helm.sh/helm-v3.3.4-linux-amd64.tar.gz
RUN tar -xvf helm-v3.3.4-linux-amd64.tar.gz && cp linux-amd64/helm /usr/local/bin
COPY service /service 
WORKDIR /service 

RUN pip3 install -r requirements.txt 
RUN pip3 install uvicorn
ENV TEST=No
ENTRYPOINT ["uvicorn", "main:app", "--host=0.0.0.0"]