# Loki

Loki is a log indexer which can then be queried via Grafana

## Architecture

- distributors: logs pushed here where they handle push data and validation. distributes to ingestors
- ingestors: persist data and ship to long-term storage (i.e S3)
- query frontend, scheduler, queriers: organize and execute user queries across long-term storage and ingestors
- compactor: merges index files and 
- rulers:

- index: stores loki labels i.e `log_level` and `source`
- chunks: stores log entries which match indexes

## logql

## References

- https://www.youtube.com/watch?v=1uk8LtQqsZQ