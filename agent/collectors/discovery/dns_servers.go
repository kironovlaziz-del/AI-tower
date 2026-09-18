package discovery

import (
	"log"
	"net"
	"os"
	"strings"
)

// discoverDNSServers reports the DNS servers this machine is configured
// to use (the "nameserver" lines in /etc/resolv.conf). These are real,
// in-use infrastructure services - reading the local resolver config is
// not a scan or a probe, it's reading a local file the OS already wrote.
func discoverDNSServers(rep *Reporter) {
	data, err := os.ReadFile("/etc/resolv.conf")
	if err != nil {
		log.Printf("[Discovery/DNS] Could not read /etc/resolv.conf: %v", err)
		return
	}

	for _, line := range strings.Split(string(data), "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "nameserver") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 2 {
			continue
		}
		ip := fields[1]
		if net.ParseIP(ip) == nil {
			continue
		}
		// 127.0.0.53 is systemd-resolved's local stub, not a real
		// upstream DNS server - reporting it as network infrastructure
		// would be misleading, so skip loopback resolvers.
		if net.ParseIP(ip).IsLoopback() {
			continue
		}

		details := map[string]interface{}{}
		// A reverse lookup often reveals the server's real hostname,
		// which is far more useful to an admin than a bare IP.
		if names, err := net.LookupAddr(ip); err == nil && len(names) > 0 {
			details["ptr"] = strings.TrimSuffix(names[0], ".")
		}

		log.Printf("[Discovery/DNS] Found DNS server: %s", ip)
		rep.Add(DiscoveredService{
			ServiceType:   "dns",
			Host:          ip,
			Port:          53,
			DiscoveredVia: "resolv_conf",
			Details:       details,
		})
	}
}
