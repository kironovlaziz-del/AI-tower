package discovery

import (
	"errors"
	"net"
)

// ifaceInfo holds everything the raw-socket methods need about the
// primary network interface.
type ifaceInfo struct {
	iface *net.Interface
	ip    net.IP     // our IPv4 on this interface
	ipNet *net.IPNet // the subnet (for enumerating neighbors)
	mac   net.HardwareAddr
}

// primaryInterface picks the interface that carries the default route's
// network: the first up, non-loopback interface that has a private IPv4
// address. This is the interface an ARP scan or DHCP sniff should use.
func primaryInterface() (*ifaceInfo, error) {
	ifaces, err := net.Interfaces()
	if err != nil {
		return nil, err
	}
	for _, iface := range ifaces {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
			continue
		}
		if len(iface.HardwareAddr) == 0 {
			continue // no MAC (e.g. tunnels) - can't build ARP frames
		}
		addrs, err := iface.Addrs()
		if err != nil {
			continue
		}
		for _, addr := range addrs {
			ipNet, ok := addr.(*net.IPNet)
			if !ok {
				continue
			}
			ip4 := ipNet.IP.To4()
			if ip4 == nil {
				continue // IPv4 only for ARP
			}
			if !ip4.IsGlobalUnicast() {
				continue
			}
			ifCopy := iface
			return &ifaceInfo{
				iface: &ifCopy,
				ip:    ip4,
				ipNet: &net.IPNet{IP: ip4.Mask(ipNet.Mask), Mask: ipNet.Mask},
				mac:   iface.HardwareAddr,
			}, nil
		}
	}
	return nil, errors.New("no suitable IPv4 interface found")
}

// enumerateHosts returns every usable host IPv4 in the subnet, excluding
// the network and broadcast addresses and our own IP. Refuses to
// enumerate anything larger than a /16 (65k hosts) - beyond that an ARP
// sweep is both slow and inconsiderate, and almost certainly means we
// picked up an unexpectedly broad mask; the sniffer-on-span-port
// deployment is the right tool for very large segments, not a host scan.
func enumerateHosts(info *ifaceInfo) []net.IP {
	ones, bits := info.ipNet.Mask.Size()
	if bits-ones > 16 {
		return nil
	}
	var hosts []net.IP
	ip := info.ipNet.IP.Mask(info.ipNet.Mask)
	// broadcast = network | ^mask
	broadcast := make(net.IP, len(ip))
	for i := range ip {
		broadcast[i] = ip[i] | ^info.ipNet.Mask[i]
	}
	for cur := cloneIP(ip); info.ipNet.Contains(cur); cur = nextIP(cur) {
		if cur.Equal(info.ipNet.IP) || cur.Equal(broadcast) || cur.Equal(info.ip) {
			continue
		}
		hosts = append(hosts, cloneIP(cur))
	}
	return hosts
}

func cloneIP(ip net.IP) net.IP {
	c := make(net.IP, len(ip))
	copy(c, ip)
	return c
}

func nextIP(ip net.IP) net.IP {
	c := cloneIP(ip)
	for i := len(c) - 1; i >= 0; i-- {
		c[i]++
		if c[i] != 0 {
			break
		}
	}
	return c
}
