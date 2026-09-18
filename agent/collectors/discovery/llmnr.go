package discovery

import (
	"log"
	"net"
	"strings"
	"time"

	"golang.org/x/net/dns/dnsmessage"
)

// LLMNR multicast group and port (RFC 4795). Windows machines use LLMNR
// for link-local name resolution; they respond to queries for their own
// name. Listening here reveals Windows hosts on the segment that
// answer - again passive: hosts self-identify, we don't scan them.
const llmnrAddr = "224.0.0.252:5355"

// discoverViaLLMNR listens on the LLMNR multicast group for a short
// window and reports any host that answers with an A/AAAA record for
// its own name. Pure UDP multicast + DNS parsing - no raw sockets, no
// privileges. Like mDNS, if :5355 is already exclusively held we skip.
//
// Note: LLMNR responders answer QUERIES (they don't announce
// spontaneously the way mDNS does), so in a fully passive listen we
// mostly catch responses to OTHER machines' queries. That's still
// useful - it surfaces which hosts are LLMNR-active - and stays strictly
// passive. We do not blast name queries for a wordlist of hostnames
// (that would be scanning, and is exactly the kind of aggressive probing
// this design avoids).
func discoverViaLLMNR(rep *Reporter) {
	addr, err := net.ResolveUDPAddr("udp4", llmnrAddr)
	if err != nil {
		log.Printf("[Discovery/LLMNR] resolve error: %v", err)
		return
	}

	conn, err := net.ListenMulticastUDP("udp4", nil, addr)
	if err != nil {
		log.Printf("[Discovery/LLMNR] cannot listen on %s: %v", llmnrAddr, err)
		return
	}
	defer conn.Close()

	_ = conn.SetReadBuffer(65536)
	deadline := time.Now().Add(4 * time.Second)
	_ = conn.SetReadDeadline(deadline)

	seenHosts := map[string]bool{}
	buf := make([]byte, 65536)
	for time.Now().Before(deadline) {
		n, src, err := conn.ReadFromUDP(buf)
		if err != nil {
			break
		}
		handleLLMNRPacket(buf[:n], src, seenHosts, rep)
	}
}

func handleLLMNRPacket(pkt []byte, src *net.UDPAddr, seenHosts map[string]bool, rep *Reporter) {
	var parser dnsmessage.Parser
	if _, err := parser.Start(pkt); err != nil {
		return
	}
	_ = parser.SkipAllQuestions()

	for {
		ah, err := parser.AnswerHeader()
		if err != nil {
			break
		}
		var ip, name string
		name = strings.TrimSuffix(ah.Name.String(), ".")
		switch ah.Type {
		case dnsmessage.TypeA:
			r, err := parser.AResource()
			if err != nil {
				break
			}
			ip = net.IP(r.A[:]).String()
		case dnsmessage.TypeAAAA:
			r, err := parser.AAAAResource()
			if err != nil {
				break
			}
			ip = net.IP(r.AAAA[:]).String()
		default:
			if err := parser.SkipAnswer(); err != nil {
				return
			}
			continue
		}

		if ip == "" || seenHosts[ip] {
			continue
		}
		seenHosts[ip] = true
		details := map[string]interface{}{}
		if name != "" {
			details["llmnr_name"] = name
		}
		log.Printf("[Discovery/LLMNR] Windows host responded: %s (%s)", ip, name)
		rep.Add(DiscoveredService{
			ServiceType:   "windows_host",
			Host:          ip,
			DiscoveredVia: "llmnr",
			Details:       details,
		})
	}
}
