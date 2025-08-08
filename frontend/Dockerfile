# syntax=docker/dockerfile:1.6

# --- Build stage ---
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
# Use lockfile if present; otherwise fall back to npm install
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
COPY . .
ARG VITE_API_BASE
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

# --- Runtime (unprivileged nginx) ---
FROM nginxinc/nginx-unprivileged:stable-alpine
WORKDIR /usr/share/nginx/html
COPY --from=build /app/dist ./
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD wget -qO- http://localhost:8080/health || exit 1
