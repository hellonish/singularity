from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from api import logging_config
from api.config import Settings, settings


def test_steps_mode_omits_inputs_outputs_and_details(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "log_mode", "steps")
    step_log = logging_config.StepLogger("chat", user_id="user-1", chat_id="chat-1")

    with caplog.at_level(logging.INFO, logger="singularity.steps.chat"):
        step_log.step("message_received", inputs={"content": "private prompt"})
        step_log.detail("generation_delta", outputs={"delta": "private reply"})
        step_log.error("generation", RuntimeError("private provider response"))

    assert "step=message_received" in caplog.text
    assert "user_id=\"user-1\"" in caplog.text
    assert "private prompt" not in caplog.text
    assert "private reply" not in caplog.text
    assert "private provider response" not in caplog.text
    assert "generation_delta" not in caplog.text
    assert "error_type=RuntimeError" in caplog.text


def test_full_mode_records_complete_inputs_outputs_and_details(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "log_mode", "full")
    step_log = logging_config.StepLogger("chat", message_id="message-1")

    with caplog.at_level(logging.INFO, logger="singularity.steps.chat"):
        step_log.step("message_received", inputs={"content": "line one\nline two"})
        step_log.detail("generation_delta", outputs={"delta": "complete reply"})

    assert 'inputs={"content":"line one\\nline two"}' in caplog.text
    assert 'outputs={"delta":"complete reply"}' in caplog.text


def test_configure_logging_writes_to_rotating_file(monkeypatch, tmp_path) -> None:
    log_path = tmp_path / "nested" / "singularity.log"
    root = logging.getLogger()
    original_handlers = list(root.handlers)

    monkeypatch.setattr(logging_config, "_configured", False)
    monkeypatch.setattr(settings, "log_file", str(log_path))
    monkeypatch.setattr(settings, "log_mode", "steps")
    monkeypatch.setattr(settings, "log_level", "INFO")
    logging_config.configure_logging()
    logging.getLogger("singularity.steps.test").info("file-handler-check")

    added_handlers = [handler for handler in root.handlers if handler not in original_handlers]
    for handler in added_handlers:
        handler.flush()
    assert "file-handler-check" in log_path.read_text(encoding="utf-8")

    for handler in added_handlers:
        root.removeHandler(handler)
        handler.close()


def test_log_mode_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, LOG_MODE="payloads-only")
