# syntax=docker/dockerfile:1

FROM golang:1.27-alpine AS build
WORKDIR /src

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/ascii-charts-mcp .

FROM scratch
COPY --from=build /out/ascii-charts-mcp /ascii-charts-mcp

# The server speaks MCP over stdio, so it must be run with `docker run -i`
# (an MCP client typically manages this for you via its own config).
ENTRYPOINT ["/ascii-charts-mcp"]
