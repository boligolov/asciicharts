// Package store persists anonymous usage statistics and free-text feedback
// to Postgres. It never sees or stores the actual data a caller charts
// (values, labels, titles) — only the shape of the request (chart type,
// style, size buckets, success/failure).
package store

import (
	"context"
	"fmt"
	"log"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Store records events to Postgres. A nil *Store is valid and every method
// on it is a safe no-op: stats and feedback are strictly best-effort and
// optional, and the server must behave identically whether or not a
// database is configured.
type Store struct {
	pool    *pgxpool.Pool
	version string
}

// Open connects to Postgres using dsn (typically the DATABASE_URL
// environment variable) and ensures the schema exists. If dsn is empty,
// Open returns (nil, nil) — a nil *Store — so callers can treat "no stats
// configured" and "stats configured" uniformly via the no-op methods below,
// without a separate enabled/disabled branch at every call site.
func Open(ctx context.Context, dsn, version string) (*Store, error) {
	if dsn == "" {
		return nil, nil
	}

	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, fmt.Errorf("connect to postgres: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping postgres: %w", err)
	}

	s := &Store{pool: pool, version: version}
	if err := s.migrate(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("migrate schema: %w", err)
	}
	return s, nil
}

// Close releases the connection pool. Safe to call on a nil *Store.
func (s *Store) Close() {
	if s != nil && s.pool != nil {
		s.pool.Close()
	}
}

const schema = `
CREATE TABLE IF NOT EXISTS chart_events (
	id                 BIGSERIAL PRIMARY KEY,
	created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
	chart_type         TEXT NOT NULL,
	style              TEXT NOT NULL DEFAULT '',
	mode               TEXT NOT NULL DEFAULT '',
	border             TEXT NOT NULL DEFAULT '',
	use_color          BOOLEAN NOT NULL DEFAULT false,
	series_count       INT NOT NULL DEFAULT 0,
	point_count_bucket TEXT NOT NULL DEFAULT '',
	output_size_bucket TEXT NOT NULL DEFAULT '',
	success            BOOLEAN NOT NULL,
	error_message      TEXT NOT NULL DEFAULT '',
	server_version     TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS feedback (
	id             BIGSERIAL PRIMARY KEY,
	created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
	message        TEXT NOT NULL,
	server_version TEXT NOT NULL DEFAULT ''
);
`

func (s *Store) migrate(ctx context.Context) error {
	_, err := s.pool.Exec(ctx, schema)
	return err
}

// ChartEvent is the anonymous shape of one render_chart call — never the
// caller's actual data.
type ChartEvent struct {
	ChartType        string
	Style            string
	Mode             string
	Border           string
	UseColor         bool
	SeriesCount      int
	PointCountBucket string
	OutputSizeBucket string
	Success          bool
	ErrorMessage     string
}

// RecordChartEvent is best-effort: on a nil Store, or if the insert fails,
// it logs (if there's something to log) and returns — stats must never
// affect the caller's render_chart result.
func (s *Store) RecordChartEvent(ctx context.Context, e ChartEvent) {
	if s == nil {
		return
	}
	_, err := s.pool.Exec(ctx, `
		INSERT INTO chart_events
			(chart_type, style, mode, border, use_color, series_count, point_count_bucket, output_size_bucket, success, error_message, server_version)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
		e.ChartType, e.Style, e.Mode, e.Border, e.UseColor, e.SeriesCount, e.PointCountBucket, e.OutputSizeBucket, e.Success, e.ErrorMessage, s.version)
	if err != nil {
		log.Printf("store: record chart event: %v", err)
	}
}

// RecordFeedback is best-effort, like RecordChartEvent.
func (s *Store) RecordFeedback(ctx context.Context, message string) {
	if s == nil {
		return
	}
	_, err := s.pool.Exec(ctx, `INSERT INTO feedback (message, server_version) VALUES ($1, $2)`, message, s.version)
	if err != nil {
		log.Printf("store: record feedback: %v", err)
	}
}
