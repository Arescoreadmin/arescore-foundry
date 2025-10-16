# Frontend NGINX Spec (SPA)
- Listen: 8080
- Health: GET /health -> 200, body "ok\n", Content-Type text/plain
- Root: /usr/share/nginx/html; index index.html
- SPA fallback: try_files $uri $uri/ /index.html
- Prod hardening: sendfile on; gzip for text assets; caching for static files (not index.html)
- Only server{} block, no http{} or events{}.
