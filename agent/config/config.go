package config

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"os"
	"strings"
)

// AgentConfig holds runtime configuration for the endpoint collector.
type AgentConfig struct {
	APIURL           string   `json:"api_url"`
	IngestionKey     string   `json:"ingestion_key"`
	AgentID          string   `json:"agent_id"`
	ScanIntervalSec  int      `json:"scan_interval_sec"`
	BatchIntervalSec int      `json:"batch_interval_sec"`
	BatchSize        int      `json:"batch_size"`
	ModelSearchPaths []string `json:"model_search_paths"`
	DiscoveryEnabled     bool     `json:"discovery_enabled"`
	DiscoveryIntervalSec int      `json:"discovery_interval_sec"`
}

// GenerateRandomID creates a random hex identifier.
func GenerateRandomID(bytesLen int) string {
	b := make([]byte, bytesLen)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// LoadConfig reads config from a JSON file and applies environment overrides.
func LoadConfig(configPath string) (*AgentConfig, error) {
	hostname, _ := os.Hostname()
	cfg := &AgentConfig{
		APIURL:           "http://localhost:8000/api/v1/shadow_ai/ingest",
		IngestionKey:     "default-key",
		AgentID:          hostname,
		ScanIntervalSec:  30,
		BatchIntervalSec: 10,
		BatchSize:        50,
		ModelSearchPaths: []string{},
		DiscoveryEnabled:     false,
		DiscoveryIntervalSec: 900,
	}

	if data, err := os.ReadFile(configPath); err == nil {
		_ = json.Unmarshal(data, cfg)
	}

	if envURL := os.Getenv("AGENT_API_URL"); envURL != "" {
		cfg.APIURL = envURL
	}
	if envKey := os.Getenv("AGENT_INGESTION_KEY"); envKey != "" {
		cfg.IngestionKey = envKey
	}
	if os.Getenv("AGENT_DISCOVERY") == "true" {
		cfg.DiscoveryEnabled = true
	}
	if envID := os.Getenv("AGENT_ID"); envID != "" {
		cfg.AgentID = envID
	}
	if cfg.AgentID == "" {
		cfg.AgentID = hostname
	}

	// Expand ~ in search paths
	homeDir, _ := os.UserHomeDir()
	for i, path := range cfg.ModelSearchPaths {
		if strings.HasPrefix(path, "~/") {
			cfg.ModelSearchPaths[i] = strings.Replace(path, "~", homeDir, 1)
		}
	}

	return cfg, nil
}
