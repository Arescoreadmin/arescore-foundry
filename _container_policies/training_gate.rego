package foundry.training

default allow := false

allow if {
  data.foundry.has_label("class:netplus")
  data.foundry.zero_exploits
  data.foundry.net_denied
}
