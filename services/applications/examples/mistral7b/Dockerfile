FROM aios_transformers:v1

COPY . /app

WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT [ "python3", "block.py" ]