package collectors

import (
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"shadow-ai-agent/config"
	"shadow-ai-agent/reporters"
)

// KnownAIProcesses contains names of known AI engines and runtimes.
var KnownAIProcesses = map[string]float64{
	"ollama":                 0.6,
	"lmstudio":               0.7,
	"vllm":                   0.8,
	"localai":                0.7,
	"llama-server":           0.6,
	"llama.cpp":              0.6,
	"text-generation-webui": 0.7,
	"jan":                    0.6,
	"anythingllm":            0.6,
	"tabby":                  0.5,
	"litellm":                0.5,
}

// ProcessCollector inspects running processes on the host.
type ProcessCollector struct {
	cfg      *config.AgentConfig
	reporter *reporters.Reporter
	seenPIDs map[int]string
	mu       sync.Mutex
}

// NewProcessCollector creates an instance of the process monitor.
func NewProcessCollector(cfg *config.AgentConfig, rep *reporters.Reporter) *ProcessCollector {
	return &ProcessCollector{
		cfg:      cfg,
		reporter: rep,
		seenPIDs: make(map[int]string),
	}
}

// ScanOnce reads /proc on Linux systems to detect active local AI runtimes.
func (c *ProcessCollector) ScanOnce() {
	procDir, err := os.Open("/proc")
	if err != nil {
		return // Not running on Linux or /proc is inaccessible
	}
	defer procDir.Close()

	entries, err := procDir.Readdirnames(-1)
	if err != nil {
		return
	}

	currentUser := os.Getenv("USER")
	activePIDs := make(map[int]bool)

	for _, entry := range entries {
		pid, err := strconv.Atoi(entry)
		if err != nil {
			continue
		}
		activePIDs[pid] = true

		commBytes, err := os.ReadFile(fmt.Sprintf("/proc/%d/comm", pid))
		if err != nil {
			continue
		}
		commName := strings.TrimSpace(string(commBytes))
		commLower := strings.ToLower(commName)

		cmdlineBytes, _ := os.ReadFile(fmt.Sprintf("/proc/%d/cmdline", pid))
		cmdline := strings.ReplaceAll(string(cmdlineBytes), string([]byte{0}), " ")

		for aiTool, risk := range KnownAIProcesses {
			if strings.Contains(commLower, aiTool) || strings.Contains(strings.ToLower(cmdline), aiTool) {
				c.mu.Lock()
				alreadyReported := c.seenPIDs[pid] == commName
				if !alreadyReported {
					c.seenPIDs[pid] = commName
				}
				c.mu.Unlock()

				if !alreadyReported {
					log.Printf("[ProcessCollector] Detected AI runtime process '%s' (PID %d)", commName, pid)
					c.reporter.Submit(reporters.TelemetryEvent{
						EventType:   "process_detected",
						AgentID:     c.cfg.AgentID,
						Domain:      "localhost",
						UserID:      currentUser,
						RiskScore:   risk,
						ActionTaken: "monitored",
						Payload: map[string]interface{}{
							"process_name": commName,
							"pid":          pid,
							"cmdline":      cmdline,
							"ai_tool":      aiTool,
						},
					})
				}
				break
			}
		}
	}

	// Purge terminated processes from seen cache
	c.mu.Lock()
	for pid := range c.seenPIDs {
		if !activePIDs[pid] {
			delete(c.seenPIDs, pid)
		}
	}
	c.mu.Unlock()
}

// RunPeriodic runs the process scanner on a regular schedule.
func (c *ProcessCollector) RunPeriodic(stopChan <-chan struct{}) {
	ticker := time.NewTicker(time.Duration(c.cfg.ScanIntervalSec) * time.Second)
	defer ticker.Stop()

	c.ScanOnce()
	for {
		select {
		case <-stopChan:
			return
		case <-ticker.C:
			c.ScanOnce()
		}
	}
}
