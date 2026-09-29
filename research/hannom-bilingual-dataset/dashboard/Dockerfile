FROM python:3.12-alpine AS build
WORKDIR /app
RUN pip install --no-cache-dir rapidfuzz
COPY scripts/build_dashboard.py scripts/build_dashboard.py
COPY scripts/_repo_paths.py scripts/_repo_paths.py
COPY data/ data/
RUN python3 scripts/build_dashboard.py

FROM nginx:alpine
COPY --from=build /app/dashboard/index.html /usr/share/nginx/html/index.html
COPY --from=build /app/dashboard/status.json /usr/share/nginx/html/status.json
COPY --from=build /app/dashboard/data/ /usr/share/nginx/html/data/
