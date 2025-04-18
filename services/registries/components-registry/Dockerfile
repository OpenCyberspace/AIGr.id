FROM node:latest as source_builder
ENV CONTAINER=1
COPY . /app
WORKDIR /app
RUN npm install
RUN rm -f .env
RUN npm install -g nexe
RUN nexe -t x64-12.9.1

FROM ubuntu:latest

ENV CONTAINER=1
RUN mkdir /app
COPY --from=source_builder /app/app /app/
COPY --from=source_builder /app/data /app/data
COPY --from=source_builder /app/log_config_container.json /app
WORKDIR /app

ENTRYPOINT ["./app"]
