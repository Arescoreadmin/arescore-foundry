package training_gate_test

import data.foundry.training_gate

test_training_gate_allows if {
  training_gate.allow with input as {
    "track": "netplus",
    "dataset": {"id": "ds1"},
    "model": {"hash": "h1"},
    "tokens": {"consent": {"signature": "s"}}
  }
}

test_training_gate_denies_if_missing_fields if {
  not training_gate.allow with input as {
    "track": "netplus",
    "dataset": {"id": ""},
    "model": {"hash": ""},
    "tokens": {"consent": {"signature": ""}}
  }
}

test_training_gate_denies_for_bad_track if {
  not training_gate.allow with input as {
    "track": "unknown",
    "dataset": {"id": "ds1"},
    "model": {"hash": "h1"},
    "tokens": {"consent": {"signature": "s"}}
  }
}
