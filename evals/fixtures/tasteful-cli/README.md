# Tasteful CLI

Tasteful CLI converts newline-delimited input into a small summary report.

## Quick start

```bash
pip install -e .
tasteful-cli --input examples/events.ndjson --output summary.json
pytest
```

## Design

- `tasteful_cli.domain` contains pure parsing and summarization functions.
- `tasteful_cli.io` owns file-system reads and writes.
- `tasteful_cli.__main__` is only the command-line adapter.

The boundary keeps the common path small: parse records, summarize by event type, write JSON.
