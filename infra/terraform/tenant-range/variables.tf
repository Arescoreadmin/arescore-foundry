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

variable "tenants" {
  description = "Tenant descriptors keyed by tenant slug."
  type = map(object({
    display_name = string
    quota_cpu    = string
    quota_memory = string
  }))
  default = {
    demo = {
      display_name = "Demo Range"
      quota_cpu    = "2"
      quota_memory = "4Gi"
    }
  }
}

variable "control_plane_namespace" {
  description = "Namespace of the control-plane used to annotate tenant ranges."
  type        = string
  default     = "foundry-control"
}
