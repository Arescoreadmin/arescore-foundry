package foundry.training


gate_ok {
  labels := input.metadata.labels
  labels[_] == "class:netplus"
  input.limits.attacker_max_exploits == 0
  input.network.egress == "deny"
}
