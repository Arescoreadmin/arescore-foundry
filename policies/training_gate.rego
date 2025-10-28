package foundry.training

default allow := false

allow if {
  "class:netplus" in input.metadata.labels
  input.limits.attacker_max_exploits <= 0
  input.network.egress == "deny"
}

allow if {
  "class:ccna" in input.metadata.labels
  input.limits.attacker_max_exploits <= 0
  input.network.egress == "deny"
}

allow if {
  "class:cissp" in input.metadata.labels
  input.limits.attacker_max_exploits <= 5
  input.network.egress == "deny"
}
