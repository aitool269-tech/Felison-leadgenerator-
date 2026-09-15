import importlib
import os
import sys
import tempfile

import pytest

# Module-level guard: pytest importeert testmodules (o.a. test_scoring.py en
# test_parsing.py, die `app` op moduleniveau importeren) bij collectie, vóór
# enige fixture hieronder draait. Zonder deze guard raakt die import-tijd
# database.init_db()-aanroep de ECHTE leads.db. Dit draait onvoorwaardelijk
# zodra conftest.py geladen wordt, wat pytest garandeert vóór het importeren
# van testmodules in dezelfde boom.
for _risky_var in (
    "DATABASE_URL",
    "POSTGRES_URL",
    "APP_ACCESS_CODE",
    "DEMO_MODE",
    "VERCEL",
    "RESEND_API_KEY",
    "VAPID_PUBLIC",
    "VAPID_PRIVATE",
):
    os.environ.pop(_risky_var, None)

import database  # noqa: E402

database.SQLITE_PATH = os.path.join(tempfile.mkdtemp(), "test_leads.db")


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
        yield test_client


@pytest.fixture
def con_factory(client):
    """Geeft een functie terug die een nieuwe DB()-connectie opent tegen
    dezelfde tijdelijke database als de `client`-fixture."""
    import database
    return lambda: database.DB()
