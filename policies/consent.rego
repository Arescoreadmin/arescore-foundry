package foundry.consent

default allow := false
default reason := "consent missing"

allow if {
  tok := input.tokens.consent
  tok.signature != ""
  tok.model_hash != ""
  tok.ttl_sec > 0
}

reason := "consent token invalid: empty signature or expired TTL" if not allow

decision := {"allow": allow, "reason": reason}
