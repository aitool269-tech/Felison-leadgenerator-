def maak_lead(con_factory, **overrides):
    con = con_factory()
    velden = {
        "vergunningnummer": "TEST-001", "naam": "Test Kantoor",
        "status": "Nieuw", "am": None, "presentje_type": None,
        "score": 60, "klasse": "B", "score_basis": 60,
    }
    velden.update(overrides)
    kolommen = ", ".join(velden.keys())
    plekken = ", ".join("?" for _ in velden)
    lead_id = con.insert_id(f"INSERT INTO leads({kolommen}) VALUES({plekken})", tuple(velden.values()))
    con.commit(); con.close()
    return lead_id


def test_claim_stuurt_geen_marketingtrigger_zonder_presentje(client, con_factory, monkeypatch):
    import app
    aangeroepen = []
    monkeypatch.setattr(app, "stuur_push", lambda *a, **k: aangeroepen.append("push"))
    monkeypatch.setattr(app, "stuur_mail", lambda *a, **k: aangeroepen.append("mail"))

    lead_id = maak_lead(con_factory, status="Nieuw", presentje_type=None)
    r = client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    assert r.status_code == 200
    assert aangeroepen == []


def test_claim_stuurt_marketingtrigger_met_presentje_ingevuld(client, con_factory, monkeypatch):
    import app
    aangeroepen = []
    monkeypatch.setattr(app, "stuur_push", lambda *a, **k: aangeroepen.append("push"))
    monkeypatch.setattr(app, "stuur_mail", lambda *a, **k: aangeroepen.append("mail"))

    lead_id = maak_lead(con_factory, status="Nieuw", presentje_type="Bloemen")
    r = client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    assert r.status_code == 200
    assert "push" in aangeroepen and "mail" in aangeroepen


def test_claim_stuurt_geen_trigger_bij_presentje_geen(client, con_factory, monkeypatch):
    import app
    aangeroepen = []
    monkeypatch.setattr(app, "stuur_push", lambda *a, **k: aangeroepen.append("push"))
    monkeypatch.setattr(app, "stuur_mail", lambda *a, **k: aangeroepen.append("mail"))

    lead_id = maak_lead(con_factory, status="Nieuw", presentje_type="Geen")
    r = client.post(f"/api/leads/{lead_id}/claim", json={"am": "Anna"})
    assert r.status_code == 200
    assert aangeroepen == []


def test_status_naar_geclaimd_zonder_presentje_stuurt_niets(client, con_factory, monkeypatch):
    import app
    aangeroepen = []
    monkeypatch.setattr(app, "stuur_push", lambda *a, **k: aangeroepen.append("push"))
    monkeypatch.setattr(app, "stuur_mail", lambda *a, **k: aangeroepen.append("mail"))

    lead_id = maak_lead(con_factory, status="Nieuw", presentje_type=None)
    r = client.post(f"/api/leads/{lead_id}/status", json={"status": "Geclaimd", "am": "Anna"})
    assert r.status_code == 200
    assert aangeroepen == []


def test_status_naar_geclaimd_met_presentje_stuurt_trigger(client, con_factory, monkeypatch):
    import app
    aangeroepen = []
    monkeypatch.setattr(app, "stuur_push", lambda *a, **k: aangeroepen.append("push"))
    monkeypatch.setattr(app, "stuur_mail", lambda *a, **k: aangeroepen.append("mail"))

    lead_id = maak_lead(con_factory, status="Nieuw", presentje_type="Wijn")
    r = client.post(f"/api/leads/{lead_id}/status", json={"status": "Geclaimd", "am": "Anna"})
    assert r.status_code == 200
    assert "push" in aangeroepen and "mail" in aangeroepen
