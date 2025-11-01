package foundry.fl_ingress

default allow := false
default reason := "blocked by default"

allow if {
  input.request.path == "/federation/v1/ingress"
  input.request.method == "POST"
  input.auth.subject != ""
  input.headers["content-type"] == "application/octet-stream"
}

reason := "path/method/content-type not allowed for FL ingress" if not allow
