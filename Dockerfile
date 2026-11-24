FROM node:22-slim AS ui
WORKDIR /ui
RUN npm i -g pnpm@12.21.0
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY ui ./
RUN pnpm build

FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY core ./core
RUN pip install --no-cache-dir .
COPY config ./config
COPY packs ./packs
COPY --from=ui /ui/dist ./ui/dist
RUN useradd -m app && mkdir -p /app/data && chown app /app/data
USER app
EXPOSE 8000
CMD ["uvicorn", "agent_platform.api:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
