package discovery

import (
	"encoding/binary"
	"encoding/hex"
	"log"
	"net"
	"os"
	"strings"
)

// discoverGateway reports the machine's default gateway, parsed from
// /proc/net/route (Linux). The gateway is frequently also the DHCP
// server and/or the network firewall, so surfacing it gives the admin a
// starting point for those. Reading /proc/net/route is a local kernel
// table read - no scanning, no privileges.
func discoverGateway(rep *Reporter) {
	data, err := os.ReadFile("/proc/net/route")
	if err != nil {
		// Not Linux, or /proc unavailable - nothing to do, not an error
		// worth alarming about.
		return
	}

	lines := strings.Split(string(data), "\n")
	// Header is line 0; each subsequent line is a route. The default
	// route is the one whose Destination is 00000000.
	for _, line := range lines[1:] {
		fields := strings.Fields(line)
		if len(fields) < 3 {
			continue
		}
		iface, destHex, gwHex := fields[0], fields[1], fields[2]
		if destHex != "00000000" {
			continue
		}
		gwIP := parseLittleEndianHexIP(gwHex)
		if gwIP == nil || gwIP.IsUnspecified() {
			continue
		}

		details := map[string]interface{}{"interface": iface}
		if names, err := net.LookupAddr(gwIP.String()); err == nil && len(names) > 0 {
			details["ptr"] = strings.TrimSuffix(names[0], ".")
		}

		log.Printf("[Discovery/GW] Found default gateway: %s (via %s)", gwIP, iface)
		rep.Add(DiscoveredService{
			ServiceType:   "gateway",
			Host:          gwIP.String(),
			DiscoveredVia: "routing_table",
			Details:       details,
		})
		return // one default route is enough
	}
}

// parseLittleEndianHexIP parses the 8-hex-char, little-endian IPv4 form
// used in /proc/net/route (e.g. "0100A8C0" -> 192.168.0.1).
func parseLittleEndianHexIP(h string) net.IP {
	if len(h) != 8 {
		return nil
	}
	b, err := hex.DecodeString(h)
	if err != nil {
		return nil
	}
	// The field is the address in native (little-endian) byte order.
	v := binary.LittleEndian.Uint32(b)
	ip := make(net.IP, 4)
	binary.BigEndian.PutUint32(ip, v)
	return ip
}
