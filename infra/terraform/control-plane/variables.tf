variable "kubeconfig" {
  description = "Path to the kubeconfig file used to talk to the cluster."
  type        = string
  default     = "~/.kube/config"
}

variable "context" {
  description = "Optional kubectl context override."
  type        = string
  default     = ""
}

variable "namespace" {
  description = "Namespace dedicated to the Foundry control-plane."
  type        = string
  default     = "foundry-control"
}

variable "opa_bundle_url" {
  description = "Remote bundle URL consumed by the control-plane OPA sidecars."
  type        = string
  default     = ""
}

variable "nats_url" {
  description = "NATS endpoint that the control-plane advertises to range-plane tenants."
  type        = string
  default     = "nats://nats.default.svc:4222"
}
