package discovery

import (
	"bytes"
	"encoding/json"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"shadow-ai-agent/config"
)

// DiscoveredService matches the backend DiscoveredServiceIn schema
// (app/schemas/discovery.py). Host is required; Port/Details optional.
type DiscoveredService struct {
	ServiceType   string                 `json:"service_type"`
	Host          string                 `json:"host"`
	Port          int                    `json:"port,omitempty"`
	DiscoveredVia string                 `json:"discovered_via"`
	Details       map[string]interface{} `json:"details,omitempty"`
}

// discoveryBatch matches the backend DiscoveryReportRequest schema.
type discoveryBatch struct {
	Services []DiscoveredService `json:"services"`
}

// Reporter delivers discovered services to POST /discovery/report.
//
// It is separate from the telemetry Reporter on purpose: discovery has a
// different endpoint, a different payload schema, and a different cadence
// (a handful of services found on a slow scan interval, versus a stream
// of per-event telemetry). Sharing one Reporter would force one schema to
// masquerade as the other. It does reuse the same ingestion key and base
// derivation, so an operator configures the agent once.
type Reporter struct {
	cfg        *config.AgentConfig
	reportURL  string
	httpClient *http.Client
	mu         sync.Mutex
	// Dedup within the agent process: the same service found by two
	// methods (or on two consecutive scans) is only sent once per flush,
	// keyed by service_type+host. The backend also dedups, but not
	// flooding it in the first place keeps logs and traffic clean.
	pending map[string]DiscoveredService
}

// deriveReportURL turns the configured telemetry APIURL into the sibling
// discovery endpoint, so the operator only ever sets one URL. It swaps a
// trailing "/shadow-ai/ingest" for "/discovery/report"; if the URL isn't
// in that expected shape it falls back to apping the path onto the API
// root it can infer, and worst case logs and uses the raw value.
func deriveReportURL(apiURL string) string {
	if strings.HasSuffix(apiURL, "/shadow-ai/ingest") {
		return strings.TrimSuffix(apiURL, "/shadow-ai/ingest") + "/discovery/report"
	}
	// Fall back: if it ends in /ingest at least, replace the last two
	// path segments.
	if i := strings.LastIndex(apiURL, "/api/"); i != -1 {
		// keep scheme+host+/api/v1
		if j := strings.Index(apiURL[i+len("/api/"):], "/"); j != -1 {
			root := apiURL[:i+len("/api/")+j]
			return root + "/discovery/report"
		}
	}
	log.Printf("[Discovery] Could not derive discovery URL from %q; using it as-is", apiURL)
	return apiURL
}

func NewReporter(cfg *config.AgentConfig) *Reporter {
	return &Reporter{
		cfg:        cfg,
		reportURL:  deriveReportURL(cfg.APIURL),
		httpClient: &http.Client{Timeout: 15 * time.Second},
		pending:    make(map[string]DiscoveredService),
	}
}

// Add queues a discovered service for the next flush (deduplicated).
func (r *Reporter) Add(svc DiscoveredService) {
	if svc.Host == "" || svc.ServiceType == "" {
		return
	}
	r.mu.Lock()
	r.pending[svc.ServiceType+"|"+svc.Host] = svc
	r.mu.Unlock()
}

// Flush sends everything queued and clears the buffer. Safe to call with
// nothing pending (it no-ops).
func (r *Reporter) Flush() {
	r.mu.Lock()
	if len(r.pending) == 0 {
		r.mu.Unlock()
		return
	}
	services := make([]DiscoveredService, 0, len(r.pending))
	for _, svc := range r.pending {
		services = append(services, svc)
	}
	r.pending = make(map[string]DiscoveredService)
	r.mu.Unlock()

	data, err := json.Marshal(discoveryBatch{Services: services})
	if err != nil {
		log.Printf("[Discovery] JSON marshal error: %v", err)
		return
	}

	req, err := http.NewRequest("POST", r.reportURL, bytes.NewBuffer(data))
	if err != nil {
		log.Printf("[Discovery] Failed to build request: %v", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Ingestion-Key", r.cfg.IngestionKey)

	resp, err := r.httpClient.Do(req)
	if err != nil {
		log.Printf("[Discovery] Network error reporting %d services: %v", len(services), err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		log.Printf("[Discovery] Reported %d discovered services (HTTP %d)", len(services), resp.StatusCode)
	} else {
		log.Printf("[Discovery] Report rejected (HTTP %d)", resp.StatusCode)
	}
}
