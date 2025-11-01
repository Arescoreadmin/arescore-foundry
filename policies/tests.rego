package policies.tests

import data.foundry.training.allow

test_netplus_egress_denied_allows {
  input := {
    "metadata": {"labels": ["class:netplus"]},
    "limits": {"attacker_max_exploits": 0},
    "network": {"egress": "deny"}
  }
  allow with input as input
}
