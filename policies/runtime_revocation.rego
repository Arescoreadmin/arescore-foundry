package foundry.runtime_revocation

default allow := false
default reason := "revoked or mismatched model"

input_revocation_ids := ids {
  revocation := object.get(input, "revocation", {})
  ids := object.get(revocation, "runtime_ids", [])
}

data_revocation_ids := ids {
  feed := object.get(data, "runtime_revocation_feed", {})
  ids := object.get(feed, "runtime_ids", [])
}

default revocation_ids := input_revocation_ids

revocation_ids := data_revocation_ids if {
  count(input_revocation_ids) == 0
  count(data_revocation_ids) > 0
}

revoked_runtime if {
  input.runtime.id in revocation_ids
}

allow if {
  input.sig != ""
  input.model.hash == input.allowed.hash
  not revoked_runtime
}

reason := "empty signature" if input.sig == ""

reason := sprintf("bad model hash: got %v expected %v", [input.model.hash, input.allowed.hash]) if {
  input.sig != ""
  input.model.hash != input.allowed.hash
}

reason := "runtime id revoked" if revoked_runtime
