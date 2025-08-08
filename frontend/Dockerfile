# syntax=docker/dockerfile:1.6

########## build stage ##########
FROM node:18-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm i --no-audit --no-fund; fi

COPY . .
# Vite reads this at build-time
ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}

RUN npm run build


########## runtime (nginx) ##########
FROM nginxinc/nginx-unprivileged:stable-alpine
WORKDIR /usr/share/nginx/html

# ship the built app
COPY --from=build /app/dist ./

# optional fallback config (safe to keep if you have frontend/nginx.conf)
# If you DON’T have this file, delete the next line.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
  CMD wget -qO- http://localhost:8080/health || exit 1
