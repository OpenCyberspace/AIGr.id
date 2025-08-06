# Stage 1: Build the Go binary
FROM golang:1.23 AS builder


WORKDIR /rpc-proxy

# Copy go files and download dependencies
COPY go.mod ./
RUN go mod download

# Copy the source code
COPY . .

# RUN go install google.golang.org/grpc

# Build the Go binary statically
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o grpc-proxy

# Stage 2: Minimal runtime image
FROM alpine:3.19

WORKDIR /proxy
COPY --from=builder /rpc-proxy/grpc-proxy .

EXPOSE 9000
ENTRYPOINT ["./grpc-proxy"]
