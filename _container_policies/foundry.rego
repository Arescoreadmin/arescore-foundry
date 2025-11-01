package foundry

has_label(v) {
  some i
  input.metadata.labels[i] == v
}

net_denied {
  input.network.egress == "deny"
}

zero_exploits {
  input.limits.attacker_max_exploits == 0
}
