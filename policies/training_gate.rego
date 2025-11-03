package foundry.training_gate

default allow := false

allow if {
  input.dataset.id != ""
  input.model.hash != ""
  input.tokens.consent.signature != ""
}
