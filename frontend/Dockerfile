# syntax=docker/dockerfile:1.7
FROM nginxinc/nginx-unprivileged:1.28-alpine

# OCI metadata (optional)
ARG VCS_REF=""
ARG BUILD_DATE=""
LABEL org.opencontainers.image.title="arescore-frontend" \
      org.opencontainers.image.description="Nginx reverse proxy + static frontend (non-root)" \
      org.opencontainers.image.source="https://github.com/Arescoreadmin/arescore-foundry" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"

# Use our hardened Nginx server config
# (assumes your config lives at frontend/nginx.conf in the repo)
COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf

# Healthcheck hits the lightweight /ready endpoint served by Nginx
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ready || exit 1

EXPOSE 8080
USER 101
# nginx-unprivileged already runs nginx in the foreground
