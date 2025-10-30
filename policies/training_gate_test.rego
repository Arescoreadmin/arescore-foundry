package foundry.training

import future.keywords.if

test_allow_true {
  allow with input as {
    "metadata": {"labels": ["class:netplus"]},
    "limits": {"attacker_max_exploits": 0},
    "network": {"egress": "deny"}
  }
}

test_allow_false_missing_label {
  not allow with input as {
    "metadata": {"labels": ["foo"]},
    "limits": {"attacker_max_exploits": 0},
    "network": {"egress": "deny"}
  }
}
