package foundry.runtime_revocation

default allow := false
default reason := "revoked or mismatched model"

revocation_ids := object.get(
  object.get(input, "revocation", {}),
  "runtime_ids",
  []
)

runtime_id := object.get(
  object.get(input, "runtime", {}),
  "id",
  ""
)

revoked_runtime if {
  runtime_id != ""
  runtime_id in revocation_ids
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

decision := {"allow": allow, "reason": reason}
