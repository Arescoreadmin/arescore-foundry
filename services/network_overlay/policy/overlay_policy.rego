package overlay.policy

default allow := false

mtu_requirements := {
  "vxlan": 1550,
  "geneve": 1550,
  "double_encap": 1600,
}

allowed_ports := {
  "vxlan": [4789],
  "geneve": [6081],
  "flannel": [8472],
  "wireguard": [51820],
  "ipsec": [500, 4500],
}

fanout_caps := {
  "gre": 16,
  "l2tpv3": 8,
}

allow {
  spec := input.spec
  valid_mtu(spec)
  required_ports(spec)
  fanout_ok(spec)
  evpn_unique(spec)
}

valid_mtu(spec) {
  required := mtu_requirements[spec.type]
  spec.mtu >= required
}

valid_mtu(spec) {
  not mtu_requirements[spec.type]
  spec.mtu >= 1500
}

required_ports(spec) {
  ports := allowed_ports[spec.type]
  not missing_port(spec, ports)
}

required_ports(spec) {
  not allowed_ports[spec.type]
}

missing_port(spec, ports) {
  port := ports[_]
  not contains(spec.ports, port)
}

contains(arr, value) {
  arr[_] == value
}

fanout_ok(spec) {
  cap := fanout_caps[spec.type]
  spec.fanout <= cap
}

fanout_ok(spec) {
  not fanout_caps[spec.type]
}

evpn_unique(spec) {
  reg := input.assigned_rt_rd
  not reg[spec.tenant]
}


evpn_unique(spec) {
  not input.assigned_rt_rd
}

violation[reason] {
  not allow
  reason := "overlay specification failed policy checks"
}
