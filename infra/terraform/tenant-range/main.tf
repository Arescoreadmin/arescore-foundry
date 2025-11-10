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

resource "kubernetes_namespace" "tenant" {
  for_each = var.tenants

  metadata {
    name = "tenant-${each.key}"
    labels = {
      "foundry.arescore.dev/plane"   = "range"
      "foundry.arescore.dev/tenant"  = each.key
      "foundry.arescore.dev/control" = var.control_plane_namespace
    }
    annotations = {
      "foundry.arescore.dev/display-name" = each.value.display_name
    }
  }
}

resource "kubernetes_resource_quota" "tenant" {
  for_each = var.tenants

  metadata {
    name      = "tenant-${each.key}-quota"
    namespace = kubernetes_namespace.tenant[each.key].metadata[0].name
  }

  spec {
    hard = {
      "requests.cpu"    = each.value.quota_cpu
      "requests.memory" = each.value.quota_memory
    }
  }
}

output "tenants" {
  description = "Computed metadata for each tenant namespace."
  value = {
    for k, ns in kubernetes_namespace.tenant : k => ns.metadata[0].name
  }
}
