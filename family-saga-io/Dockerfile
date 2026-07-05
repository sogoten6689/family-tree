# ── Stage 1: build ──────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_BACKEND_URL=
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

COPY package.json bun.lockb* package-lock.json* yarn.lock* ./
RUN npm install --frozen-lockfile 2>/dev/null || npm install

COPY . .
RUN npm run build

# ── Stage 2: serve ──────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA + proxy API tới backend trong docker network
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
\n\
    location ~ ^/(api|docs|redoc|openapi\\.json|health) {\n\
        proxy_pass         http://backend:8000;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header   Host              $host;\n\
        proxy_set_header   X-Real-IP         $remote_addr;\n\
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;\n\
        proxy_set_header   X-Forwarded-Proto $scheme;\n\
        proxy_read_timeout 120s;\n\
    }\n\
\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
