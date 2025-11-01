package foundry.runtime_revocation

default allow := false
default reason := "revoked or mismatched model"

revoked_runtime if {
  input.runtime.id in input.revocation.runtime_ids
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
