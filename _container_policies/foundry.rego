package foundry

has_label(v) if {
  some i
  input.metadata.labels[i] == v
}

net_denied if {
  input.network.egress == "deny"
}

zero_exploits if {
  input.limits.attacker_max_exploits == 0
}
