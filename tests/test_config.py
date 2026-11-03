from __future__ import annotations
from dataclasses import replace
import pytest
from secquery.config import Settings


def test_load_settings_uses_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SECQUERY_DATA_DIR", str(tmp_path / "custom"))
    monkeypatch.setenv("SECQUERY_EMBEDDER_BACKEND", "offline")
    monkeypatch.setenv("SECQUERY_CHUNK_SIZE", "500")
    settings = Settings.load(env_file=None)
    assert settings.data_dir == tmp_path / "custom"
    assert settings.embedder_backend == "offline"
    assert settings.chunk_size == 500


def test_invalid_chunk_overlap_is_rejected(test_settings):
    invalid = replace(test_settings, chunk_overlap=test_settings.chunk_size)
    with pytest.raises(ValueError, match="chunk_overlap"):
        invalid.validate()
