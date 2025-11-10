terraform {
  required_version = ">= 1.5.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig
  config_context = var.context != "" ? var.context : null
}

resource "kubernetes_namespace" "control_plane" {
  metadata {
    name = var.namespace
    labels = {
      "foundry.arescore.dev/plane" = "control"
      "foundry.arescore.dev/version" = "v1"
    }
    annotations = {
      "foundry.arescore.dev/opa-bundle" = var.opa_bundle_url
      "foundry.arescore.dev/nats-url"   = var.nats_url
    }
  }
}

resource "kubernetes_config_map" "plane_settings" {
  metadata {
    name      = "foundry-plane-settings"
    namespace = kubernetes_namespace.control_plane.metadata[0].name
  }

  data = {
    "plane"      = "control"
    "nats_url"   = var.nats_url
    "opa_bundle" = var.opa_bundle_url
  }
}

output "namespace" {
  description = "Name of the namespace created for the control-plane."
  value       = kubernetes_namespace.control_plane.metadata[0].name
}
