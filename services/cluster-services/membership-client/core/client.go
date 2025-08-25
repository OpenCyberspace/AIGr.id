package core

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os/exec"
)

// ClusterClient represents the API client for the cluster membership system.
type ClusterClient struct {
	BaseURL string
	Logger  *log.Logger
}

// NewClusterClient initializes the ClusterClient with the base URL.
func NewClusterClient(baseURL string, logger *log.Logger) *ClusterClient {
	return &ClusterClient{
		BaseURL: baseURL,
		Logger:  logger,
	}
}

type PreCheckAddNodeRequest struct {
	NodeData NodeData `json:"node_data"`
}

type PreCheckAddNodeResponse struct {
	Allowed         bool        `json:"allowed"`
	NodeData        NodeData    `json:"node_data"`
	Success         bool        `json:"success"`
	Data            interface{} `json:"data"`
	ClusterResponse interface{} `json:"cluster_response"`
}

type MgmtRequest struct {
	MgmtAction string                 `json:"mgmt_action"`
	MgmtData   map[string]interface{} `json:"mgmt_data"`
}

type MgmtResponse struct {
	Result  interface{} `json:"result"`
	Success bool        `json:"success"`
	Error   string      `json:"error,omitempty"`
}

type JoinNodeRequest struct {
	NodeData NodeData `json:"node_data"`
	Mode     string   `json:"mode,omitempty"`
	CustomIP string   `json:"custom_ip,omitempty"`
}

type JoinNodeResponse struct {
	Result struct {
		Success     bool   `json:"success"`
		JoinCommand string `json:"join_command"`
		Message     string `json:"message"`
	} `json:"result"`
	Success bool   `json:"success"`
	Error   string `json:"error,omitempty"`
}

type PreCheckRemoveNodeRequest struct {
	NodeID string `json:"node_id"`
}

type PreCheckRemoveNodeResponse struct {
	Allowed bool   `json:"allowed"`
	NodeID  string `json:"node_id"`
	Success bool   `json:"success"`
	Error   string `json:"error,omitempty"`
}

type RemoveNodeRequest struct {
	NodeID   string `json:"node_id"`
	Mode     string `json:"mode,omitempty"`
	CustomIP string `json:"custom_ip,omitempty"`
}

type RemoveNodeResponse struct {
	Result  interface{} `json:"result"`
	Success bool        `json:"success"`
	Error   string      `json:"error,omitempty"`
}

func (c *ClusterClient) PreCheckAddNode(req PreCheckAddNodeRequest, clusterId string) (*PreCheckAddNodeResponse, error) {
	return post[PreCheckAddNodeRequest, PreCheckAddNodeResponse](c, "/pre-checks/add-node/"+clusterId, req)
}

func (c *ClusterClient) MgmtAddNode(req MgmtRequest, clusterId string) (*MgmtResponse, error) {
	return post[MgmtRequest, MgmtResponse](c, "/pre-checks/add-node/mgmt", req)
}

func (c *ClusterClient) JoinNodeToCluster(req JoinNodeRequest, clusterId string) (*JoinNodeResponse, error) {
	return post[JoinNodeRequest, JoinNodeResponse](c, "/pre-checks/add-node/join", req)
}

func (c *ClusterClient) PreCheckRemoveNode(req PreCheckRemoveNodeRequest, clusterId string) (*PreCheckRemoveNodeResponse, error) {
	return post[PreCheckRemoveNodeRequest, PreCheckRemoveNodeResponse](c, "/pre-checks/remove-node", req)
}

func (c *ClusterClient) MgmtRemoveNode(req MgmtRequest, clusterId string) (*MgmtResponse, error) {
	return post[MgmtRequest, MgmtResponse](c, "/pre-checks/remove-node/mgmt", req)
}

func (c *ClusterClient) RemoveNodeFromCluster(req RemoveNodeRequest, clusterId string) (*RemoveNodeResponse, error) {
	return post[RemoveNodeRequest, RemoveNodeResponse](c, "/pre-checks/remove-node/delete", req)
}

// --- Helper ---

func post[Req any, Res any](c *ClusterClient, path string, payload Req) (*Res, error) {
	fullURL := c.BaseURL + path
	c.Logger.Printf("POST %s", fullURL)

	data, err := json.Marshal(payload)
	if err != nil {
		c.Logger.Printf("Failed to marshal request: %v", err)
		return nil, err
	}

	resp, err := http.Post(fullURL, "application/json", bytes.NewBuffer(data))
	if err != nil {
		c.Logger.Printf("HTTP POST error: %v", err)
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		data, _ := io.ReadAll(resp.Body)
		c.Logger.Printf("error message: %s", data)
		return nil, fmt.Errorf("%s", string(data))
	}

	var out Res
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		c.Logger.Printf("Failed to decode response: %v", err)
		return nil, err
	}

	c.Logger.Printf("response: %v", out)

	return &out, nil
}

// main methods:

func (c *ClusterClient) DryRunAddNodePrecheck(nodeData NodeData, clusterId string) (*PreCheckAddNodeResponse, error) {
	c.Logger.Printf("[DryRunAddNodePrecheck] Sending node data for precheck: %+v", nodeData)

	resp, err := post[NodeData, PreCheckAddNodeResponse](c, "/pre-check-policies/add_node/dry_run/"+clusterId, nodeData)
	if err != nil {
		c.Logger.Printf("[DryRunAddNodePrecheck] Error: %v", err)
		return nil, err
	}
	if !resp.Success {
		return resp, fmt.Errorf("add-node precheck failed: %s", resp.Data)
	}
	return resp, nil
}

func (c *ClusterClient) DryRunRemoveNodePrecheck(nodeID string, clusterId string) (*PreCheckRemoveNodeResponse, error) {
	req := PreCheckRemoveNodeRequest{
		NodeID: nodeID,
	}
	c.Logger.Printf("[DryRunRemoveNodePrecheck] Sending node ID for precheck: %s", nodeID)

	resp, err := post[PreCheckRemoveNodeRequest, PreCheckRemoveNodeResponse](c, "/pre-check-policies/remove_node/dry_run/"+clusterId, req)
	if err != nil {
		c.Logger.Printf("[DryRunRemoveNodePrecheck] Error: %v", err)
		return nil, err
	}
	if !resp.Success {
		return resp, fmt.Errorf("remove-node precheck failed: %s", resp.Error)
	}
	return resp, nil
}

func (c *ClusterClient) JoinNode(nodeData NodeData, mode string, customIP string, clusterId string) error {
	req := JoinNodeRequest{
		NodeData: nodeData,
		Mode:     mode,
		CustomIP: customIP,
	}

	c.Logger.Printf("[JoinNode] Requesting join command for node: %s", nodeData.ID)
	resp, err := post[JoinNodeRequest, JoinNodeResponse](c, "/join-node/"+clusterId, req)
	if err != nil {
		c.Logger.Printf("[JoinNode] HTTP error: %v", err)
		return err
	}
	if !resp.Success || !resp.Result.Success {
		return fmt.Errorf("join request failed: %s", resp.Error)
	}

	joinCmd := resp.Result.JoinCommand
	c.Logger.Printf("[JoinNode] Join command received: %s", joinCmd)

	// Execute the join command
	cmd := exec.Command("bash", "-c", joinCmd)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	c.Logger.Println("[JoinNode] Executing join command...")
	if err := cmd.Run(); err != nil {
		c.Logger.Printf("[JoinNode] Join command failed: %v\nstderr: %s", err, stderr.String())
		return fmt.Errorf("join command failed: %v\nstderr: %s", err, stderr.String())
	}

	c.Logger.Printf("[JoinNode] Join successful.\nstdout: %s", stdout.String())
	return nil
}

func (c *ClusterClient) RemoveNode(nodeID string, clusterId string) error {
	req := RemoveNodeRequest{
		NodeID: nodeID,
	}

	c.Logger.Printf("[RemoveNode] Sending removal request for node: %s", nodeID)

	resp, err := post[RemoveNodeRequest, RemoveNodeResponse](c, "/remove-node/"+clusterId, req)
	if err != nil {
		c.Logger.Printf("[RemoveNode] HTTP error: %v", err)
		return err
	}

	if !resp.Success {
		c.Logger.Printf("[RemoveNode] Failed: %s", resp.Error)
		return fmt.Errorf("remove-node request failed: %s", resp.Error)
	}

	c.Logger.Printf("[RemoveNode] Success: %v", resp.Result)
	return nil
}
