"""log.py — centralized structured JSONL logging for all pipeline steps.

All pipeline steps (extract, adjudicate, verify, merge, apply, enrich) use this
module to record decisions, actions, failures, and timing in a consistent format.

Logs are written to data/logs/ as JSONL files (one per run), making them
easy to grep, tail, and analyze with jq/DuckDB.

Schema (every line has these base fields):
    {
        "ts": "2026-07-01T17:30:00Z",      # ISO 8601 timestamp
        "elapsed": 1.23,                     # seconds since run start
        "level": "info",                     # debug|info|warn|error
        "event": "edge_rejected",            # past-tense event name
        "run_id": "20260701_173000",         # unique run identifier
        "step": "verify",                    # pipeline step
        "source": "unitedgangs",             # source being processed
        ...additional context fields
    }

Usage:
    from apps.pipeline.log import PipelineLogger

    with PipelineLogger("extract", source="unitedgangs") as log:
        log.info("extraction_started", pages=42)
        log.decision("edge_accepted", org="org:foo", target="org:bar", reason="2/3 agreement")
        log.action("file_written", path="data/orgs/foo.json", fields_changed=["description"])
        log.error("llm_timeout", attempt=3, model="claude-sonnet-4.5")
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = ROOT / "data" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class PipelineLogger:
    """Structured JSONL logger for pipeline operations."""

    def __init__(self, step: str, source: str = "", **metadata):
        """Initialize a logger for a pipeline run.

        Args:
            step: Pipeline step name (extract, adjudicate, verify, merge, apply, enrich)
            source: Source being processed (e.g. 'unitedgangs', or org ID for enrich)
            **metadata: Additional metadata for the run header
        """
        self.step = step
        self.source = source
        self.start_time = time.time()
        self.run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # Create log file: data/logs/{step}_{source}_{timestamp}.jsonl
        safe_source = source.replace("/", "_").replace(":", "_") if source else "global"
        self.log_path = LOGS_DIR / f"{step}_{safe_source}_{self.run_id}.jsonl"
        self._file = self.log_path.open("w", encoding="utf-8")

        # Counters
        self.counts = {
            "info": 0,
            "warn": 0,
            "error": 0,
            "decisions": 0,
            "actions": 0,
        }

        # Write run header
        self._write("info", "run_started", **metadata)

    def _ts(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _elapsed(self) -> float:
        return round(time.time() - self.start_time, 2)

    def _write(self, level: str, event: str, **data):
        entry = {
            "ts": self._ts(),
            "elapsed": self._elapsed(),
            "level": level,
            "event": event,
            "run_id": self.run_id,
            "step": self.step,
            "source": self.source,
        }
        # Add context fields (filter out None values)
        entry.update({k: v for k, v in data.items() if v is not None})
        self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._file.flush()

    # --- Severity-based methods ---

    def debug(self, event: str, **data):
        """Low-level diagnostic info (off in production by default)."""
        self._write("debug", event, **data)

    def info(self, event: str, **data):
        """Normal business events / milestones."""
        self.counts["info"] += 1
        self._write("info", event, **data)

    def warn(self, event: str, **data):
        """Unexpected but handled situation."""
        self.counts["warn"] += 1
        self._write("warn", event, **data)

    def error(self, event: str, **data):
        """Failed operation requiring attention."""
        self.counts["error"] += 1
        self._write("error", event, **data)

    # --- Semantic methods (map to info level with structured data) ---

    def decision(self, event: str, **data):
        """Log a pipeline decision (accept/reject/skip/merge)."""
        self.counts["decisions"] += 1
        self._write("info", event, **data)

    def action(self, event: str, **data):
        """Log an action taken (file write, edge added/removed, field changed)."""
        self.counts["actions"] += 1
        self._write("info", event, **data)

    def tool_call(self, tool: str, input_data: dict, result_length: int):
        """Log a tool execution (web search, fetch URL)."""
        self._write("debug", "tool_executed", tool=tool, input=input_data, result_chars=result_length)

    # --- Lifecycle ---

    def close(self):
        """Write summary and close the log file."""
        self._write("info", "run_completed", counts=self.counts)
        self._file.close()
        # Print summary to stdout
        total = sum(self.counts.values())
        print(f"  📋 Log: {self.log_path.name} ({total} entries, {self._elapsed():.1f}s)")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
