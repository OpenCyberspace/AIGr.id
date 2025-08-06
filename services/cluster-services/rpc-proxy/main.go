package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"strings"
	"sync"

	pb "rpc-proxy/service"

	"github.com/redis/go-redis/v9"
	"google.golang.org/grpc"
	"google.golang.org/grpc/metadata"
)

// RedisManager maintains active redis connections
type RedisManager struct {
	mu      sync.Mutex
	clients map[string]*redis.Client
}

func NewRedisManager() *RedisManager {
	return &RedisManager{
		clients: make(map[string]*redis.Client),
	}
}

func (rm *RedisManager) getClient(serviceName string) (*redis.Client, error) {
	rm.mu.Lock()
	defer rm.mu.Unlock()

	client, exists := rm.clients[serviceName]

	if exists && client != nil {
		if _, err := client.Ping(context.Background()).Result(); err == nil {
			return client, nil
		}
		// Reconnect if ping fails
		log.Printf("[RedisManager] Reconnecting to Redis at %s", serviceName)
		client.Close()
	}

	host := fmt.Sprintf("%s-executor-svc.blocks.svc.cluster.local:6379", serviceName)

	newClient := redis.NewClient(&redis.Options{
		Addr: host,
	})
	if _, err := newClient.Ping(context.Background()).Result(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis at %s: %v", host, err)
	}
	rm.clients[serviceName] = newClient
	return newClient, nil
}

// Server implements the InferenceProxy gRPC server
type Server struct {
	pb.UnimplementedInferenceProxyServer
	redisMgr *RedisManager
}

func (s *Server) Infer(ctx context.Context, req *pb.InferenceMessage) (*pb.InferenceRespose, error) {
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return nil, fmt.Errorf("missing metadata in request")
	}

	serviceHeaders := md.Get("x-service-name")
	if len(serviceHeaders) == 0 {
		return nil, fmt.Errorf("missing x-service-name header")
	}
	serviceName := strings.TrimSpace(serviceHeaders[0])

	client, err := s.redisMgr.getClient(serviceName)
	if err != nil {
		return nil, err
	}

	err = client.LPush(ctx, "EXECUTOR_INPUTS", req.RpcData).Err()
	if err != nil {
		return nil, fmt.Errorf("failed to push to Redis queue: %v", err)
	}

	return &pb.InferenceRespose{Message: true}, nil
}

func main() {
	lis, err := net.Listen("tcp", ":9000")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	redisMgr := NewRedisManager()

	pb.RegisterInferenceProxyServer(grpcServer, &Server{redisMgr: redisMgr})
	log.Println("gRPC InferenceProxy server started on :9000")
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("gRPC server failed: %v", err)
	}
}
