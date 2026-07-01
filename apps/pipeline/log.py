"""pipeline_log.py — centralized structured logging for all pipeline steps.

All pipeline steps (extract, adjudicate, verify, merge, apply, enrich) use this
module to record decisions, actions, failures, and timing in a consistent format.

Logs are written to data/logs/ as JSONL files (one per run), making them
easy to grep, tail, and analyze.

Usage:
    from apps.pipeline.pipeline_log import PipelineLogger

    log = PipelineLogger("extract", source="unitedgangs")
    log.info("Starting extraction", pages=42)
    log.decision("accept_edge", org="org:foo", target="org:bar", reason="2/3 agreement")
    log.action("write_file", path="data/orgs/foo.json", fields_changed=["description"])
    log.error("LLM timeout", attempt=3, model="claude-sonnet-4.5")
    log.close()  # writes summary
"""

import json
import os
import time
from datetime import datetime
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
        self.run_id = datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")

        # Create log file: data/logs/{step}_{source}_{timestamp}.jsonl
        safe_source = source.replace("/", "_").replace(":", "_") if source else "global"
        self.log_path = LOGS_DIR / f"{step}_{safe_source}_{self.run_id}.jsonl"
        self._file = self.log_path.open("w", encoding="utf-8")

        # Counters
        self.counts = {
            "info": 0,
            "decisions": 0,
            "actions": 0,
            "errors": 0,
            "warnings": 0,
        }

        # Write run header
        self._write({
            "type": "run_start",
            "step": step,
            "source": source,
            "timestamp": self._ts(),
            "metadata": metadata,
        })

    def _ts(self) -> str:
        return datetime.now(datetime.UTC).isoformat(timespec="seconds")

    def _elapsed(self) -> float:
        return round(time.time() - self.start_time, 2)

    def _write(self, entry: dict):
        self._file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._file.flush()

    def info(self, message: str, **data):
        """Log an informational message."""
        self.counts["info"] += 1
        self._write({
            "type": "info",
            "timestamp": self._ts(),
            "elapsed": self._elapsed(),
            "message": message,
            **data,
        })

    def decision(self, action: str, **data):
        """Log a decision (accept/reject/skip/merge)."""
        self.counts["decisions"] += 1
        self._write({
            "type": "decision",
            "timestamp": self._ts(),
            "elapsed": self._elapsed(),
            "action": action,
            **data,
        })

    def action(self, action: str, **data):
        """Log an action taken (file write, edge added/removed, field changed)."""
        self.counts["actions"] += 1
        self._write({
            "type": "action",
            "timestamp": self._ts(),
            "elapsed": self._elapsed(),
            "action": action,
            **data,
        })

    def warning(self, message: str, **data):
        """Log a warning."""
        self.counts["warnings"] += 1
        self._write({
            "type": "warning",
            "timestamp": self._ts(),
            "elapsed": self._elapsed(),
            "message": message,
            **data,
        })

    def error(self, message: str, **data):
        """Log an error."""
        self.counts["errors"] += 1
        self._write({
            "type": "error",
            "timestamp": self._ts(),
            "elapsed": self._elapsed(),
            "message": message,
            **data,
        })

    def tool_call(self, tool: str, input_data: dict, result_length: int):
        """Log a tool execution (web search, fetch URL)."""
        self._write({
            "type": "tool_call",
            "timestamp": self._ts(),
            "elapsed": self._elapsed(),
            "tool": tool,
            "input": input_data,
            "result_chars": result_length,
        })

    def close(self):
        """Write summary and close the log file."""
        self._write({
            "type": "run_end",
            "timestamp": self._ts(),
            "elapsed_total": self._elapsed(),
            "counts": self.counts,
        })
        self._file.close()
        # Print summary to stdout
        total = sum(self.counts.values())
        print(f"  📋 Log: {self.log_path.name} ({total} entries, {self._elapsed():.1f}s)")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
