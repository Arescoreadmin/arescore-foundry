package policies_test

import data.foundry.consent
import data.foundry.authority
import data.foundry.runtime_revocation

test_consent_required_denies_without_token if {
  not consent.allow with input as {
    "tokens": { "consent": { "signature": "", "model_hash": "", "ttl_sec": 0 } }
  }
}

test_consent_allows_with_valid_token if {
  consent.allow with input as {
    "tokens": { "consent": { "signature": "abc", "model_hash": "h123", "ttl_sec": 120 } }
  }
}

test_crl_denies_revoked_cert if {
  not authority.allow with input as {
    "auth": { "issuer": "arescore-ca", "serial": "SER123" },
    "crl": { "serials": ["SER123"] }
  }
}

test_bad_model_hash_denied if {
  not runtime_revocation.allow with input as {
    "sig": "s1",
    "model": {"hash": "bad"},
    "allowed": {"hash": "good"},
    "revocation": {"runtime_ids": []},
    "runtime": {"id": "r-1"}
  }
}

test_empty_sig_denied if {
  not runtime_revocation.allow with input as {
    "sig": "",
    "model": {"hash": "good"},
    "allowed": {"hash": "good"},
    "revocation": {"runtime_ids": []},
    "runtime": {"id": "r-1"}
  }
}

test_runtime_allows_when_good if {
  runtime_revocation.allow with input as {
    "sig": "s1",
    "model": {"hash": "good"},
    "allowed": {"hash": "good"},
    "revocation": {"runtime_ids": []},
    "runtime": {"id": "r-1"}
  }
}

test_runtime_revocation_from_data_feed if {
  not runtime_revocation.allow with input as {
    "sig": "s1",
    "model": {"hash": "good"},
    "allowed": {"hash": "good"},
    "runtime": {"id": "r-9"}
  }
  with data.runtime_revocation_feed as {"runtime_ids": ["r-9"]}
}
