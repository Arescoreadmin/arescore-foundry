package foundry.runtime_revocation

default allow := false
default reason := "revoked or mismatched model"

signature := object.get(input, "sig", "")

model_hash := object.get(
  object.get(input, "model", {}),
  "hash",
  ""
)

allowed_hash := object.get(
  object.get(input, "allowed", {}),
  "hash",
  ""
)

runtime_id := object.get(
  object.get(input, "runtime", {}),
  "id",
  ""
)

revocation_sources := [
  object.get(object.get(input, "revocation", {}), "runtime_ids", []),
  object.get(object.get(input, "revocation_service", {}), "runtime_ids", []),
]

revoked_runtime if {
  runtime_id != ""
  some ids
  ids := revocation_sources[_]
  runtime_id == ids[_]
}

allow if {
  signature != ""
  model_hash != ""
  allowed_hash != ""
  runtime_id != ""
  model_hash == allowed_hash
  not revoked_runtime
}

reason := "empty signature" if signature == ""

reason := "missing model hash" if {
  signature != ""
  model_hash == ""
}

reason := "missing allowed hash" if {
  signature != ""
  model_hash != ""
  allowed_hash == ""
}

reason := sprintf("bad model hash: got %v expected %v", [model_hash, allowed_hash]) if {
  signature != ""
  model_hash != ""
  allowed_hash != ""
  model_hash != allowed_hash
}

reason := "missing runtime id" if {
  signature != ""
  model_hash != ""
  allowed_hash != ""
  runtime_id == ""
}

reason := "runtime id revoked" if revoked_runtime
