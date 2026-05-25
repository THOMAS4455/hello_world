from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.constants import _DEFAULT_ORIGINS, _load_allowed_origins  # noqa: E402


def test_load_allowed_origins_from_json(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    assert _load_allowed_origins() == ["https://app.example.com"]


def test_load_allowed_origins_from_csv(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com, https://b.example.com")
    assert _load_allowed_origins() == ["https://a.example.com", "https://b.example.com"]


def test_load_allowed_origins_default_when_empty(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert _load_allowed_origins() == list(_DEFAULT_ORIGINS)
