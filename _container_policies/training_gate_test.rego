package foundry.training

test_allow_true if {
  data.foundry.training.allow with input as {
    "metadata": {"labels": ["class:netplus"]},
    "limits":   {"attacker_max_exploits": 0},
    "network":  {"egress": "deny"}
  }
}

test_allow_false_missing_label if {
  not data.foundry.training.allow with input as {
    "metadata": {"labels": []},
    "limits":   {"attacker_max_exploits": 0},
    "network":  {"egress": "deny"}
  }
}
