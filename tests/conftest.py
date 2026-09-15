import importlib
import sys

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    """FastAPI TestClient tegen een lege, tijdelijke SQLite-database.

    Raakt nooit de echte leads.db: database.SQLITE_PATH wordt vóór het
    (opnieuw) laden van app.py omgeleid naar een tijdelijk bestand, en
    storende env vars (toegangscode, demo-modus, Postgres) worden verwijderd.
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    monkeypatch.delenv("APP_ACCESS_CODE", raising=False)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("VAPID_PUBLIC", raising=False)
    monkeypatch.delenv("VAPID_PRIVATE", raising=False)

    import database
    monkeypatch.setattr(database, "PG_URL", None)
    monkeypatch.setattr(database, "SQLITE_PATH", tmp_path / "test_leads.db")

    if "app" in sys.modules:
        app_module = importlib.reload(sys.modules["app"])
    else:
        import app as app_module

    from fastapi.testclient import TestClient
    with TestClient(app_module.app) as test_client:
        test_client._app_module = app_module  # voor con_factory-fixture
        yield test_client


@pytest.fixture
def con_factory(client):
    """Geeft een functie terug die een nieuwe DB()-connectie opent tegen
    dezelfde tijdelijke database als de `client`-fixture."""
    import database
    return lambda: database.DB()
