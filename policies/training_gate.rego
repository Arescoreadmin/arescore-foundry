package foundry.training_gate

default allow := false
default reason := "missing dataset/model/consent"

track_allowed if {
  input.track == "netplus"
}

track_allowed if {
  input.track == "ccna"
}

track_allowed if {
  input.track == "cissp"
}

allow if {
  track_allowed
  input.dataset.id != ""
  input.model.hash != ""
  input.tokens.consent.signature != ""
}

reason := "track not authorized" if {
  not track_allowed
}

reason := "dataset id empty" if {
  track_allowed
  input.dataset.id == ""
}

reason := "model hash empty" if {
  track_allowed
  input.dataset.id != ""
  input.model.hash == ""
}

reason := "consent signature missing" if {
  track_allowed
  input.dataset.id != ""
  input.model.hash != ""
  input.tokens.consent.signature == ""
}

decision := {"allow": allow, "reason": reason}
