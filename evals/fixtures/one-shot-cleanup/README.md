# One-Shot Cleanup

This fixture represents a small incident handoff script. The goal is to turn a rough export into readable Markdown that a responder can paste into an incident note.

The project optimizes for readability and dev-speed:

- Keep the workflow local and single-file.
- Make the input/output shape obvious.
- Prefer copyable examples and behavior tests over framework adoption.
- Do not add services, queues, databases, or scalability layers unless the script stops being a one-shot handoff tool.

## Quick start

```bash
python cleanup_export.py examples/raw-export.txt > handoff.md
pytest
```
