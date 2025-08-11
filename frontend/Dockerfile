# syntax=docker/dockerfile:1.7-labs

########## Build stage ##########
FROM node:18-alpine AS builder
WORKDIR /app

# Install deps (prefer lockfile if present) with cached npm dir
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
  if [ -f package-lock.json ]; then \
    npm ci --no-audit --no-fund; \
  else \
    npm install --no-audit --no-fund; \
  fi

# Copy the app and build
COPY . .
# Pass any VITE_* at build time: --build-arg VITE_API_BASE=...
ARG VITE_API_BASE
ENV VITE_API_BASE=${VITE_API_BASE}
ENV CI=true
RUN --mount=type=cache,target=/root/.npm npm run build

########## Runtime stage (non-root nginx) ##########
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime

# nginx in this image listens on 8080
EXPOSE 8080

# Copy built assets; ensure nginx (uid 101) owns them
COPY --from=builder --chown=101:101 /app/dist/ /usr/share/nginx/html/

# Minimal optimized nginx config: caching + SPA fallback + basic headers
RUN cat >/etc/nginx/conf.d/default.conf <<'NGINX'
server {
  listen       8080 default_server;
  server_name  _;
  root         /usr/share/nginx/html;
  index        index.html;

  # Cache hashed assets aggressively
  location ~* \.(?:js|css|png|jpg|jpeg|gif|svg|ico|woff2?)$ {
    access_log  off;
    add_header  Cache-Control "public, max-age=31536000, immutable";
    try_files   $uri =404;
  }

  # SPA fallback (e.g., React/Vite router)
  location / {
    try_files $uri /index.html;
  }

  # Basic security headers for static files
  add_header X-Content-Type-Options nosniff always;
  add_header X-Frame-Options DENY always;
  add_header Referrer-Policy no-referrer-when-downgrade always;
}
NGINX

# Simple healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
