FROM node:18.20.3-alpine3.19@sha256:4862d3c79737924e572a487b39a9e327acb517364e5e324c0f15067375c41f23 AS build
WORKDIR /app
COPY package*.json ./
# no lockfile -> use npm install
RUN --mount=type=cache,target=/root/.npm npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.25.3-alpine@sha256:46371dae8e17a9d22931d0e80a6c08e47f3b28ed449e0853a4fbb42f2c33f768 AS runtime
WORKDIR /usr/share/nginx/html
COPY --from=build /app/dist .
COPY nginx.conf /etc/nginx/conf.d/default.conf
USER 101
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=3s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ || exit 1
