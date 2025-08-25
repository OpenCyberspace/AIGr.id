package core

import (
	"fmt"
	"os/exec"
)

type NodeData struct {
	ID       string                 `json:"id"`
	Memory   int64                  `json:"memory"` // in MB
	Swap     int64                  `json:"swap"`   // in MB
	VCPUs    VCPUInfo               `json:"vcpus"`
	Storage  StorageInfo            `json:"storage"`
	Network  NetworkInfo            `json:"network"`
	GPUs     GPUInfo                `json:"gpus"`
	Tags     []string               `json:"tags"`
	Metadata map[string]interface{} `json:"nodeMetadata"` // arbitrary key-value fields
}

type VCPUInfo struct {
	Count int `json:"count"`
}

type StorageInfo struct {
	Disks int   `json:"disks"`
	Size  int64 `json:"size"`
}

type NetworkInfo struct {
	Interfaces  int `json:"interfaces"`
	RxBandwidth int `json:"rxBandwidth"`
	TxBandwidth int `json:"txBandwidth"`
}

type GPUInfo struct {
	Count      int        `json:"count"`
	Memory     int64      `json:"memory"`     // in MB
	ModelNames []string   `json:"modelNames"` // e.g., "NVIDIA A100"
	Features   []string   `json:"features"`   // e.g., "fp16", "tensorcore"
	GPUs       []GPUEntry `json:"gpus"`
}

type GPUEntry struct {
	ModelName string `json:"modelName"`
	Memory    int64  `json:"memory"`
}

func InstallPrecheck(gpu bool) error {
	// List of required binaries
	required := []string{"kubeadm", "containerd"}

	// Add GPU check if needed
	if gpu {
		required = append(required, "nvidia-smi")
	}

	// Check each binary
	for _, bin := range required {
		if _, err := exec.LookPath(bin); err != nil {
			return fmt.Errorf("required binary not found: %s", bin)
		}
	}

	return nil
}
