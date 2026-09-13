# syntax=docker/dockerfile:1

FROM golang:1.27-alpine AS build
WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/ascii-charts-mcp .

FROM scratch
COPY --from=build /out/ascii-charts-mcp /ascii-charts-mcp

# By default the server speaks MCP over stdio, so it must be run with
# `docker run -i` (an MCP client typically manages this for you via its own
# config). Setting PORT switches it to a long-running HTTP server instead,
# serving MCP at /mcp and a plain health check at /healthz — see
# docker-compose.yml's "web" service and docs/development.md.
EXPOSE 8080
ENTRYPOINT ["/ascii-charts-mcp"]
