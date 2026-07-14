"""Central logging configuration and a structured step logger.

Two concerns live here:

1. ``configure_logging`` installs a rotating file handler (and keeps the console
   handler) so operators can follow what happens over time. It is called once at
   application startup from the FastAPI lifespan.

2. ``StepLogger`` is the vocabulary the chat and research flows use to record
   step-by-step progress. It honours ``settings.log_mode``:

   - ``"full"``  logs each step plus its ``inputs`` / ``outputs`` payloads.
   - ``"steps"`` logs only the step boundary (name, phase, and context ids),
     never the payloads. Use this when the log file is shared with people who
     should not see user content.

The step logger emits normal ``logging`` records on the ``singularity.steps``
logger, so everything already routed to the file (and console) picks them up —
there is no second logging path to configure.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any

from api.config import settings

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

_configured = False


def configure_logging() -> None:
    """Idempotently configure the root logger with console + optional file output.

    Safe to call more than once (tests, reload); handlers are only attached on
    the first call. The console handler is always present so container stdout
    keeps working; the file handler is added only when ``log_file`` is set.
    """
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Keep a single console handler (stdout) so Docker/`docker logs` still works.
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

    if settings.log_file:
        path = Path(settings.log_file).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            path,
            maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    _configured = True
    logging.getLogger("singularity.steps").info(
        "logging configured mode=%s level=%s file=%s",
        settings.log_mode,
        settings.log_level,
        settings.log_file or "-",
    )


def _render(value: Any) -> str:
    """Render a payload as single-line JSON without dropping content."""
    try:
        return json.dumps(value, default=str, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError):
        return json.dumps(repr(value), ensure_ascii=False)


class StepLogger:
    """Records step-by-step progress for one flow (a chat turn or research run).

    Bind the stable context once (user id, and the chat or run id) and every
    emitted record carries it, so a single ``grep`` follows one user's activity
    end to end. ``full`` mode appends inputs/outputs; ``steps`` mode omits them.
    """

    def __init__(self, flow: str, **context: Any) -> None:
        self._logger = logging.getLogger(f"singularity.steps.{flow}")
        self._flow = flow
        # Only keep context values that were actually provided.
        self._context = {k: v for k, v in context.items() if v is not None}
        self._full = settings.log_mode == "full"

    def _prefix(self) -> str:
        parts = [f"flow={self._flow}"] + [f"{k}={_render(v)}" for k, v in self._context.items()]
        return " ".join(parts)

    def step(
        self,
        name: str,
        *,
        phase: str = "run",
        inputs: Any = None,
        outputs: Any = None,
        level: int = logging.INFO,
        **extra: Any,
    ) -> None:
        """Emit one step record.

        ``phase`` is a free label such as ``start``/``end``/``error``. ``inputs``
        and ``outputs`` are only rendered in ``full`` mode. ``extra`` fields are
        always rendered (keep them small: ids, counts, model names).
        """
        fields = [self._prefix(), f"step={name}", f"phase={phase}"]
        fields += [f"{k}={_render(v)}" for k, v in extra.items() if v is not None]
        if self._full:
            if inputs is not None:
                fields.append(f"inputs={_render(inputs)}")
            if outputs is not None:
                fields.append(f"outputs={_render(outputs)}")
        self._logger.log(level, " ".join(fields))

    def detail(self, name: str, *, inputs: Any = None, outputs: Any = None, **extra: Any) -> None:
        """Emit high-volume payload detail in ``full`` mode only."""
        if self._full:
            self.step(name, phase="detail", inputs=inputs, outputs=outputs, **extra)

    def error(self, name: str, exc: BaseException, **extra: Any) -> None:
        """Record a failed step, including exception detail only in full mode."""
        fields = [
            self._prefix(),
            f"step={name}",
            "phase=error",
            f"error_type={type(exc).__name__}",
        ]
        if self._full:
            fields.append(f"error={_render(str(exc))}")
        fields += [f"{k}={_render(v)}" for k, v in extra.items() if v is not None]
        self._logger.error(" ".join(fields), exc_info=self._full)
