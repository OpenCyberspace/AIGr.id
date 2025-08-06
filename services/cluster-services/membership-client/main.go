package main

import (
	"encoding/json"
	"flag"
	"log"
	"os"

	clusterclient "membership-client/core"
)

func main() {
	// --- CLI Flags ---
	var (
		gpu        = flag.Bool("gpu", false, "Enable GPU info")
		metadata   = flag.String("metadata", "", "Path to metadata JSON")
		nodeID     = flag.String("node-id", "", "Optional node ID")
		dump       = flag.Bool("dump-json", false, "Dump node data as JSON and exit")
		action     = flag.String("action", "", "Action: dry-run-add, dry-run-remove, join, remove")
		apiBaseURL = flag.String("api", "http://localhost:8080", "API base URL")
	)
	flag.Parse()

	logger := log.New(os.Stdout, "[CLI] ", log.LstdFlags)
	client := clusterclient.NewClusterClient(*apiBaseURL, logger)

	// --- Collect Node Info ---
	nodeData, err := clusterclient.GatherNodeData(*gpu, *nodeID, *metadata)
	if err != nil {
		logger.Fatalf("Failed to collect node info: %v", err)
	}

	if *dump {
		writeJSON("node_data.json", nodeData)
		logger.Println("Node data dumped to node_data.json")
		return
	}

	// --- Action Routing ---
	switch *action {
	case "dry-run-add":
		resp, err := client.DryRunAddNodePrecheck(*nodeData)
		if err != nil {
			logger.Fatalf("Dry run (add-node) failed: %v", err)
		}
		logger.Printf("Precheck add-node passed? %v\n", resp.Allowed)

	case "dry-run-remove":
		if nodeData.ID == "" {
			logger.Fatalf("Node ID required for dry-run-remove")
		}
		resp, err := client.DryRunRemoveNodePrecheck(nodeData.ID)
		if err != nil {
			logger.Fatalf("Dry run (remove-node) failed: %v", err)
		}
		logger.Printf("Precheck remove-node passed? %v\n", resp.Allowed)

	case "join":
		if err := client.JoinNode(*nodeData, "local_network", ""); err != nil {
			logger.Fatalf("Join failed: %v", err)
		}

	case "remove":
		if err := client.RemoveNode(nodeData.ID); err != nil {
			logger.Fatalf("Remove failed: %v", err)
		}

	default:
		logger.Fatalf("Unknown or missing --action: must be one of dry-run-add, dry-run-remove, join, remove")
	}
}

func writeJSON(filename string, data interface{}) {
	f, err := os.Create(filename)
	if err != nil {
		log.Fatalf("Failed to create %s: %v", filename, err)
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	if err := enc.Encode(data); err != nil {
		log.Fatalf("Failed to write JSON: %v", err)
	}
}
