# syntax=docker/dockerfile:1
#
# The asciicharts MCP server (go/cmd/asciicharts-mcp): one static binary on an empty image.
# Build from the repository root (the build context is the whole repo):
#   docker build -f deploy/Dockerfile -t asciicharts .
FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go/go.mod go/go.sum ./
RUN go mod download
COPY go/ ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /asciicharts-mcp ./cmd/asciicharts-mcp

FROM scratch
COPY --from=build /asciicharts-mcp /asciicharts-mcp
USER 65534:65534

# By default the server speaks MCP over stdio, so it must be run with `docker run -i` (an MCP client
# typically manages this via its own config). Setting PORT switches it to a long-running HTTP server
# instead, serving MCP at /mcp and a plain health check at /healthz — see docker-compose.yml.
EXPOSE 8080
ENTRYPOINT ["/asciicharts-mcp"]
