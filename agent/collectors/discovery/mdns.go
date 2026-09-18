package discovery

import (
	"log"
	"net"
	"strings"
	"time"

	"golang.org/x/net/dns/dnsmessage"
)

// mDNS multicast group and port (RFC 6762). Devices and services on the
// LAN announce themselves here unsolicited, and answer PTR queries for
// service types - so LISTENING (plus one gentle service-enumeration
// query) is passive discovery, not scanning: we only learn what hosts
// choose to broadcast about themselves.
const (
	mdnsAddr = "224.0.0.251:5353"
	// The meta-query that asks "what service types exist on this
	// network?" - the standard DNS-SD service enumeration (RFC 6763).
	mdnsServiceEnumQuery = "_services._dns-sd._udp.local."
)

// discoverViaMDNS joins the mDNS multicast group, sends one service
// enumeration query, and collects answers for a short window. Uses only
// UDP multicast (net package) + a DNS message parser - no raw sockets,
// no CAP_NET_RAW, so it works as an unprivileged process. The only
// prerequisite is that UDP :5353 can be bound; if a local mDNS daemon
// already holds it exclusively we log and skip rather than fail.
func discoverViaMDNS(rep *Reporter) {
	addr, err := net.ResolveUDPAddr("udp4", mdnsAddr)
	if err != nil {
		log.Printf("[Discovery/mDNS] resolve error: %v", err)
		return
	}

	// ListenMulticastUDP joins the group and (on most systems) sets
	// SO_REUSEADDR so we can coexist with an existing responder.
	conn, err := net.ListenMulticastUDP("udp4", nil, addr)
	if err != nil {
		log.Printf("[Discovery/mDNS] cannot listen on %s (likely held by a local mDNS daemon): %v", mdnsAddr, err)
		return
	}
	defer conn.Close()

	_ = conn.SetReadBuffer(65536)

	// Send the service-enumeration query so responders reply promptly,
	// rather than waiting only for spontaneous announcements.
	if q := buildMDNSQuery(mdnsServiceEnumQuery); q != nil {
		if _, err := conn.WriteToUDP(q, addr); err != nil {
			log.Printf("[Discovery/mDNS] query send failed (will still listen passively): %v", err)
		}
	}

	deadline := time.Now().Add(4 * time.Second)
	_ = conn.SetReadDeadline(deadline)

	seenHosts := map[string]bool{}
	buf := make([]byte, 65536)
	for time.Now().Before(deadline) {
		n, _, err := conn.ReadFromUDP(buf)
		if err != nil {
			break // deadline reached - normal end of the listen window
		}
		handleMDNSPacket(buf[:n], seenHosts, rep)
	}
}

// buildMDNSQuery builds a single PTR question for the given name.
func buildMDNSQuery(name string) []byte {
	qname, err := dnsmessage.NewName(name)
	if err != nil {
		return nil
	}
	msg := dnsmessage.Message{
		Header: dnsmessage.Header{Response: false},
		Questions: []dnsmessage.Question{{
			Name:  qname,
			Type:  dnsmessage.TypePTR,
			Class: dnsmessage.ClassINET,
		}},
	}
	packed, err := msg.Pack()
	if err != nil {
		return nil
	}
	return packed
}

// handleMDNSPacket parses an mDNS response and reports what it reveals.
// A/AAAA records give host IP+name; PTR/SRV records reveal service types.
func handleMDNSPacket(pkt []byte, seenHosts map[string]bool, rep *Reporter) {
	var parser dnsmessage.Parser
	if _, err := parser.Start(pkt); err != nil {
		return
	}
	_ = parser.SkipAllQuestions()

	for {
		ah, err := parser.AnswerHeader()
		if err != nil {
			break // no more answers
		}
		switch ah.Type {
		case dnsmessage.TypeA:
			r, err := parser.AResource()
			if err != nil {
				break
			}
			ip := net.IP(r.A[:]).String()
			reportMDNSHost(ip, strings.TrimSuffix(ah.Name.String(), "."), seenHosts, rep)
		case dnsmessage.TypeAAAA:
			r, err := parser.AAAAResource()
			if err != nil {
				break
			}
			ip := net.IP(r.AAAA[:]).String()
			reportMDNSHost(ip, strings.TrimSuffix(ah.Name.String(), "."), seenHosts, rep)
		default:
			// PTR/SRV/TXT etc: skip the body but keep parsing. The A/AAAA
			// records are what give us concrete host IPs to report;
			// service-type enumeration without an IP isn't actionable as
			// a discovered *service* row, so we don't fabricate one.
			if err := parser.SkipAnswer(); err != nil {
				return
			}
		}
	}
}

func reportMDNSHost(ip, name string, seenHosts map[string]bool, rep *Reporter) {
	if ip == "" || seenHosts[ip] {
		return
	}
	seenHosts[ip] = true
	details := map[string]interface{}{}
	if name != "" {
		details["mdns_name"] = name
	}
	log.Printf("[Discovery/mDNS] Host announced itself: %s (%s)", ip, name)
	rep.Add(DiscoveredService{
		ServiceType:   "mdns_host",
		Host:          ip,
		DiscoveredVia: "mdns",
		Details:       details,
	})
}
