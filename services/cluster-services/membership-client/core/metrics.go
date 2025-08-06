package core

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"net"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
)

func readMemInfo() (int64, error) {
	data, err := ioutil.ReadFile("/proc/meminfo")
	if err != nil {
		return 0, fmt.Errorf("failed to read meminfo: %v", err)
	}

	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "MemTotal:") {
			fields := strings.Fields(line)
			if len(fields) < 2 {
				return 0, errors.New("malformed MemTotal line")
			}
			return strconv.ParseInt(fields[1], 10, 64)
		}
	}
	return 0, errors.New("MemTotal not found")
}

func readStorageInfo() (int, int64, error) {
	cmd := exec.Command("df", "-BM", "/")
	output, err := cmd.Output()
	if err != nil {
		return 0, 0, fmt.Errorf("failed to get storage info: %v", err)
	}
	lines := strings.Split(string(output), "\n")
	if len(lines) < 2 {
		return 0, 0, errors.New("unexpected df output")
	}
	fields := strings.Fields(lines[1])
	if len(fields) < 2 {
		return 0, 0, errors.New("malformed df output")
	}
	sizeStr := strings.TrimSuffix(fields[1], "M")
	size, err := strconv.ParseInt(sizeStr, 10, 64)
	if err != nil {
		return 0, 0, err
	}
	return 1, size, nil
}

func queryGPUInfo() (GPUInfo, error) {
	cmd := exec.Command("nvidia-smi",
		"--query-gpu=name,memory.total",
		"--format=csv,noheader,nounits")
	var out bytes.Buffer
	cmd.Stdout = &out
	if err := cmd.Run(); err != nil {
		return GPUInfo{}, fmt.Errorf("nvidia-smi failed: %v", err)
	}

	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	totalMem := int64(0)
	modelSet := make(map[string]struct{})
	var entries []GPUEntry

	for _, line := range lines {
		fields := strings.Split(strings.TrimSpace(line), ",")
		if len(fields) != 2 {
			continue
		}
		model := strings.TrimSpace(fields[0])
		memMB, _ := strconv.ParseInt(strings.TrimSpace(fields[1]), 10, 64)
		modelSet[model] = struct{}{}
		totalMem += memMB
		entries = append(entries, GPUEntry{
			ModelName: model,
			Memory:    memMB,
		})
	}

	models := make([]string, 0, len(modelSet))
	for model := range modelSet {
		models = append(models, model)
	}

	return GPUInfo{
		Count:      len(entries),
		Memory:     totalMem,
		ModelNames: models,
		Features:   []string{"fp16", "tensorcore"}, // assume default
		GPUs:       entries,
	}, nil
}

func GatherNodeData(gpuEnabled bool, nodeID string, metadataPath string) (*NodeData, error) {
	if nodeID == "" {
		hostname, err := os.Hostname()
		if err != nil {
			return nil, fmt.Errorf("failed to get hostname: %v", err)
		}
		nodeID = hostname
	}

	// --- Memory ---
	memKB, err := readMemInfo()
	if err != nil {
		return nil, err
	}

	// --- Storage ---
	disks, storageMB, err := readStorageInfo()
	if err != nil {
		return nil, err
	}

	// --- Network ---
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil, fmt.Errorf("failed to read network interfaces: %v", err)
	}
	netCount := len(ifaces)

	// --- Metadata ---
	metadata := make(map[string]interface{})
	if metadataPath != "" {
		content, err := ioutil.ReadFile(metadataPath)
		if err != nil {
			return nil, fmt.Errorf("failed to read metadata file: %v", err)
		}
		if err := json.Unmarshal(content, &metadata); err != nil {
			return nil, fmt.Errorf("invalid metadata JSON: %v", err)
		}
	}

	// --- GPU Info ---
	var gpuInfo GPUInfo
	if gpuEnabled {
		gpuInfo, err = queryGPUInfo()
		if err != nil {
			return nil, err
		}
	}

	// Final assembly
	node := &NodeData{
		ID:     nodeID,
		Memory: memKB / 1024,
		Swap:   0,
		VCPUs: VCPUInfo{
			Count: runtime.NumCPU(),
		},
		Storage: StorageInfo{
			Disks: disks,
			Size:  storageMB,
		},
		Network: NetworkInfo{
			Interfaces:  netCount, // placeholder
			TxBandwidth: 10000,
		},
		GPUs:     gpuInfo,
		Metadata: metadata,
	}

	return node, nil
}
