package voice.policy

default allow := false

allow {
  input.spec.dscp == 46
  input.metrics.jitter_ms < 30
  input.metrics.loss_pct < 1
}

violation[msg] {
  not allow
  msg := "voice specification failed QoS policy"
}
